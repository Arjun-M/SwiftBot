"""
SwiftBot - Main client class
Copyright (c) 2025 Arjun-M/SwiftBot
"""

import asyncio
import logging
from typing import Optional, Dict, List, Callable, Any
from .router import CommandRouter
from .context import Context
from .connection.pool import HTTPConnectionPool
from .connection.worker import WorkerPool
from .api.telegram import TelegramAPI
from .types import EventType
from .update_types import Update

# Set up logger
logger = logging.getLogger(__name__)


class SwiftBot:
    """
    SwiftBot - Ultra-fast Telegram bot framework.

    Features:
    - 30× faster command routing with Trie data structure
    - HTTP/2 connection pooling for maximum throughput
    - Worker pool for concurrent update processing
    - Telethon-inspired decorator syntax
    - Enterprise-grade middleware system
    - Multiple storage backends (Redis, PostgreSQL, MongoDB, File)
    - Broadcast system with progress tracking

    Example:
        client = SwiftBot(token="YOUR_TOKEN", worker_pool_size=50)

        @client.on(Message(pattern=r"^/start"))
        async def start(ctx):
            await ctx.reply("Hello!")

        await client.run()

    Copyright (c) 2025 Arjun-M/SwiftBot
    """

    def __init__(
        self,
        token: str,
        parse_mode: str = "HTML",
        async_mode: bool = True,
        worker_pool_size: int = 50,
        max_connections: int = 100,
        timeout: float = 30.0,
        enable_http2: bool = True,
        api_base_url: str = "https://api.telegram.org",
        connection_pool: Optional[Dict] = None,
        retry_config: Optional[Dict] = None,
        rate_limiter: Optional[Dict] = None,
        debug: bool = False,
    ):
        """
        Initialize SwiftBot client.

        Args:
            token: Bot token from @BotFather
            parse_mode: Default parse mode (HTML, Markdown, MarkdownV2)
            async_mode: Use async mode (recommended)
            worker_pool_size: Number of concurrent workers
            max_connections: Maximum HTTP connections
            timeout: Request timeout in seconds
            enable_http2: Enable HTTP/2 support
            api_base_url: Telegram API base URL
            connection_pool: Advanced connection pool config
            retry_config: Retry configuration
            rate_limiter: Rate limiter configuration
            debug: Enable debug logging
        """
        self.token = token
        self.parse_mode = parse_mode
        self.async_mode = async_mode
        self.api_base_url = api_base_url
        self.debug = debug

        # Set up logging
        if debug:
            logging.basicConfig(level=logging.DEBUG)
        else:
            logging.basicConfig(level=logging.INFO)

        # Initialize connection pool
        pool_config = connection_pool or {}
        self.connection_pool = HTTPConnectionPool(
            max_connections=pool_config.get('max_connections', max_connections),
            max_keepalive_connections=pool_config.get('max_keepalive_connections', 50),
            keepalive_expiry=pool_config.get('keepalive_expiry', 30.0),
            timeout=timeout,
            enable_http2=enable_http2,
            max_retries=retry_config.get('max_retries', 3) if retry_config else 3,
            backoff_factor=retry_config.get('backoff_factor', 0.5) if retry_config else 0.5,
        )

        # Initialize worker pool
        self.worker_pool = WorkerPool(
            num_workers=worker_pool_size,
            max_queue_size=1000,
            enable_dead_letter=True
        )

        # Initialize Telegram API
        self.api = TelegramAPI(token, self.connection_pool, api_base_url)

        # Initialize router
        self.router = CommandRouter()

        # Middleware chain
        self.middleware: List = []

        # Running state
        self.running = False
        self._update_offset = 0

        # Bot info cache
        self._bot_info = None

        # Statistics
        self._stats = {
            'updates_processed': 0,
            'errors_handled': 0,
            'handlers_executed': 0,
            'start_time': None
        }

    def on(self, event_type: EventType, priority: int = 0):
        """
        Decorator for registering event handlers.

        Example:
            @client.on(Message(text="hello"))
            async def handler(ctx):
                await ctx.reply("Hi!")

        Args:
            event_type: Event type instance (Message, CallbackQuery, etc.)
            priority: Handler priority (higher = executed first)

        Returns:
            Decorator function
        """
        def decorator(func: Callable):
            try:
                self.router.add_handler(event_type, func, priority)
                logger.debug(f"Registered handler {func.__name__} with priority {priority}")
                return func
            except Exception as e:
                logger.error(f"Error registering handler {func.__name__}: {e}")
                raise

        return decorator

    def use(self, middleware):
        """
        Register middleware.

        Example:
            from SwiftBot.middleware import Logger
            client.use(Logger(level="INFO"))

        Args:
            middleware: Middleware instance
        """
        self.middleware.append(middleware)
        logger.info(f"Registered middleware: {type(middleware).__name__}")

    async def get_me(self):
        """
        Get bot information.

        Returns:
            Bot user object
        """
        if not self._bot_info:
            self._bot_info = await self.api.get_me()
        return self._bot_info

    async def _process_update(self, raw_update: Dict):
        """
        Process a single update through router and middleware.
        FIXED: Properly create Update object and handle all update types.

        Args:
            raw_update: Raw update dictionary from Telegram API
        """
        try:
            # Create proper Update object from raw data
            update = Update.from_dict(raw_update)

            # Determine update type and get the specific update object
            update_type = update.get_update_type()
            update_obj = update.get_update_object()

            if not update_type or not update_obj:
                logger.warning(f"Unknown update type: {raw_update}")
                return

            logger.debug(f"Processing {update_type} update")

            # Route to handler
            handler, match, event_type = await self.router.route(update_obj, update_type)

            if not handler:
                logger.debug(f"No handler found for {update_type}")
                return

            # Create context with proper parameters
            ctx = Context(self, update, update_obj, match)

            # Execute middleware chain and handler
            await self._execute_middleware_chain(ctx, handler)

            self._stats['updates_processed'] += 1
            self._stats['handlers_executed'] += 1

        except Exception as e:
            logger.error(f"Error processing update: {e}")
            self._stats['errors_handled'] += 1

            # Try to execute error handlers in middleware
            try:
                for middleware in self.middleware:
                    if hasattr(middleware, 'on_error'):
                        await middleware.on_error(None, e)
            except:
                pass

    async def _execute_middleware_chain(self, ctx: Context, handler: Callable):
        """
        Execute middleware chain and handler.

        Args:
            ctx: Context object
            handler: Final handler function
        """
        middleware_iter = iter(self.middleware)

        async def next_handler():
            """Call next middleware or final handler"""
            try:
                middleware = next(middleware_iter)
                if hasattr(middleware, 'on_update'):
                    await middleware.on_update(ctx, next_handler)
                else:
                    # Skip middleware without on_update method
                    await next_handler()
            except StopIteration:
                # No more middleware, call final handler
                try:
                    await handler(ctx)
                except Exception as e:
                    logger.error(f"Error in handler {handler.__name__}: {e}")
                    raise

        try:
            await next_handler()
        except Exception as e:
            # Call error handlers in middleware
            for middleware in self.middleware:
                try:
                    if hasattr(middleware, 'on_error'):
                        await middleware.on_error(ctx, e)
                except Exception as middleware_error:
                    logger.error(f"Error in middleware error handler: {middleware_error}")

            # Re-raise if not handled
            raise

    async def run_polling(
        self,
        timeout: int = 30,
        limit: int = 100,
        drop_pending_updates: bool = False,
        allowed_updates: Optional[List[str]] = None,
        backoff_factor: float = 0.5,
        max_backoff: float = 60,
        circuit_breaker_threshold: int = 5,
        circuit_breaker_timeout: int = 60,
    ):
        """
        Start bot in polling mode (long polling).

        Args:
            timeout: Long polling timeout
            limit: Updates per request
            drop_pending_updates: Drop pending updates on start
            allowed_updates: Update types to receive
            backoff_factor: Exponential backoff factor
            max_backoff: Maximum backoff time
            circuit_breaker_threshold: Failed requests before circuit break
            circuit_breaker_timeout: Circuit breaker reset time
        """
        if self.running:
            raise RuntimeError("Bot is already running")

        self.running = True
        self._stats['start_time'] = asyncio.get_event_loop().time()

        try:
            # Start worker pool
            await self.worker_pool.start()

            # Get bot info
            bot_info = await self.get_me()
            logger.info(f"Bot started: @{bot_info.get('username', 'Unknown')}")
            logger.info(f"Worker pool: {self.worker_pool.num_workers} workers")
            logger.info(f"Connection pool: {self.connection_pool.max_connections} connections")
            logger.info(f"HTTP/2: {'enabled' if self.connection_pool.enable_http2 else 'disabled'}")

            # Drop pending updates if requested
            if drop_pending_updates:
                await self.api.get_updates(offset=-1)
                logger.info("Dropped pending updates")

            consecutive_failures = 0
            backoff_time = 0

            # Main polling loop
            while self.running:
                try:
                    # Get updates
                    updates = await self.api.get_updates(
                        offset=self._update_offset,
                        limit=limit,
                        timeout=timeout,
                        allowed_updates=allowed_updates,
                    )

                    # Reset failure counter on success
                    consecutive_failures = 0
                    backoff_time = 0

                    # Process updates
                    for update in updates:
                        try:
                            # Update offset
                            self._update_offset = update.get('update_id', 0) + 1

                            # Submit to worker pool
                            await self.worker_pool.submit(self._process_update, update)

                        except Exception as e:
                            logger.error(f"Error submitting update to worker pool: {e}")

                except Exception as e:
                    consecutive_failures += 1
                    logger.error(f"Error in polling loop: {e}")

                    # Circuit breaker
                    if consecutive_failures >= circuit_breaker_threshold:
                        logger.warning(f"Circuit breaker opened after {consecutive_failures} failures")
                        await asyncio.sleep(circuit_breaker_timeout)
                        consecutive_failures = 0
                        continue

                    # Exponential backoff
                    backoff_time = min(
                        backoff_factor * (2 ** consecutive_failures),
                        max_backoff
                    )
                    logger.info(f"Retrying in {backoff_time}s after error: {e}")
                    await asyncio.sleep(backoff_time)

        except KeyboardInterrupt:
            logger.info("Received KeyboardInterrupt, stopping...")
        except Exception as e:
            logger.error(f"Fatal error in polling: {e}")
            raise
        finally:
            # Cleanup
            self.running = False
            await self.worker_pool.stop()
            await self.connection_pool.close()
            logger.info("Bot stopped")

    async def run_webhook(
        self,
        host: str = "0.0.0.0",
        port: int = 8443,
        webhook_url: str = None,
        cert_path: Optional[str] = None,
        key_path: Optional[str] = None,
        drop_pending_updates: bool = True,
        secret_token: Optional[str] = None,
        allowed_updates: Optional[List[str]] = None,
    ):
        """
        Start bot in webhook mode.

        Args:
            host: Server host
            port: Server port
            webhook_url: Public webhook URL
            cert_path: SSL certificate path
            key_path: SSL key path
            drop_pending_updates: Drop pending updates
            secret_token: Webhook secret token
            allowed_updates: Update types to receive
        """
        if not webhook_url:
            raise ValueError("webhook_url is required for webhook mode")

        if self.running:
            raise RuntimeError("Bot is already running")

        self.running = True
        self._stats['start_time'] = asyncio.get_event_loop().time()

        try:
            # Start worker pool
            await self.worker_pool.start()

            # Set webhook
            logger.info(f"Setting webhook: {webhook_url}")
            await self.api.set_webhook(
                url=webhook_url,
                max_connections=self.worker_pool.num_workers,
                allowed_updates=allowed_updates,
                drop_pending_updates=drop_pending_updates,
                secret_token=secret_token,
            )

            # Start webhook server
            from .webhook import WebhookServer
            server = WebhookServer(
                client=self,
                host=host,
                port=port,
                ssl_context=(cert_path, key_path) if cert_path else None,
                secret_token=secret_token,
            )

            await server.start()
            logger.info(f"Webhook server started on {host}:{port}")

            # Keep running
            while self.running:
                await asyncio.sleep(1)

        except KeyboardInterrupt:
            logger.info("Received KeyboardInterrupt, stopping...")
        except Exception as e:
            logger.error(f"Fatal error in webhook mode: {e}")
            raise
        finally:
            if 'server' in locals():
                await server.stop()
            await self.worker_pool.stop()
            await self.connection_pool.close()
            logger.info("Bot stopped")

    async def run(
        self,
        mode: str = "polling",
        **kwargs
    ):
        """
        Start bot in specified mode.

        Args:
            mode: "polling" or "webhook"
            **kwargs: Mode-specific arguments
        """
        if mode == "polling":
            await self.run_polling(**kwargs)
        elif mode == "webhook":
            await self.run_webhook(**kwargs)
        else:
            raise ValueError(f"Invalid mode: {mode}. Use 'polling' or 'webhook'")

    def stop(self):
        """Stop the bot"""
        self.running = False
        logger.info("Bot stop requested")

    def get_stats(self) -> Dict:
        """
        Get bot statistics.

        Returns:
            Dictionary with statistics
        """
        current_time = asyncio.get_event_loop().time()
        uptime = current_time - self._stats['start_time'] if self._stats['start_time'] else 0

        return {
            "running": self.running,
            "uptime_seconds": uptime,
            "updates_processed": self._stats['updates_processed'],
            "errors_handled": self._stats['errors_handled'],
            "handlers_executed": self._stats['handlers_executed'],
            "worker_pool": self.worker_pool.get_stats() if hasattr(self.worker_pool, 'get_stats') else {},
            "connection_pool": self.connection_pool.get_stats() if hasattr(self.connection_pool, 'get_stats') else {},
            "router": self.router.get_stats(),
            "middleware_count": len(self.middleware),
        }
