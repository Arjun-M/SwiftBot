"""
Official plugins — first-class, installable middleware plugins.

grammy's ecosystem success comes from plugins being *middleware functions*
that anyone can publish and install with a single ``bot.use(...)``. This
module ships the four plugins most bots need, implemented as plain
``on_update(ctx, next_handler)`` middleware so they compose with everything
else in SwiftBot:

- ``spam_deflector`` — deflect users who flood the bot with too many messages
  per minute; ignored updates never reach handlers.
- ``session_limiter`` — enforce a minimum interval between a user's accepted
  messages (throttle, not block).
- ``idempotency`` — deduplicate identical updates arriving twice (webhook
  retries, double-taps).
- ``whitelist`` — accept updates only from a set of user/chat ids.

Example::

    from swiftbot import SwiftBot
    from swiftbot import plugins

    bot = SwiftBot(token="...")
    bot.use(plugins.spam_deflector(threshold=10, window=60))
    bot.use(plugins.session_limiter(min_interval=2.0))
    bot.use(plugins.idempotency())
    bot.use(plugins.whitelist(user_ids={123456}))

Copyright (c) 2026 Arjun-M/SwiftBot
"""

import asyncio
import hashlib
import json
import logging
import time
from typing import Any, Callable, Dict, Optional, Set

logger = logging.getLogger(__name__)


class SpamDeflector:
    """
    Deflect flooders: if a user sends more than ``threshold`` updates within
    ``window`` seconds, further updates from that user are dropped until the
    window resets.
    """

    def __init__(self, threshold: int = 10, window: float = 60.0,
                 on_deflect: Optional[Callable] = None) -> None:
        self.threshold = threshold
        self.window = window
        self.on_deflect = on_deflect
        self._hits: Dict[Any, list] = {}

    async def on_update(self, ctx, next_handler) -> None:
        user_id = getattr(getattr(ctx, "user", None), "id", None)
        if user_id is None:
            await next_handler()
            return
        now = time.time()
        hits = [t for t in self._hits.setdefault(user_id, []) if now - t < self.window]
        if len(hits) >= self.threshold:
            if self.on_deflect is not None:
                try:
                    result = self.on_deflect(ctx)
                    if asyncio.iscoroutine(result):
                        await result
                except Exception as exc:
                    logger.error("spam_deflector hook raised: %s", exc, exc_info=True)
            return  # dropped
        hits.append(now)
        self._hits[user_id] = hits
        await next_handler()


def spam_deflector(threshold: int = 10, window: float = 60.0,
                   on_deflect: Optional[Callable] = None) -> SpamDeflector:
    return SpamDeflector(threshold=threshold, window=window, on_deflect=on_deflect)


class SessionLimiter:
    """
    Throttle each user: messages arrive at most once per ``min_interval``
    seconds; the rest are dropped (with an optional deflect hook).
    """

    def __init__(self, min_interval: float = 2.0,
                 on_deflect: Optional[Callable] = None) -> None:
        self.min_interval = min_interval
        self.on_deflect = on_deflect
        self._last: Dict[Any, float] = {}

    async def on_update(self, ctx, next_handler) -> None:
        user_id = getattr(getattr(ctx, "user", None), "id", None)
        if user_id is None:
            await next_handler()
            return
        now = time.time()
        last = self._last.get(user_id, 0.0)
        if now - last < self.min_interval:
            if self.on_deflect is not None:
                try:
                    result = self.on_deflect(ctx)
                    if asyncio.iscoroutine(result):
                        await result
                except Exception as exc:
                    logger.error("session_limiter hook raised: %s", exc, exc_info=True)
            return
        self._last[user_id] = now
        await next_handler()


def session_limiter(min_interval: float = 2.0,
                    on_deflect: Optional[Callable] = None) -> SessionLimiter:
    return SessionLimiter(min_interval=min_interval, on_deflect=on_deflect)


class Idempotency:
    """
    Deduplicate identical updates: same user + same text/callback data within
    ``window`` seconds is delivered only once.
    """

    def __init__(self, window: float = 5.0) -> None:
        self.window = window
        self._seen: Dict[str, float] = {}

    @staticmethod
    def _fingerprint(ctx) -> Optional[str]:
        user_id = getattr(getattr(ctx, "user", None), "id", None)
        text = getattr(ctx, "text", None) or getattr(ctx, "data", None)
        if user_id is None or text is None:
            return None
        raw = json.dumps({"u": user_id, "t": text}, sort_keys=True, default=str)
        return hashlib.sha1(raw.encode()).hexdigest()

    async def on_update(self, ctx, next_handler) -> None:
        fp = self._fingerprint(ctx)
        if fp is None:
            await next_handler()
            return
        now = time.time()
        last = self._seen.get(fp, 0.0)
        if now - last < self.window:
            return  # duplicate
        self._seen[fp] = now
        # Prune stale fingerprints lazily.
        self._seen = {k: v for k, v in self._seen.items() if now - v < self.window * 2}
        await next_handler()


def idempotency(window: float = 5.0) -> Idempotency:
    return Idempotency(window=window)


class Whitelist:
    """
    Accept updates only from ``user_ids`` and/or ``chat_ids``. Everything else
    is silently dropped.
    """

    def __init__(self, user_ids: Optional[Set[int]] = None,
                 chat_ids: Optional[Set[int]] = None) -> None:
        self.user_ids = user_ids or set()
        self.chat_ids = chat_ids or set()

    async def on_update(self, ctx, next_handler) -> None:
        user_id = getattr(getattr(ctx, "user", None), "id", None)
        chat_id = getattr(getattr(ctx, "chat", None), "id", None)
        if self.user_ids and user_id not in self.user_ids:
            return
        if self.chat_ids and chat_id not in self.chat_ids:
            return
        await next_handler()


def whitelist(user_ids: Optional[Set[int]] = None,
              chat_ids: Optional[Set[int]] = None) -> Whitelist:
    return Whitelist(user_ids=user_ids, chat_ids=chat_ids)
