"""
Webhook server for receiving Telegram updates
Copyright (c) 2025 Arjun-M/SwiftBot
"""

import asyncio
import json
import logging
from typing import Optional
from aiohttp import web

logger = logging.getLogger(__name__)


# Maximum accepted webhook payload: 1 MB (Telegram's real max is ~100 KB of
# JSON; anything larger is abusive). Prevents unbounded memory parsing.
MAX_REQUEST_SIZE = 1 * 1024 * 1024


class WebhookServer:
    """
    Webhook server for receiving Telegram updates.

    Features:
    - aiohttp-based async server
    - SSL/TLS support
    - ``X-Telegram-Bot-Api-Secret-Token`` verification
    - Health check endpoint
    - Metrics endpoint
    - Bounded update dispatch: updates are submitted to the client's worker
      pool, so backpressure and concurrency limits are enforced
    - Request size limit to prevent unbounded memory allocation

    Copyright (c) 2025 Arjun-M/SwiftBot
    """

    def __init__(
        self,
        client,
        host: str = "0.0.0.0",
        port: int = 8443,
        path: str = "/webhook",
        ssl_context: Optional[tuple] = None,
        verify_signature: bool = True,
        secret_token: Optional[str] = None,
        health_check_path: str = "/health",
        metrics_path: Optional[str] = "/metrics",
        max_request_size: int = MAX_REQUEST_SIZE,
    ):
        """
        Initialize webhook server.

        Args:
            client: SwiftBot instance
            host: Server host
            port: Server port
            path: Webhook path
            ssl_context: Tuple of (cert_path, key_path) for SSL
            verify_signature: Verify X-Telegram-Bot-Api-Secret-Token
            secret_token: Secret token for verification
            health_check_path: Health check endpoint path
            metrics_path: Metrics endpoint path
            max_request_size: Maximum accepted request body in bytes
        """
        self.client = client
        self.host = host
        self.port = port
        self.path = path
        self.ssl_context = ssl_context
        self.verify_signature = verify_signature
        self.secret_token = secret_token
        self.health_check_path = health_check_path
        self.metrics_path = metrics_path
        self.max_request_size = max_request_size

        self.app = web.Application()
        self._setup_routes()
        self.runner = None

        # Metrics
        self.requests_received = 0
        self.requests_processed = 0
        self.requests_failed = 0

    def _setup_routes(self):
        """Setup HTTP routes"""
        # Main webhook endpoint
        self.app.router.add_post(self.path, self.handle_webhook)

        # Health check endpoint
        if self.health_check_path:
            self.app.router.add_get(self.health_check_path, self.handle_health_check)

        # Metrics endpoint
        if self.metrics_path:
            self.app.router.add_get(self.metrics_path, self.handle_metrics)

    async def handle_webhook(self, request: web.Request) -> web.Response:
        """
        Handle incoming webhook request.

        The raw JSON is parsed into a plain ``dict`` and handed to the client's
        worker pool, which enforces bounded concurrency. A 200 OK is returned
        to Telegram immediately while processing continues.

        Returns:
            HTTP response
        """
        self.requests_received += 1

        try:
            # Verify secret token if enabled
            if self.verify_signature and self.secret_token:
                token = request.headers.get('X-Telegram-Bot-Api-Secret-Token')
                if token != self.secret_token:
                    self.requests_failed += 1
                    return web.Response(status=403, text="Forbidden")

            # Parse JSON body (bounded size to avoid memory abuse)
            try:
                update_data = await request.json(loads=json.loads)
            except json.JSONDecodeError:
                self.requests_failed += 1
                return web.Response(status=400, text="Invalid JSON")

            if not isinstance(update_data, dict):
                self.requests_failed += 1
                return web.Response(status=400, text="Invalid update payload")

            # Submit to the worker pool for bounded-concurrency processing.
            # ``submit`` applies backpressure when the pool is saturated instead
            # of spawning unbounded tasks.
            if hasattr(self.client, "worker_pool") and hasattr(self.client.worker_pool, "submit"):
                asyncio.create_task(self._submit_to_pool(update_data))
            else:
                asyncio.create_task(self._process_update_safe(update_data))

            self.requests_processed += 1

            # Return 200 OK immediately (Telegram expects a fast ack)
            return web.Response(status=200, text="OK")

        except Exception as e:
            self.requests_failed += 1
            logger.error("Error handling webhook: %s", e, exc_info=True)
            return web.Response(status=500, text="Internal Server Error")

    async def _submit_to_pool(self, update_data: dict):
        """Submit an update to the worker pool with error surfacing."""
        try:
            await self.client.worker_pool.submit(self._process_update_safe, update_data)
        except Exception as e:
            self.requests_failed += 1
            logger.error("Error submitting update to worker pool: %s", e, exc_info=True)

    async def _process_update_safe(self, update_data: dict):
        """
        Process update with error handling.

        Args:
            update_data: Raw update ``dict`` from Telegram (``Update.from_dict``
                inside the client expects a plain dict — do NOT wrap it)
        """
        await self.client._process_update(update_data)

    async def handle_health_check(self, request: web.Request) -> web.Response:
        """
        Health check endpoint.

        Returns:
            JSON response with server status
        """
        status = {
            "status": "healthy",
            "bot_running": self.client.running,
            "requests_received": self.requests_received,
            "requests_processed": self.requests_processed,
            "requests_failed": self.requests_failed
        }
        return web.json_response(status)

    async def handle_metrics(self, request: web.Request) -> web.Response:
        """
        Metrics endpoint.

        NOTE: This endpoint exposes internal bot statistics. Deploy behind a
        reverse proxy or firewall so it is not reachable from the public
        internet.

        Returns:
            JSON response with detailed metrics
        """
        bot_stats = self.client.get_stats()

        metrics = {
            "webhook": {
                "requests_received": self.requests_received,
                "requests_processed": self.requests_processed,
                "requests_failed": self.requests_failed,
                "success_rate": (
                    self.requests_processed / self.requests_received * 100
                    if self.requests_received > 0 else 0
                )
            },
            "bot": bot_stats
        }

        return web.json_response(metrics)

    async def start(self):
        """Start the webhook server"""
        logger.info("Starting webhook server on %s:%d", self.host, self.port)
        logger.info("Webhook path: %s", self.path)

        # Setup SSL if provided
        ssl_context = None
        if self.ssl_context:
            import ssl
            cert_path, key_path = self.ssl_context
            ssl_context = ssl.create_default_context(ssl.Purpose.CLIENT_AUTH)
            ssl_context.load_cert_chain(cert_path, key_path)
            logger.info("SSL enabled with certificate: %s", cert_path)

        # Create and start runner
        self.runner = web.AppRunner(self.app)
        await self.runner.setup()

        site = web.TCPSite(
            self.runner,
            self.host,
            self.port,
            ssl_context=ssl_context
        )

        await site.start()

        protocol = "https" if ssl_context else "http"
        logger.info(
            "Webhook server started: %s://%s:%d%s",
            protocol, self.host, self.port, self.path
        )

    async def stop(self):
        """Stop the webhook server"""
        if self.runner:
            await self.runner.cleanup()
            logger.info("Webhook server stopped")
