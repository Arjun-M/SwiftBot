"""
HTTP/2 connection pooling for maximum performance
Copyright (c) 2025 Arjun-M/SwiftBot
"""

import asyncio
import time as _time
from contextlib import asynccontextmanager
from typing import Optional, Dict, Any

import httpx

from ..exceptions.telegram import TooManyRequests


class HTTPConnectionPool:
    """
    High-performance HTTP connection pool with HTTP/2 support.

    Features:
    - Persistent keep-alive connections (reduced latency)
    - HTTP/2 multiplexing (100+ concurrent requests per connection)
    - Automatic connection recycling
    - Exponential backoff retry logic
    - Telegram ``Retry-After`` compliance (prevents bot bans)
    - Circuit breaker for fault tolerance
    - Multipart file upload support

    Copyright (c) 2025 Arjun-M/SwiftBot
    """

    def __init__(
        self,
        max_connections: int = 100,
        max_keepalive_connections: int = 50,
        keepalive_expiry: float = 30.0,
        timeout: float = 30.0,
        connect_timeout: float = 10.0,
        enable_http2: bool = True,
        max_retries: int = 3,
        backoff_factor: float = 0.5,
    ):
        self.max_connections = max_connections
        self.max_keepalive = max_keepalive_connections
        self.enable_http2 = enable_http2
        self.max_retries = max_retries
        self.backoff_factor = backoff_factor

        self.limits = httpx.Limits(
            max_connections=max_connections,
            max_keepalive_connections=max_keepalive_connections,
            keepalive_expiry=keepalive_expiry
        )

        self.timeout = httpx.Timeout(
            timeout=timeout,
            connect=connect_timeout,
            read=timeout,
            write=timeout,
            pool=timeout
        )

        # The pool transport handles transient network errors; HTTP-layer
        # retry logic (429/5xx) now lives in ``request()`` where we can
        # honor Telegram's ``Retry-After`` header.
        self.transport = httpx.AsyncHTTPTransport(
            http2=enable_http2,
            limits=self.limits
        )

        self._client: Optional[httpx.AsyncClient] = None
        self._lock = asyncio.Lock()

        # Circuit breaker state
        self._failures = 0
        self._circuit_open = False
        self._circuit_threshold = 5
        self._circuit_reset_time = 60
        self._last_failure_time = 0

    async def initialize(self):
        """Initialize the HTTP client"""
        if self._client is None:
            self._client = httpx.AsyncClient(
                http2=self.enable_http2,
                limits=self.limits,
                timeout=self.timeout,
                transport=self.transport,
                follow_redirects=True
            )

    async def close(self):
        """Close the HTTP client and cleanup connections"""
        if self._client:
            await self._client.aclose()
            self._client = None

    def _check_circuit_breaker(self):
        """
        Check circuit breaker state.
        Opens circuit after threshold failures, closes after timeout.
        """
        if self._circuit_open:
            if _time.time() - self._last_failure_time > self._circuit_reset_time:
                self._circuit_open = False
                self._failures = 0
                return False
            return True
        return False

    def _parse_retry_after(self, response: httpx.Response) -> Optional[float]:
        """Read Telegram's ``Retry-After`` header (in seconds) if present."""
        header = response.headers.get("retry-after")
        if header:
            try:
                return float(header)
            except (TypeError, ValueError):
                return None
        return None

    async def request(
        self,
        method: str,
        url: str,
        retry_on_status: list = None,
        respect_retry_after: bool = True,
        **kwargs
    ) -> httpx.Response:
        """
        Make HTTP request with automatic retry and circuit breaker.

        Retries 429 (respecting Telegram's ``Retry-After`` header/parameter)
        and transient 5xx server errors with exponential backoff. Raises
        ``TooManyRequests`` (a typed ``TelegramError``) once the retry
        budget is exhausted on a 429, so bot code can catch it precisely.

        Args:
            method: HTTP method (GET, POST, etc.)
            url: Request URL
            retry_on_status: Status codes to retry on
            respect_retry_after: Pause for ``Retry-After`` on 429 responses
            **kwargs: Additional request parameters (``files=`` for multipart
                uploads is passed straight through to httpx)

        Returns:
            HTTP response

        Raises:
            TooManyRequests: Rate limit retries exhausted (with retry_after)
            Exception: Circuit breaker open or max retries exceeded
        """
        if self._check_circuit_breaker():
            raise Exception("Circuit breaker is open")

        if retry_on_status is None:
            retry_on_status = [429, 500, 502, 503, 504]

        await self.initialize()

        for attempt in range(self.max_retries):
            try:
                response = await self._client.request(method, url, **kwargs)

                # Reset failure counter on success
                if response.status_code < 500:
                    self._failures = 0

                if response.status_code == 429:
                    retry_after = self._parse_retry_after(response)
                    if respect_retry_after and retry_after is not None:
                        if attempt == self.max_retries - 1:
                            raise TooManyRequests(
                                retry_after=int(retry_after),
                                description="Too Many Requests: retry after",
                            )
                        # Telegram dictates exactly how long to wait before
                        # retrying. Sleeping once and retrying once is enough:
                        # if the API is still throttling, the caller should
                        # see the concrete ``TooManyRequests`` error.
                        await asyncio.sleep(retry_after)
                        continue
                    if attempt < self.max_retries - 1:
                        await asyncio.sleep(self.backoff_factor * (2 ** attempt))
                        continue
                    seconds = int(retry_after) if retry_after else None
                    raise TooManyRequests(retry_after=seconds, description="Too Many Requests: retry after")

                if response.status_code in retry_on_status:
                    if attempt < self.max_retries - 1:
                        await asyncio.sleep(self.backoff_factor * (2 ** attempt))
                        continue
                    # Last attempt: surface the real status code to the caller
                    # so ``TelegramAPI`` can raise a typed error.
                    return response

                return response

            except TooManyRequests:
                raise
            except Exception as e:
                self._failures += 1
                self._last_failure_time = _time.time()

                if self._failures >= self._circuit_threshold:
                    self._circuit_open = True

                if attempt < self.max_retries - 1:
                    await asyncio.sleep(self.backoff_factor * (2 ** attempt))
                    continue

                raise e

        raise Exception(f"Max retries ({self.max_retries}) exceeded")

    async def get(self, url: str, **kwargs):
        """GET request"""
        return await self.request("GET", url, **kwargs)

    async def post(self, url: str, **kwargs):
        """POST request (``files=`` keyword enables multipart upload)"""
        return await self.request("POST", url, **kwargs)

    @property
    def client(self) -> Optional[httpx.AsyncClient]:
        """Expose the underlying httpx client for direct multipart requests."""
        return self._client

    @asynccontextmanager
    async def stream(self, method: str, url: str, **kwargs):
        """
        Stream response for large files or data.

        Usage:
            async with pool.stream("GET", url) as response:
                async for chunk in response.aiter_bytes():
                    process(chunk)
        """
        await self.initialize()
        async with self._client.stream(method, url, **kwargs) as response:
            yield response

    def get_stats(self) -> Dict[str, Any]:
        return {
            "max_connections": self.max_connections,
            "max_keepalive": self.max_keepalive,
            "http2_enabled": self.enable_http2,
            "failures": self._failures,
            "circuit_open": self._circuit_open,
        }

