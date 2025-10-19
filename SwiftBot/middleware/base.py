"""
Middleware base class
Copyright (c) 2025 Arjun-M/SwiftBot
"""

from typing import Callable, Awaitable


class Middleware:
    """
    Base middleware class for request/response processing.

    Middleware can intercept updates before they reach handlers,
    modify context, implement authentication, rate limiting, logging, etc.

    Example:
        class MyMiddleware(Middleware):
            async def on_update(self, ctx, next_handler):
                # Pre-processing
                print(f"Before: {ctx.user.id}")

                # Call next middleware or handler
                await next_handler()

                # Post-processing
                print(f"After: {ctx.user.id}")

            async def on_error(self, ctx, error):
                print(f"Error: {error}")

    Copyright (c) 2025 Arjun-M/SwiftBot
    """

    async def on_update(self, ctx, next_handler: Callable[[], Awaitable]):
        """
        Called when update is received.

        Args:
            ctx: Context object
            next_handler: Next middleware or handler in chain
        """
        await next_handler()

    async def on_error(self, ctx, error: Exception):
        """
        Called when error occurs in handler.

        Args:
            ctx: Context object
            error: Exception that occurred
        """
        pass
