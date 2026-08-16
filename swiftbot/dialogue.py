"""
Dialogue — a typed, state-carrying conversation FSM.

Where a ``Wizard`` accumulates answers into a flat data dict, a ``Dialogue``
treats every state transition as a typed function call: each state declares
the states it may legally move to, and its *return value is passed to the next
state*. Illegal transitions and missing states raise loudly, so a conversation
that drifts out of its declared graph fails in the open instead of silently
resetting.

The Dialogue is storage-agnostic — any ``BaseStorage`` (memory, JSON file, or
Redis) persists the current state and its carry value, so conversations
survive bot restarts.

Example::

    dlg = bot.dialogue("survey")

    @dlg.state("ask_name", next=["ask_age"])
    async def ask_name(ctx, prev=None):
        await ctx.reply("What is your name?")
        return Dialogue.next("ask_age")

    @dlg.state("ask_age", next=["done"])
    async def ask_age(ctx, prev=None):
        await ctx.reply("And your age?")
        return Dialogue.next("done")

    @dlg.finish
    async def done(ctx, prev=None):
        await ctx.reply(f"Registered! Carry from start: {prev}")
        return Dialogue.end

    # In any handler:
    await dlg.enter(ctx, "ask_name")     # begin
    await dlg.step_forward(ctx, answer)  # advance — next state receives the answer

Copyright (c) 2026 Arjun-M/SwiftBot
"""

import asyncio
import logging
import time
from typing import Any, Callable, Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)

DEFAULT_TIMEOUT = 600.0  # 10 minutes per state


class DialogueTransitionError(Exception):
    """A state attempted an illegal or malformed transition."""


class _NextState:
    __slots__ = ("state", "carry")

    def __init__(self, state: str, carry: Any) -> None:
        self.state = state
        self.carry = carry

    def __repr__(self) -> str:
        return f"NextState({self.state!r})"


class _EndState:
    """Sentinel returned by a finish handler or an explicit end transition."""

    def __repr__(self) -> str:
        return "Dialogue.end"

    def __bool__(self) -> bool:
        return True


END = _EndState()


class Dialogue:
    """
    A named, storage-backed conversation whose states carry data forward.
    """

    @staticmethod
    def next(state: str, carry: Any = None) -> _NextState:
        return _NextState(state, carry)
    end = END

    def __init__(self, name: str, storage: Any = None, timeout: float = DEFAULT_TIMEOUT) -> None:
        self.name = name
        self._storage = storage
        self._states: Dict[str, Dict[str, Any]] = {}
        self._finish_fn: Optional[Callable] = None
        self._timeout_fn: Optional[Callable] = None
        self._timeout = timeout
        self._timeouts: Dict[str, float] = {}

    # ------------------------------------------------------------------
    # Registration
    # ------------------------------------------------------------------

    def state(self, name: str, next: Optional[List[str]] = None,
              timeout: Optional[float] = None) -> Callable:
        """
        Register a state. ``next`` declares the legal transitions; omitting it
        permits a transition to any registered state. ``timeout`` (seconds)
        expires the dialogue in this state when exceeded.
        """
        def deco(fn: Callable) -> Callable:
            if name in self._states:
                raise ValueError(f"dialogue {self.name!r}: state {name!r} already registered")
            self._states[name] = {"fn": fn, "next": next, "timeout": timeout}
            return fn
        return deco

    def finish(self, fn: Callable) -> Callable:
        """Register the completion handler ``async def (ctx, prev)``."""
        self._finish_fn = fn
        return fn

    def on_timeout(self, fn: Callable) -> Callable:
        """Optional hook ``async def (ctx, expired_state)`` called on state expiry."""
        self._timeout_fn = fn
        return fn

    # ------------------------------------------------------------------
    # Storage helpers
    # ------------------------------------------------------------------

    def _uid(self, ctx) -> Optional[int]:
        user_id = getattr(getattr(ctx, "user", None), "id", None)
        if user_id is None:
            raw = getattr(ctx, "raw", None)
            if isinstance(raw, dict):
                user_id = raw.get("message", {}).get("from", {}).get("id")
        return user_id

    def _ns(self) -> str:
        return f"swiftbot:dialogue:{self.name}"

    async def _get_state(self, ctx) -> Optional[Tuple[str, Any]]:
        uid = self._uid(ctx)
        if uid is None:
            return None
        return await self._storage.get(self._ns(), str(uid))

    async def _set_state(self, ctx, state: str, carry: Any) -> None:
        uid = self._uid(ctx)
        await self._storage.set(self._ns(), str(uid), (state, carry))

    async def _clear_state(self, ctx) -> None:
        uid = self._uid(ctx)
        await self._storage.delete(self._ns(), str(uid))

    # ------------------------------------------------------------------
    # Control
    # ------------------------------------------------------------------

    async def enter(self, ctx, state: str, carry: Any = None) -> bool:
        """Begin the dialogue at ``state`` with an optional carry value."""
        if state not in self._states:
            raise DialogueTransitionError(
                f"dialogue {self.name!r}: no such start state {state!r}")
        await self._set_state(ctx, state, carry)
        return await self._run_state(ctx, state, carry, started=True)

    async def step_forward(self, ctx, answer: Any = None) -> bool:
        """
        Advance the active dialogue: the next state receives ``answer`` as its
        ``prev`` value. Returns True if the dialogue advanced (or finished),
        False if none was active.
        """
        current = await self._get_state(ctx)
        if current is None:
            return False
        state, carry = current
        if await self._is_expired(ctx, state):
            return await self._expire(ctx, state)

        target_fn = self._states.get(state, {}).get("fn")
        next_val = None
        try:
            next_val = await target_fn(ctx, prev=answer)
        except Exception as exc:
            logger.error("Dialogue %r state %r raised: %s", self.name, state,
                         exc, exc_info=True)
            await self._clear_state(ctx)
            return False

        if isinstance(next_val, _EndState) or next_val is END:
            await self._clear_state(ctx)
            return True
        if isinstance(next_val, _NextState):
            advanced = await self._transition(ctx, state, next_val)
            # If the final state's function ended the dialogue (returned END,
            # None, or an error), ``current`` was already cleared — nothing to do.
            return advanced
        # Returning None/anything else ends the dialogue (convenience).
        await self._clear_state(ctx)
        return True

    async def exit(self, ctx) -> bool:
        await self._clear_state(ctx)
        return True

    async def current(self, ctx) -> Optional[str]:
        current = await self._get_state(ctx)
        return current[0] if current else None

    async def current_data(self, ctx) -> Optional[Any]:
        current = await self._get_state(ctx)
        return current[1] if current else None

    def active(self, ctx) -> bool:
        """Sync check: does this ctx currently have an active dialogue?"""
        # Sync callers can rely on this; async callers should prefer current().
        current = getattr(ctx, "_dialogue_cache", None)
        return current is not None and current.get(self.name) is not None

    # ------------------------------------------------------------------
    # Internals
    # ------------------------------------------------------------------

    def _ts_key(self, uid: int) -> Tuple[str, str]:
        return self._ns(), f"{uid}:at"

    async def _is_expired(self, ctx, state: str) -> bool:
        uid = self._uid(ctx)
        if uid is None:
            return False
        spec = self._states.get(state, {})
        spec_timeout = spec.get("timeout")
        deadline = spec_timeout if spec_timeout is not None else self._timeout
        at = await self._storage.get(*self._ts_key(uid)) if self._storage else None
        if at is None:
            return False
        return time.monotonic() - at > deadline

    async def _record_entry(self, ctx) -> None:
        uid = self._uid(ctx)
        if uid is None:
            return
        await self._storage.set(*self._ts_key(uid), time.monotonic())

    async def _transition(self, ctx, from_state: str, nxt: _NextState) -> bool:
        if nxt.state not in self._states:
            await self._clear_state(ctx)
            raise DialogueTransitionError(
                f"dialogue {self.name!r}: transition to unknown state {nxt.state!r}")
        allowed = self._states[from_state].get("next")
        if allowed is not None and nxt.state not in allowed:
            await self._clear_state(ctx)
            raise DialogueTransitionError(
                f"dialogue {self.name!r}: {from_state!r} cannot transition to "
                f"{nxt.state!r}; allowed: {allowed}")
        await self._record_entry(ctx)
        await self._set_state(ctx, nxt.state, nxt.carry)
        result = await self._run_state(ctx, nxt.state, nxt.carry)
        # If the target state ended the dialogue (returned END or None),
        # clear the state so ``current`` reports ``None``.
        if result is None or isinstance(result, _EndState) or result is END:
            await self._clear_state(ctx)
        return result is not False

    async def _run_state(self, ctx, state: str, carry: Any,
                         started: bool = False) -> bool:
        await self._record_entry(ctx)
        try:
            return await self._states[state]["fn"](ctx, prev=carry)
        except DialogueTransitionError:
            raise
        except Exception as exc:
            logger.error("Dialogue %r state %r raised: %s", self.name, state,
                         exc, exc_info=True)
            await self._clear_state(ctx)
            return False
        return True

    async def _expire(self, ctx, state: str) -> bool:
        await self._clear_state(ctx)
        if self._timeout_fn is not None:
            try:
                await self._timeout_fn(ctx, state)
            except Exception as exc:
                logger.error("Dialogue %r timeout hook raised: %s",
                             self.name, exc, exc_info=True)
        return False

    def __repr__(self) -> str:
        return f"Dialogue({self.name!r}, states={list(self._states)})"
