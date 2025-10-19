"""
Webhook server for receiving Telegram updates
Copyright (c) 2025 Arjun-M/SwiftBot
"""

import asyncio
import json
import hmac
import hashlib
from typing import Optional, Callable
from aiohttp import web


class WebhookServer:
    """
    Production-ready webhook server for receiving Telegram updates.

    Features:
    - AIOHTTP-based async server
    - SSL/TLS support
    - Signature verification
    - Health check endpoint
    - Metrics endpoint
    - Request logging

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

        Args:
            request: AIOHTTP request object

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

            # Parse JSON body
            try:
                update_data = await request.json()
            except json.JSONDecodeError:
                self.requests_failed += 1
                return web.Response(status=400, text="Invalid JSON")

            # Process update asynchronously
            asyncio.create_task(self._process_update_safe(update_data))

            self.requests_processed += 1

            # Return 200 OK immediately
            return web.Response(status=200, text="OK")

        except Exception as e:
            self.requests_failed += 1
            print(f"Error handling webhook: {e}")
            return web.Response(status=500, text="Internal Server Error")

    async def _process_update_safe(self, update_data: dict):
        """
        Process update with error handling.

        Args:
            update_data: Update data from Telegram
        """
        try:
            # Convert dict to object-like structure
            class UpdateObj:
                def __init__(self, data):
                    self.__dict__.update(data)
                    # Handle nested objects
                    for key, value in data.items():
                        if isinstance(value, dict):
                            setattr(self, key, UpdateObj(value))

            update = UpdateObj(update_data)
            await self.client._process_update(update)

        except Exception as e:
            print(f"Error processing update: {e}")

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
        print(f"Starting webhook server on {self.host}:{self.port}")
        print(f"Webhook path: {self.path}")
        print(f"Health check: {self.health_check_path}")

        # Setup SSL if provided
        ssl_context = None
        if self.ssl_context:
            import ssl
            cert_path, key_path = self.ssl_context
            ssl_context = ssl.create_default_context(ssl.Purpose.CLIENT_AUTH)
            ssl_context.load_cert_chain(cert_path, key_path)
            print(f"SSL enabled with certificate: {cert_path}")

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
        print(f"Webhook server started: {protocol}://{self.host}:{self.port}{self.path}")
        print("Press Ctrl+C to stop")

    async def stop(self):
        """Stop the webhook server"""
        if self.runner:
            await self.runner.cleanup()
            print("Webhook server stopped")

