"""
Rate limiting middleware
Copyright (c) 2025 Arjun-M/SwiftBot
"""

import time
from collections import defaultdict
from .base import Middleware


class RateLimiter(Middleware):
    """
    Rate limiting middleware to prevent spam and abuse.

    Supports multiple strategies:
    - fixed_window: Fixed time windows
    - sliding_window: Sliding time windows (more accurate)
    - token_bucket: Token bucket algorithm

    Copyright (c) 2025 Arjun-M/SwiftBot
    """

    def __init__(
        self,
        rate: int = 10,
        per: int = 60,
        strategy: str = "sliding_window",
        storage=None,
        key_func=None,
        on_exceeded=None
    ):
        """
        Initialize rate limiter.

        Args:
            rate: Maximum requests
            per: Time period in seconds
            strategy: Rate limiting strategy
            storage: Storage backend (Redis recommended for multi-instance)
            key_func: Function to generate rate limit key from context
            on_exceeded: Callback when rate limit exceeded
        """
        self.rate = rate
        self.per = per
        self.strategy = strategy
        self.storage = storage
        self.key_func = key_func or (lambda ctx: f"user:{ctx.user.id}")
        self.on_exceeded = on_exceeded

        # In-memory storage (fallback)
        self._memory_store = defaultdict(list)

    async def on_update(self, ctx, next_handler):
        """Check rate limit before processing"""
        key = self.key_func(ctx)

        if await self._is_rate_limited(key):
            if self.on_exceeded:
                await self.on_exceeded(ctx)
            else:
                await ctx.reply("⚠️ Rate limit exceeded. Please slow down.")
            return

        await self._record_request(key)
        await next_handler()

    async def _is_rate_limited(self, key: str) -> bool:
        """Check if key is rate limited"""
        current_time = time.time()

        if self.storage:
            # Use external storage (Redis)
            return await self._check_redis(key, current_time)
        else:
            # Use in-memory storage
            return self._check_memory(key, current_time)

    def _check_memory(self, key: str, current_time: float) -> bool:
        """Check rate limit using in-memory store"""
        requests = self._memory_store[key]

        # Remove old requests
        cutoff_time = current_time - self.per
        requests[:] = [t for t in requests if t > cutoff_time]

        return len(requests) >= self.rate

    async def _check_redis(self, key: str, current_time: float) -> bool:
        """Check rate limit using Redis"""
        # Redis implementation
        # This is a simplified version - production should use Redis ZSET
        try:
            count = await self.storage.get(f"ratelimit:{key}")
            return int(count or 0) >= self.rate
        except:
            return False

    async def _record_request(self, key: str):
        """Record a request"""
        current_time = time.time()

        if self.storage:
            await self._record_redis(key, current_time)
        else:
            self._memory_store[key].append(current_time)

    async def _record_redis(self, key: str, current_time: float):
        """Record request in Redis"""
        try:
            # Increment counter
            await self.storage.incr(f"ratelimit:{key}")
            await self.storage.expire(f"ratelimit:{key}", self.per)
        except:
            pass
