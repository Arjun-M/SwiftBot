"""
User data persistence middleware
Copyright (c) 2025 Arjun-M/SwiftBot
"""

from .base import Middleware


class UserData:
    """Helper class for user data access"""

    def __init__(self, user_id: int, storage):
        self.user_id = user_id
        self.storage = storage
        self._cache = {}

    async def get(self, key: str, default=None):
        """Get user data"""
        if key in self._cache:
            return self._cache[key]

        value = await self.storage.get(self.user_id, key)
        if value is not None:
            self._cache[key] = value
        return value if value is not None else default

    async def set(self, key: str, value):
        """Set user data"""
        self._cache[key] = value
        await self.storage.set(self.user_id, key, value)

    async def delete(self, key: str):
        """Delete user data"""
        self._cache.pop(key, None)
        await self.storage.delete(self.user_id, key)

    async def clear(self):
        """Clear all user data"""
        self._cache.clear()
        await self.storage.clear(self.user_id)


class UserDataMiddleware(Middleware):
    """
    Middleware for user data persistence.

    Provides ctx.user_data for storing user-specific data.

    Copyright (c) 2025 Arjun-M/SwiftBot
    """

    def __init__(self, storage, auto_create: bool = True, cache_ttl: int = 300):
        """
        Initialize user data middleware.

        Args:
            storage: Storage adapter instance
            auto_create: Automatically create user data on first access
            cache_ttl: Cache TTL in seconds
        """
        self.storage = storage
        self.auto_create = auto_create
        self.cache_ttl = cache_ttl

    async def on_update(self, ctx, next_handler):
        """Attach user data to context"""
        if ctx.user:
            ctx.user_data = UserData(ctx.user.id, self.storage)

        await next_handler()
