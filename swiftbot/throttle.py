"""
Throttle — outbound rate limiting for API calls.

Telegram enforces a hard limit of roughly 30 messages per second per bot, and
a per-chat ceiling of ~20 messages per minute. ``throttle()`` is a transformer
that keeps the bot under a configurable rate: it never drops calls — it simply
delays them.

Unlike simple middleware, throttling must happen *before* the HTTP request is
sent, so it lives in the transformer layer. Transformers may be async, and
``throttle()`` returns one: it smooths traffic with a token bucket.

Example::

    from swiftbot.throttle import throttle

    # Never exceed 25 messages/second globally
    bot.api.config.use(throttle(max_per_second=25.0))

    # Even stricter for a single chat via a payload-aware bucket:
    bot.api.config.use(throttle(max_per_second=15.0,
                                per_chat=1.0))   # one message per chat per second

Copyright (c) 2026 Arjun-M/SwiftBob / 2026 Arjun-M/SwiftBot
"""

import asyncio
import logging
import time
from typing import Any, Dict

logger = logging.getLogger(__name__)


class throttle:
    """
    An async transformer implementing a token bucket. Returns an async callable
    ``await (method, payload) -> payload`` so it composes with
    ``bot.api.config.use(...)``.
    """

    def __init__(self, max_per_second: float = 30.0,
                 per_chat: float = 0.0,
                 burst: int = 5) -> None:
        if max_per_second <= 0:
            raise ValueError("max_per_second must be positive")
        self.max_per_second = float(max_per_second)
        self.per_chat = float(per_chat)
        self._interval = 1.0 / self.max_per_second
        self._burst = max(1, int(burst))
        self._tokens = float(self._burst)
        self._last = time.monotonic()
        self._lock = asyncio.Lock()
        # per-chat buckets keyed by chat id
        self._chat_last: Dict[Any, float] = {}
        self._chat_lock = asyncio.Lock()

    async def __call__(self, method: str, payload: Dict[str, Any]) -> Dict[str, Any]:
        await self._wait_global()
        if self.per_chat > 0:
            await self._wait_chat(payload)
        return payload

    async def _wait_global(self) -> None:
        async with self._lock:
            now = time.monotonic()
            elapsed = now - self._last
            self._tokens = min(float(self._burst), self._tokens + elapsed / self._interval)
            self._last = now
            if self._tokens >= 1.0:
                self._tokens -= 1.0
                return
            wait = (1.0 - self._tokens) * self._interval
            self._tokens = 0.0
        await asyncio.sleep(wait)

    async def _wait_chat(self, payload: Dict[str, Any]) -> None:
        chat_id = None
        for key in ("chat_id", "chat"):
            if key in payload:
                chat_id = payload[key]
                break
        if chat_id is None:
            return
        async with self._chat_lock:
            now = time.monotonic()
            last = self._chat_last.get(chat_id, 0.0)
            wait = max(0.0, self.per_chat - (now - last))
            self._chat_last[chat_id] = now + wait
        if wait > 0:
            await asyncio.sleep(wait)

    def __repr__(self) -> str:
        return (f"throttle(max_per_second={self.max_per_second}, "
                f"per_chat={self.per_chat})")
