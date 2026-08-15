"""
Authentication and authorization middleware
Copyright (c) 2025 Arjun-M/SwiftBot
"""

from .base import Middleware


class Auth(Middleware):
    """
    Authentication middleware for access control.

    Supports whitelisting, blacklisting, and custom auth functions.

    Copyright (c) 2025 Arjun-M/SwiftBot
    """

    def __init__(
        self,
        whitelist: list = None,
        blacklist: list = None,
        admin_list: list = None,
        check_func = None,
        on_unauthorized = None
    ):
        """
        Initialize auth middleware.

        Args:
            whitelist: List of allowed user IDs (None = allow all)
            blacklist: List of blocked user IDs
            admin_list: List of admin user IDs
            check_func: Custom authorization function
            on_unauthorized: Callback for unauthorized access
        """
        self.whitelist = set(whitelist) if whitelist else None
        self.blacklist = set(blacklist) if blacklist else set()
        self.admin_list = set(admin_list) if admin_list else set()
        self.check_func = check_func
        self.on_unauthorized = on_unauthorized

    async def on_update(self, ctx, next_handler):
        """Check authorization before processing"""
        if not ctx.user:
            return

        user_id = ctx.user.id

        # Check blacklist
        if user_id in self.blacklist:
            if self.on_unauthorized:
                await self.on_unauthorized(ctx)
            else:
                await ctx.reply("🚫 Access denied.")
            return

        # Check whitelist
        if self.whitelist and user_id not in self.whitelist:
            if self.on_unauthorized:
                await self.on_unauthorized(ctx)
            else:
                await ctx.reply("🚫 You are not authorized to use this bot.")
            return

        # Check custom function
        if self.check_func and not self.check_func(ctx):
            if self.on_unauthorized:
                await self.on_unauthorized(ctx)
            else:
                await ctx.reply("🚫 Authorization check failed.")
            return

        # Add admin flag to context
        ctx.is_admin = user_id in self.admin_list

        await next_handler()
