"""
Scopes — attach middleware to a slice of traffic instead of the whole bot.

Global ``bot.use(...)`` middleware runs for every update. A ``Scope`` wraps
middleware so it only runs when a predicate matches the raw update — for
example, heavy moderation middleware only in groups, or a slow path only for
private chats. Scopes compose freely and can hold ``Composer`` bundles with
their own error boundaries.

Example::

    from swiftbot.scopes import Scope
    from swiftbot.plugins import session_limiter

    # Only rate-limit group traffic
    bot.scope(lambda upd: upd.get("message", {}).get("chat", {}).get("type") == "group") \
       .use(session_limiter(min_interval=1.0))

    # Composable with the F filter algebra
    bot.scope(F.private).use(slow_handler_middleware, metrics_bundle)

Copyright (c) 2026 Arjun-M/SwiftBot
"""

import logging
from typing import Any, Callable, List

logger = logging.getLogger(__name__)


class Scope:
    """
    A middleware chain guarded by a predicate over the raw update dict.
    """

    def __init__(self, predicate: Callable) -> None:
        self.predicate = predicate
        self._middleware: List[Any] = []

    def use(self, *middleware: Any) -> "Scope":
        """Append middleware (plain callables or ``Composer`` bundles)."""
        self._middleware.extend(middleware)
        return self

    async def on_update(self, ctx, next_handler) -> None:
        """
        Middleware-protocol entry point: run the chain only when the predicate
        matches, then call ``next_handler`` either way.
        """
        raw = getattr(getattr(ctx, "update", None), "raw", None)
        matched = False
        try:
            matched = bool(self.predicate(raw if isinstance(raw, dict) else {}))
        except Exception as exc:  # a broken predicate never blocks updates
            logger.error("Scope predicate raised: %s", exc, exc_info=True)

        if not matched or not self._middleware:
            await next_handler()
            return

        # Build the chain: each middleware calls the next; the tail calls next_handler.
        async def _chain(index: int) -> None:
            if index >= len(self._middleware):
                await next_handler()
                return
            mw = self._middleware[index]
            if hasattr(mw, "on_update"):
                await mw.on_update(ctx, lambda i=index + 1: _chain(i))
            else:
                await mw(ctx, lambda i=index + 1: _chain(i))

        await _chain(0)

    def __len__(self) -> int:
        return len(self._middleware)

    def __repr__(self) -> str:
        return f"Scope(middleware={len(self._middleware)})"
