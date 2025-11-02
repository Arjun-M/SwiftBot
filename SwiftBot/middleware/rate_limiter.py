"""
Rate limiting middleware with cache-based storage
Copyright (c) 2025 Arjun-M/SwiftBot
"""

import time
from collections import defaultdict
from .base import Middleware


class RateLimiter(Middleware):
    """
    Rate limiting middleware to prevent spam and abuse.

    Uses in-memory cache for rate limiting without external storage dependencies.
    Features automatic cleanup and configurable strategies.

    Copyright (c) 2025 Arjun-M/SwiftBot
    """

    def __init__(
        self,
        rate: int = 10,
        per: int = 60,
        strategy: str = "sliding_window",
        key_func=None,
        on_exceeded=None,
        cleanup_interval: int = 300
    ):
        """
        Initialize rate limiter with cache-based storage.

        Args:
            rate: Maximum requests
            per: Time period in seconds
            strategy: Rate limiting strategy
            key_func: Function to generate rate limit key from context
            on_exceeded: Callback when rate limit exceeded
            cleanup_interval: Interval for cleaning old entries (seconds)
        """
        self.rate = rate
        self.per = per
        self.strategy = strategy
        self.key_func = key_func or (lambda ctx: f"user:{ctx.user.id if ctx.user else 'anonymous'}")
        self.on_exceeded = on_exceeded
        self.cleanup_interval = cleanup_interval

        # Cache-based storage
        self._request_cache = defaultdict(list)
        self._last_cleanup = time.time()

    async def on_update(self, ctx, next_handler):
        """Check rate limit before processing"""
        key = self.key_func(ctx)
        current_time = time.time()

        # Periodic cleanup
        if current_time - self._last_cleanup > self.cleanup_interval:
            self._cleanup_old_entries(current_time)

        if self._is_rate_limited(key, current_time):
            if self.on_exceeded:
                await self.on_exceeded(ctx)
            else:
                await ctx.reply("⚠️ Rate limit exceeded. Please slow down.")
            return

        self._record_request(key, current_time)
        await next_handler()

    def _is_rate_limited(self, key: str, current_time: float) -> bool:
        """Check if key is rate limited using cache"""
        requests = self._request_cache[key]

        # Remove old requests
        cutoff_time = current_time - self.per
        requests[:] = [t for t in requests if t > cutoff_time]

        return len(requests) >= self.rate

    def _record_request(self, key: str, current_time: float):
        """Record a request in cache"""
        self._request_cache[key].append(current_time)

    def _cleanup_old_entries(self, current_time: float):
        """Clean up old cache entries"""
        cutoff_time = current_time - self.per

        # Clean up request logs
        for key in list(self._request_cache.keys()):
            self._request_cache[key] = [t for t in self._request_cache[key] if t > cutoff_time]

            # Remove empty entries
            if not self._request_cache[key]:
                del self._request_cache[key]

        self._last_cleanup = current_time

    def get_stats(self) -> dict:
        """Get rate limiter statistics"""
        current_time = time.time()
        active_users = 0
        total_requests = 0

        for key, requests in self._request_cache.items():
            if requests:
                # Count recent requests
                recent_requests = [t for t in requests if current_time - t < self.per]
                if recent_requests:
                    active_users += 1
                    total_requests += len(recent_requests)

        return {
            'active_users': active_users,
            'total_recent_requests': total_requests,
            'rate_limit': f"{self.rate}/{self.per}s",
            'strategy': self.strategy
        }
