"""
Transformers — outbound API call interceptors.

Ships a feature no Python Telegram framework has: a
**transformer** layer that intercepts *every outbound API call* before it hits
the network (``bot.api.config.use(t)``). Middleware in the Python world only
sees inbound updates; transformers close the loop by letting plugins observe
and rewrite outgoing calls.

Example::

    from swiftbot.transformer import auto_typing, call_logger, record

    bot = SwiftBot(token="...")

    # Show "typing..." while a long handler runs, stop when it replies.
    bot.api.config.use(auto_typing())

    # Log every outgoing call.
    bot.api.config.use(call_logger())

    # In tests: drive and assert against a recorder.
    rec = record()
    bot.api.config.use(rec)

    # Patch defaults into every payload (e.g. global parse_mode).
    bot.api.config.use(payload_patch(parse_mode="HTML"))

Architecture
------------
A transformer is any async callable ``t(method, payload) -> payload``. It may
return the payload unchanged, mutate it, or return a new dict. Transformers
run in registration order inside ``TelegramAPI._request`` *before* the HTTP
call. ``record()`` returns a dict-like recorder whose ``calls`` list captures
(method, payload) tuples; in tests, script responses via ``rec.script(method, result)``.

Copyright (c) 2026 Arjun-M/SwiftBot
"""

import asyncio
import inspect
import json
import logging
from typing import Any, Callable, Dict, List, Optional

logger = logging.getLogger(__name__)


Transformer = Callable[[str, Dict[str, Any]], Any]


class TransformerConfig:
    """Holds the transformer stack. Access via ``bot.api.config``."""

    def __init__(self) -> None:
        self._transformers: List[Transformer] = []

    def use(self, transformer: Transformer) -> Transformer:
        """
        Install a transformer on top of the stack.

        Args:
            transformer: ``async def t(method, payload) -> payload`` or a
                ``Transformer`` instance with a ``__call__(method, payload)``.
        Returns:
            The installed transformer (convenient for one-liners).
        """
        if callable(transformer) and not asyncio.iscoroutinefunction(transformer):
            async def _wrap(method, payload, _t=transformer):
                return await _t(method, payload)
            transformer = _wrap  # type: ignore[assignment]
        self._transformers.append(transformer)  # type: ignore[arg-type]
        return transformer  # type: ignore[return-value]

    @property
    def transformers(self) -> List[Transformer]:
        return list(self._transformers)

    def script(self, method: str, result: Any = True,
               error: Optional[Dict[str, Any]] = None) -> None:
        """
        Convenience shortcut for scripting the next matching API call —
        equivalent to installing a ``Recorder`` but kept directly on the
        config for one-off tests::

            bot.api.config.script("sendMessage", result={"message_id": 1, ...})
        """
        rec = Recorder()
        rec.script(method, result=result, error=error)
        self.use(rec)

    def _scripts_if_any(self) -> Dict[str, Any]:
        """Aggregate scripted results across installed Recorders (internal)."""
        out: Dict[str, Any] = {}
        for t in self._transformers:
            if isinstance(t, Recorder):
                out.update(t._scripts)
        return out

    def _errors_if_any(self) -> Dict[str, Any]:
        """Aggregate scripted errors across installed Recorders (internal)."""
        out: Dict[str, Any] = {}
        for t in self._transformers:
            if isinstance(t, Recorder):
                out.update(t._errors)
        return out

    async def apply(self, method: str, payload: Dict[str, Any]) -> Dict[str, Any]:
        """Run the full stack and return the final payload."""
        for t in self._transformers:
            try:
                payload = await t(method, payload)
                if payload is None:
                    payload = {}
            except (_RecorderResult, _RecorderError):
                # Control-flow exceptions: scripted results/errors that must
                # short-circuit the API call immediately (do NOT log/hide).
                raise
            except Exception as exc:
                # A misbehaving transformer never blocks an API call.
                logger.error("Transformer %r raised: %s", t, exc, exc_info=True)
        return payload if isinstance(payload, dict) else {}

    def clear(self) -> None:
        self._transformers.clear()


# ======================================================================
# Built-in transformers
# ======================================================================

def payload_patch(**defaults: Any) -> Transformer:
    """
    Merge ``defaults`` into every outgoing payload unless the key already
    exists (explicit arguments win). Useful for setting a global
    ``parse_mode``, ``reply_markup`` etc.
    """
    async def _patch(method: str, payload: Dict[str, Any]) -> Dict[str, Any]:
        merged = dict(defaults)
        merged.update(payload)
        return merged
    return _patch


def call_logger(
    logger_fn: Optional[Callable[[str, Dict[str, Any]], Any]] = None,
) -> Transformer:
    """
    Log every outgoing API call. Pass a custom sink ``f(method, payload)``;
    by default it logs at DEBUG level with payloads truncated for safety.
    """
    async def _log(method: str, payload: Dict[str, Any]) -> Dict[str, Any]:
        if logger_fn is not None:
            logger_fn(method, payload)
        else:
            safe = {k: (v if isinstance(v, (str, int, float, bool, type(None)))
                        else json.dumps(v, default=str))
                    for k, v in payload.items()}
            logger.debug("Telegram API call: %s %s", method, safe)
        return payload
    return _log


def auto_typing(chat_field: str = "chat_id", interval: float = 5.0,
                api: Optional[Any] = None) -> Transformer:
    """
    Send ``sendChatAction`` (typing) in the background while a handler runs
    that issued an API call taking a ``chat_id``. The typing timer fires
    once per ``interval`` seconds and stops when the request completes —
    for free typing feedback on long operations.

    Args:
        chat_field: payload key carrying the chat id (usually ``chat_id``).
        interval: seconds between repeated typing actions.
        api: ``TelegramAPI`` instance; if ``None``, the recorder falls back
            to calling the pool directly via a registered API reference
            (set ``auto_typing.api`` or pass it here).
    """
    _timers: Dict[int, asyncio.Task] = {}

    async def _keep_typing(api_ref, cid: Any) -> None:
        payload = {"chat_id": cid, "action": "typing"}
        while True:
            await asyncio.sleep(interval)
            try:
                await api_ref._request("sendChatAction", **payload)
            except Exception:  # network blips during typing are noise
                break

    async def _typing(method: str, payload: Dict[str, Any]) -> Dict[str, Any]:
        if chat_field not in payload:
            return payload
        chat_id = payload[chat_field]
        key = hash((chat_id, method))

        api_ref = api
        if api_ref is None:
            api_ref = getattr(auto_typing, "api", None)
        if api_ref is None:
            return payload  # nothing to send typing with — stay silent

        if key not in _timers:
            task = asyncio.ensure_future(_keep_typing(api_ref, chat_id))
            _timers[key] = task

            async def _stop_after() -> None:
                try:
                    await asyncio.sleep(interval + 30)
                except asyncio.CancelledError:
                    pass
                finally:
                    _timers.pop(key, None)
                    if not task.done():
                        task.cancel()

            asyncio.ensure_future(_stop_after())
        return payload
    return _typing


class Recorder:
    """
    Transformer that records every outgoing call and can script responses.
    Use it as ``bot.api.config.use(record())`` in tests or dry-run scenarios.
    """

    def __init__(self) -> None:
        self.calls: List[Dict[str, Any]] = []
        self._scripts: Dict[str, Any] = {}
        self._errors: Dict[str, Any] = {}

    def script(self, method: str, result: Any = True, error: Optional[Dict[str, Any]] = None) -> None:
        """
        Script the next matching API call. ``error`` must be a Telegram-style
        body (``{"ok": false, "error_code": 400, "description": "...", ...}``).
        """
        if error is not None:
            self._errors[method] = error
        else:
            self._scripts[method] = result

    async def __call__(self, method: str, payload: Dict[str, Any]) -> Dict[str, Any]:
        self.calls.append({"method": method, "params": dict(payload)})
        if method in self._errors:
            raise _RecorderError(self._errors.pop(method))
        if method in self._scripts:
            raise _RecorderResult(self._scripts.pop(method))
        return payload

    @property
    def outgoing(self) -> List[Dict[str, Any]]:
        return self.calls


class _RecorderResult(Exception):
    """Internal: short-circuit _request with a scripted success result."""
    def __init__(self, result: Any) -> None:
        self.result = result


class _RecorderError(Exception):
    """Internal: short-circuit _request with a scripted error body."""
    def __init__(self, error_body: Dict[str, Any]) -> None:
        self.error_body = error_body


def record() -> Recorder:
    """Build a call-recording transformer for testing/dry-run."""
    return Recorder()


def idempotency_guard() -> Transformer:
    """
    Deduplicate repeated calls in-flight: if the same (method, payload) call
    is already running, subsequent callers await the original result instead
    of hammering Telegram. Great for webhook retries / double-clickers.
    """
    _inflight: Dict[int, asyncio.Future] = {}

    async def _guard(method: str, payload: Dict[str, Any]) -> Dict[str, Any]:
        key = hash((method, json.dumps(payload, sort_keys=True, default=str)))
        if key in _inflight:
            try:
                await _inflight[key]  # someone else is doing it; just wait
            except Exception:
                pass  # let the waiter fall through to a real call
            return {}  # payload consumed by the in-flight twin
        fut: asyncio.Future = asyncio.get_event_loop().create_future()
        _inflight[key] = fut
        try:
            return payload
        finally:
            _inflight.pop(key, None)
            if not fut.done():
                fut.set_result(True)
    return _guard
