"""
Composer — extractable middleware bundles with scoped error boundaries.

Structures large bots around ``Composer``: modules
export a bundle of middleware, register scoped ``.catch()`` error handlers,
and the bot installs the bundle with a single ``bot.use(bundle)``. This lets
errors in one module be handled by that module instead of bubbling to a
single global handler.

Example::

    from swiftbot.composer import Composer
    from swiftbot.middleware import Logger

    admin = Composer(Logger(), admin_only_middleware)
    admin.catch(lambda ctx, e: ctx.reply("Admin area error"))

    todo = Composer()
    todo.use(list_middleware)
    todo.on_error = lambda ctx, e: log_error(e)

    bot = Composer(Logger())
    bot.use(admin, todo)
    bot.use(main_middleware)

    bot.install_on(bot)   # install everything onto the SwiftBot client

Any ``Composer`` can be passed to ``SwiftBot.use()`` directly; the client
flattens the nested middleware with its boundary semantics preserved.

Copyright (c) 2026 Arjun-M/SwiftBot
"""

import asyncio
import logging
from typing import Any, Callable, List, Optional

logger = logging.getLogger(__name__)


class Composer:
    """
    A bundle of middleware that can be composed, nested and given scoped
    error boundaries.
    """

    def __init__(self, *middleware: Any) -> None:
        self.middleware: List[Any] = list(middleware)
        self._error_handler: Optional[Callable] = None
        self.on_error: Optional[Callable] = None  # alias-style convenience

    # ------------------------------------------------------------------
    # Composition
    # ------------------------------------------------------------------

    def use(self, *middleware: Any) -> "Composer":
        """Append middleware to this bundle. Returns ``self`` for chaining."""
        self.middleware.extend(middleware)
        return self

    def catch(self, handler: Callable) -> Callable:
        """
        Register a scoped error boundary: ``handler(ctx, exception)`` is
        called for every exception raised inside this bundle.
        """
        self._error_handler = handler
        return handler

    def on_exception(self, handler: Callable) -> Callable:
        """Alias of ``catch`` mirroring the ``on_error`` attribute style."""
        return self.catch(handler)

    # ------------------------------------------------------------------
    # Middleware protocol
    # ------------------------------------------------------------------

    async def on_update(self, ctx, next_handler) -> None:
        """
        Run the bundle's middleware chain with this composer's error boundary.
        The Composer itself satisfies the ``on_update(ctx, next_handler)``
        middleware protocol so ``bot.use(composer)`` works natively.
        """
        iter_ = iter(self.middleware)

        async def _next() -> None:
            try:
                mw = next(iter_)
            except StopIteration:
                await next_handler()
                return

            if isinstance(mw, Composer):
                # nested composer: run it inline (its boundary wraps it)
                await mw.on_update(ctx, _next)
            elif hasattr(mw, "on_update"):
                await mw.on_update(ctx, _next)
            else:
                # Raw middleware callable: ``(ctx, next_handler)`` protocol
                # (SwiftBot middleware is defined by the call shape, not by a
                # base class — see ``SwiftBot.use``).
                result = mw(ctx, _next)
                if asyncio.iscoroutine(result):
                    await result

        try:
            await _next()
        except Exception as exc:
            boundary = self._error_handler or self.on_error
            if boundary is not None:
                try:
                    result = boundary(ctx, exc)
                    if asyncio.iscoroutine(result):
                        await result
                except Exception as boundary_exc:
                    logger.error("Composer error boundary raised: %s",
                                 boundary_exc, exc_info=True)
                return  # boundary consumed the error; chain ends here
            raise  # no boundary — let the client/global handler see it

    def __len__(self) -> int:
        return len(self.middleware)

    def __repr__(self) -> str:
        return f"Composer(middleware={len(self.middleware)}, boundary={bool(self._error_handler)})"


class DispatchRoute:
    """One entry of a ``bot.route()`` dispatch table (update kind → middleware)."""

    def __init__(self, update_kind: str, middleware: Any) -> None:
        self.update_kind = update_kind
        self.middleware = middleware
