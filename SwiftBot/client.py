"""
SwiftBot - Main client class
Copyright (c) 2025 Arjun-M/SwiftBot
"""


import asyncio
from typing import Optional, Dict, List, Callable, Any
from .router import CommandRouter
from .context import Context
from .connection.pool import HTTPConnectionPool
from .connection.worker import WorkerPool
from .api.telegram import TelegramAPI
from .types import EventType
from .update_types import Update
from .exceptions import SwiftBotException, SwiftBotError, ConfigurationError
from .exceptions.handlers import CentralizedExceptionHandler

# Remove excessive logging - let middleware handle it
import logging
logging.getLogger("httpx").setLevel(logging.WARNING)
logging.getLogger("http.client").setLevel(logging.WARNING)


class SwiftBot:
    """
    SwiftBot - Ultra-fast Telegram bot framework with enhanced error handling.

    Features:
    - 30× faster command routing with Trie data structure
    - HTTP/2 connection pooling for maximum throughput
    - Worker pool for concurrent update processing
    - Telethon-inspired decorator syntax
    - Enterprise-grade middleware system
    - Multiple storage backends (Redis, PostgreSQL, MongoDB, File)
    - Broadcast system with progress tracking
    - Centralized exception handling
    - Optimized logging through middleware

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
        enable_centralized_exceptions: bool = True,
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
            debug: Enable debug mode (handled by middleware)
            enable_centralized_exceptions: Enable centralized exception handling
        """
        # Validate token
        if not token or not isinstance(token, str):
            raise ConfigurationError("Bot token is required and must be a string")

        if not token.strip():
            raise ConfigurationError("Bot token cannot be empty")

        self.token = token.strip()
        self.parse_mode = parse_mode
        self.async_mode = async_mode
        self.api_base_url = api_base_url
        self.debug = debug

        # Initialize centralized exception handler
        self.exception_handler = CentralizedExceptionHandler() if enable_centralized_exceptions else None

        # Initialize connection pool with validation
        pool_config = connection_pool or {}
        try:
            self.connection_pool = HTTPConnectionPool(
                max_connections=pool_config.get('max_connections', max_connections),
                max_keepalive_connections=pool_config.get('max_keepalive_connections', 50),
                keepalive_expiry=pool_config.get('keepalive_expiry', 30.0),
                timeout=timeout,
                enable_http2=enable_http2,
                max_retries=retry_config.get('max_retries', 3) if retry_config else 3,
                backoff_factor=retry_config.get('backoff_factor', 0.5) if retry_config else 0.5,
            )
        except Exception as e:
            raise ConfigurationError(f"Failed to initialize connection pool: {e}")

        # Initialize worker pool with validation
        try:
            self.worker_pool = WorkerPool(
                num_workers=worker_pool_size,
                max_queue_size=1000,
                enable_dead_letter=True
            )
        except Exception as e:
            raise ConfigurationError(f"Failed to initialize worker pool: {e}")

        # Initialize Telegram API
        try:
            self.api = TelegramAPI(token, self.connection_pool, api_base_url)
        except Exception as e:
            raise ConfigurationError(f"Failed to initialize Telegram API: {e}")

        # Initialize router
        self.router = CommandRouter()

        # Middleware chain
        self.middleware: List = []

        # Running state
        self.running = False
        self._update_offset = 0

        # Bot info cache with TTL
        self._bot_info = None
        self._bot_info_expires = 0

        # Statistics
        self._stats = {
            'updates_processed': 0,
            'errors_handled': 0,
            'handlers_executed': 0,
            'start_time': None,
            'exceptions_by_type': {},
            'performance_metrics': {}
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
                return func
            except Exception as e:
                if self.exception_handler:
                    self.exception_handler.handle_exception(e, context="handler_registration")
                raise SwiftBotError(f"Error registering handler {func.__name__}: {e}")

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
        try:
            self.middleware.append(middleware)
        except Exception as e:
            if self.exception_handler:
                self.exception_handler.handle_exception(e, context="middleware_registration")
            raise SwiftBotError(f"Error registering middleware: {e}")

    async def get_me(self, use_cache: bool = True):
        """
        Get bot information with caching.

        Args:
            use_cache: Whether to use cached bot info

        Returns:
            Bot user object
        """
        current_time = asyncio.get_event_loop().time()

        if use_cache and self._bot_info and current_time < self._bot_info_expires:
            return self._bot_info

        try:
            self._bot_info = await self.api.get_me()
            self._bot_info_expires = current_time + 300  # Cache for 5 minutes
            return self._bot_info
        except Exception as e:
            if self.exception_handler:
                self.exception_handler.handle_exception(e, context="get_me")
            raise SwiftBotError(f"Failed to get bot info: {e}")

    async def _handle_exception(self, exception: Exception, context: str = "unknown"):
        """Handle exceptions through centralized handler"""
        if self.exception_handler:
            await self.exception_handler.handle_exception_async(exception, context)

        # Update statistics
        exc_type = type(exception).__name__
        self._stats['exceptions_by_type'][exc_type] = self._stats['exceptions_by_type'].get(exc_type, 0) + 1
        self._stats['errors_handled'] += 1

    async def _process_update(self, raw_update: Dict):
        """
        Process a single update through router and middleware with enhanced error handling.

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
                await self._handle_exception(
                    SwiftBotError(f"Unknown update type: {raw_update}"),
                    "update_processing"
                )
                return

            # Route to handler
            handler, match, event_type = await self.router.route(update_obj, update_type)

            if not handler:
                # This is normal, not an error
                return

            # Create context with proper parameters
            ctx = Context(self, update, update_obj, match)

            # Execute middleware chain and handler
            await self._execute_middleware_chain(ctx, handler)

            self._stats['updates_processed'] += 1
            self._stats['handlers_executed'] += 1

        except Exception as e:
            await self._handle_exception(e, "update_processing")

            # Try to execute error handlers in middleware
            try:
                for middleware in self.middleware:
                    if hasattr(middleware, 'on_error'):
                        await middleware.on_error(None, e)
            except Exception as middleware_error:
                await self._handle_exception(middleware_error, "middleware_error_handling")

    async def _execute_middleware_chain(self, ctx: Context, handler: Callable):
        """
        Execute middleware chain and handler with improved error handling.

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
                    await self._handle_exception(e, f"handler_{handler.__name__}")
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
                    await self._handle_exception(middleware_error, "middleware_error_handler")

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
        Start bot in polling mode with enhanced error handling.

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
            raise SwiftBotError("Bot is already running")

        self.running = True
        self._stats['start_time'] = asyncio.get_event_loop().time()

        try:
            # Start worker pool
            await self.worker_pool.start()

            # Get bot info
            bot_info = await self.get_me()

            # Drop pending updates if requested
            if drop_pending_updates:
                try:
                    await self.api.get_updates(offset=-1)
                except Exception as e:
                    await self._handle_exception(e, "drop_pending_updates")

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
                            await self._handle_exception(e, "update_submission")

                except Exception as e:
                    consecutive_failures += 1
                    await self._handle_exception(e, "polling_loop")

                    # Circuit breaker
                    if consecutive_failures >= circuit_breaker_threshold:
                        await asyncio.sleep(circuit_breaker_timeout)
                        consecutive_failures = 0
                        continue

                    # Exponential backoff
                    backoff_time = min(
                        backoff_factor * (2 ** consecutive_failures),
                        max_backoff
                    )
                    await asyncio.sleep(backoff_time)

        except KeyboardInterrupt:
            pass  # Graceful shutdown
        except Exception as e:
            await self._handle_exception(e, "polling_fatal")
            raise SwiftBotError(f"Fatal error in polling: {e}")
        finally:
            # Cleanup
            self.running = False
            await self.worker_pool.stop()
            await self.connection_pool.close()

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
        Start bot in webhook mode with enhanced error handling.
        """
        if not webhook_url:
            raise ConfigurationError("webhook_url is required for webhook mode")

        if self.running:
            raise SwiftBotError("Bot is already running")

        self.running = True
        self._stats['start_time'] = asyncio.get_event_loop().time()

        try:
            # Start worker pool
            await self.worker_pool.start()

            # Set webhook
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

            # Keep running
            while self.running:
                await asyncio.sleep(1)

        except KeyboardInterrupt:
            pass  # Graceful shutdown
        except Exception as e:
            await self._handle_exception(e, "webhook_fatal")
            raise SwiftBotError(f"Fatal error in webhook mode: {e}")
        finally:
            if 'server' in locals():
                await server.stop()
            await self.worker_pool.stop()
            await self.connection_pool.close()

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
            raise ConfigurationError(f"Invalid mode: {mode}. Use 'polling' or 'webhook'")

    def stop(self):
        """Stop the bot"""
        self.running = False

    def get_stats(self) -> Dict:
        """
        Get bot statistics with enhanced metrics.

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
            "exceptions_by_type": self._stats['exceptions_by_type'],
            "worker_pool": self.worker_pool.get_stats() if hasattr(self.worker_pool, 'get_stats') else {},
            "connection_pool": self.connection_pool.get_stats() if hasattr(self.connection_pool, 'get_stats') else {},
            "router": self.router.get_stats(),
            "middleware_count": len(self.middleware),
            "bot_info_cached": self._bot_info is not None,
        }      

    # ===========================================
    # TELEGRAM API FORWARDING METHODS
    # This allows using client.send_message() instead of client.api.send_message()
    # Can be called from main thread, startup, or anywhere outside decorators
    # ===========================================

    async def get_me(self):
        """Get bot information (cached)"""
        if not self._bot_info:
            self._bot_info = await self.api.get_me()
        return self._bot_info

    async def get_updates(self, offset: Optional[int] = None, limit: int = 100, 
                         timeout: int = 0, allowed_updates: Optional[List[str]] = None):
        """Get pending updates"""
        return await self.api.get_updates(offset, limit, timeout, allowed_updates)

    async def log_out(self):
        """Log out from cloud Bot API server"""
        return await self.api.log_out()

    async def close(self):
        """Close bot instance"""
        return await self.api.close()

    # ============= Messaging =============

    async def send_message(self, chat_id: int, text: str, parse_mode: Optional[str] = None,
                          entities: Optional[List] = None, disable_web_page_preview: bool = False,
                          disable_notification: bool = False, protect_content: bool = False,
                          reply_to_message_id: Optional[int] = None, 
                          allow_sending_without_reply: bool = False,
                          reply_markup: Optional[Dict] = None):
        """Send text message"""
        return await self.api.send_message(
            chat_id=chat_id, text=text, parse_mode=parse_mode or self.parse_mode,
            entities=entities, disable_web_page_preview=disable_web_page_preview,
            disable_notification=disable_notification, protect_content=protect_content,
            reply_to_message_id=reply_to_message_id,
            allow_sending_without_reply=allow_sending_without_reply,
            reply_markup=reply_markup
        )

    async def forward_message(self, chat_id: int, from_chat_id: int, message_id: int,
                             disable_notification: bool = False, protect_content: bool = False):
        """Forward message"""
        return await self.api.forward_message(chat_id, from_chat_id, message_id,
                                              disable_notification, protect_content)

    async def copy_message(self, chat_id: int, from_chat_id: int, message_id: int,
                          caption: Optional[str] = None, parse_mode: Optional[str] = None,
                          caption_entities: Optional[List] = None,
                          disable_notification: bool = False, protect_content: bool = False,
                          reply_to_message_id: Optional[int] = None,
                          allow_sending_without_reply: bool = False,
                          reply_markup: Optional[Dict] = None):
        """Copy message"""
        return await self.api.copy_message(
            chat_id, from_chat_id, message_id, caption, parse_mode or self.parse_mode,
            caption_entities, disable_notification, protect_content, reply_to_message_id,
            allow_sending_without_reply, reply_markup
        )

    # ============= Media =============

    async def send_photo(self, chat_id: int, photo, caption: Optional[str] = None,
                        parse_mode: Optional[str] = None, caption_entities: Optional[List] = None,
                        disable_notification: bool = False, protect_content: bool = False,
                        reply_to_message_id: Optional[int] = None,
                        allow_sending_without_reply: bool = False,
                        reply_markup: Optional[Dict] = None):
        """Send photo"""
        return await self.api.send_photo(
            chat_id, photo, caption, parse_mode or self.parse_mode, caption_entities,
            disable_notification, protect_content, reply_to_message_id,
            allow_sending_without_reply, reply_markup
        )

    async def send_audio(self, chat_id: int, audio, caption: Optional[str] = None,
                        parse_mode: Optional[str] = None, caption_entities: Optional[List] = None,
                        duration: Optional[int] = None, performer: Optional[str] = None,
                        title: Optional[str] = None, thumb = None,
                        disable_notification: bool = False, protect_content: bool = False,
                        reply_to_message_id: Optional[int] = None,
                        allow_sending_without_reply: bool = False,
                        reply_markup: Optional[Dict] = None):
        """Send audio"""
        return await self.api.send_audio(
            chat_id, audio, caption, parse_mode or self.parse_mode, caption_entities,
            duration, performer, title, thumb, disable_notification, protect_content,
            reply_to_message_id, allow_sending_without_reply, reply_markup
        )

    async def send_document(self, chat_id: int, document, thumb = None,
                           caption: Optional[str] = None, parse_mode: Optional[str] = None,
                           caption_entities: Optional[List] = None,
                           disable_content_type_detection: bool = False,
                           disable_notification: bool = False, protect_content: bool = False,
                           reply_to_message_id: Optional[int] = None,
                           allow_sending_without_reply: bool = False,
                           reply_markup: Optional[Dict] = None):
        """Send document"""
        return await self.api.send_document(
            chat_id, document, thumb, caption, parse_mode or self.parse_mode,
            caption_entities, disable_content_type_detection, disable_notification,
            protect_content, reply_to_message_id, allow_sending_without_reply, reply_markup
        )

    async def send_video(self, chat_id: int, video, duration: Optional[int] = None,
                        width: Optional[int] = None, height: Optional[int] = None,
                        thumb = None, caption: Optional[str] = None,
                        parse_mode: Optional[str] = None, caption_entities: Optional[List] = None,
                        supports_streaming: bool = False, disable_notification: bool = False,
                        protect_content: bool = False, reply_to_message_id: Optional[int] = None,
                        allow_sending_without_reply: bool = False,
                        reply_markup: Optional[Dict] = None):
        """Send video"""
        return await self.api.send_video(
            chat_id, video, duration, width, height, thumb, caption,
            parse_mode or self.parse_mode, caption_entities, supports_streaming,
            disable_notification, protect_content, reply_to_message_id,
            allow_sending_without_reply, reply_markup
        )

    async def send_animation(self, chat_id: int, animation, duration: Optional[int] = None,
                            width: Optional[int] = None, height: Optional[int] = None,
                            thumb = None, caption: Optional[str] = None,
                            parse_mode: Optional[str] = None,
                            caption_entities: Optional[List] = None,
                            disable_notification: bool = False, protect_content: bool = False,
                            reply_to_message_id: Optional[int] = None,
                            allow_sending_without_reply: bool = False,
                            reply_markup: Optional[Dict] = None):
        """Send animation"""
        return await self.api.send_animation(
            chat_id, animation, duration, width, height, thumb, caption,
            parse_mode or self.parse_mode, caption_entities, disable_notification,
            protect_content, reply_to_message_id, allow_sending_without_reply, reply_markup
        )

    async def send_voice(self, chat_id: int, voice, caption: Optional[str] = None,
                        parse_mode: Optional[str] = None, caption_entities: Optional[List] = None,
                        duration: Optional[int] = None, disable_notification: bool = False,
                        protect_content: bool = False, reply_to_message_id: Optional[int] = None,
                        allow_sending_without_reply: bool = False,
                        reply_markup: Optional[Dict] = None):
        """Send voice message"""
        return await self.api.send_voice(
            chat_id, voice, caption, parse_mode or self.parse_mode, caption_entities,
            duration, disable_notification, protect_content, reply_to_message_id,
            allow_sending_without_reply, reply_markup
        )

    async def send_video_note(self, chat_id: int, video_note, duration: Optional[int] = None,
                             length: Optional[int] = None, thumb = None,
                             disable_notification: bool = False, protect_content: bool = False,
                             reply_to_message_id: Optional[int] = None,
                             allow_sending_without_reply: bool = False,
                             reply_markup: Optional[Dict] = None):
        """Send video note"""
        return await self.api.send_video_note(
            chat_id, video_note, duration, length, thumb, disable_notification,
            protect_content, reply_to_message_id, allow_sending_without_reply, reply_markup
        )

    async def send_media_group(self, chat_id: int, media: List[Dict],
                              disable_notification: bool = False, protect_content: bool = False,
                              reply_to_message_id: Optional[int] = None,
                              allow_sending_without_reply: bool = False):
        """Send media group (album)"""
        return await self.api.send_media_group(
            chat_id, media, disable_notification, protect_content,
            reply_to_message_id, allow_sending_without_reply
        )

    async def send_location(self, chat_id: int, latitude: float, longitude: float,
                           horizontal_accuracy: Optional[float] = None,
                           live_period: Optional[int] = None, heading: Optional[int] = None,
                           proximity_alert_radius: Optional[int] = None,
                           disable_notification: bool = False, protect_content: bool = False,
                           reply_to_message_id: Optional[int] = None,
                           allow_sending_without_reply: bool = False,
                           reply_markup: Optional[Dict] = None):
        """Send location"""
        return await self.api.send_location(
            chat_id, latitude, longitude, horizontal_accuracy, live_period, heading,
            proximity_alert_radius, disable_notification, protect_content,
            reply_to_message_id, allow_sending_without_reply, reply_markup
        )

    async def send_venue(self, chat_id: int, latitude: float, longitude: float,
                        title: str, address: str, foursquare_id: Optional[str] = None,
                        foursquare_type: Optional[str] = None,
                        google_place_id: Optional[str] = None,
                        google_place_type: Optional[str] = None,
                        disable_notification: bool = False, protect_content: bool = False,
                        reply_to_message_id: Optional[int] = None,
                        allow_sending_without_reply: bool = False,
                        reply_markup: Optional[Dict] = None):
        """Send venue"""
        return await self.api.send_venue(
            chat_id, latitude, longitude, title, address, foursquare_id, foursquare_type,
            google_place_id, google_place_type, disable_notification, protect_content,
            reply_to_message_id, allow_sending_without_reply, reply_markup
        )

    async def send_contact(self, chat_id: int, phone_number: str, first_name: str,
                          last_name: Optional[str] = None, vcard: Optional[str] = None,
                          disable_notification: bool = False, protect_content: bool = False,
                          reply_to_message_id: Optional[int] = None,
                          allow_sending_without_reply: bool = False,
                          reply_markup: Optional[Dict] = None):
        """Send contact"""
        return await self.api.send_contact(
            chat_id, phone_number, first_name, last_name, vcard, disable_notification,
            protect_content, reply_to_message_id, allow_sending_without_reply, reply_markup
        )

    async def send_poll(self, chat_id: int, question: str, options: List[str],
                       is_anonymous: bool = True, type: str = "regular",
                       allows_multiple_answers: bool = False,
                       correct_option_id: Optional[int] = None,
                       explanation: Optional[str] = None, explanation_parse_mode: Optional[str] = None,
                       explanation_entities: Optional[List] = None,
                       open_period: Optional[int] = None, close_date: Optional[int] = None,
                       is_closed: bool = False, disable_notification: bool = False,
                       protect_content: bool = False, reply_to_message_id: Optional[int] = None,
                       allow_sending_without_reply: bool = False,
                       reply_markup: Optional[Dict] = None):
        """Send poll"""
        return await self.api.send_poll(
            chat_id, question, options, is_anonymous, type, allows_multiple_answers,
            correct_option_id, explanation, explanation_parse_mode or self.parse_mode,
            explanation_entities, open_period, close_date, is_closed, disable_notification,
            protect_content, reply_to_message_id, allow_sending_without_reply, reply_markup
        )

    async def send_dice(self, chat_id: int, emoji: str = "🎲",
                       disable_notification: bool = False, protect_content: bool = False,
                       reply_to_message_id: Optional[int] = None,
                       allow_sending_without_reply: bool = False,
                       reply_markup: Optional[Dict] = None):
        """Send dice"""
        return await self.api.send_dice(
            chat_id, emoji, disable_notification, protect_content,
            reply_to_message_id, allow_sending_without_reply, reply_markup
        )

    # ============= Chat Actions =============

    async def send_chat_action(self, chat_id: int, action: str):
        """Send chat action (typing, upload_photo, etc.)"""
        return await self.api.send_chat_action(chat_id, action)

    # ============= Message Management =============

    async def edit_message_text(self, text: str, chat_id: Optional[int] = None,
                               message_id: Optional[int] = None,
                               inline_message_id: Optional[str] = None,
                               parse_mode: Optional[str] = None, entities: Optional[List] = None,
                               disable_web_page_preview: bool = False,
                               reply_markup: Optional[Dict] = None):
        """Edit message text"""
        return await self.api.edit_message_text(
            text, chat_id, message_id, inline_message_id, parse_mode or self.parse_mode,
            entities, disable_web_page_preview, reply_markup
        )

    async def edit_message_caption(self, chat_id: Optional[int] = None,
                                   message_id: Optional[int] = None,
                                   inline_message_id: Optional[str] = None,
                                   caption: Optional[str] = None,
                                   parse_mode: Optional[str] = None,
                                   caption_entities: Optional[List] = None,
                                   reply_markup: Optional[Dict] = None):
        """Edit message caption"""
        return await self.api.edit_message_caption(
            chat_id, message_id, inline_message_id, caption, parse_mode or self.parse_mode,
            caption_entities, reply_markup
        )

    async def edit_message_media(self, media: Dict, chat_id: Optional[int] = None,
                                message_id: Optional[int] = None,
                                inline_message_id: Optional[str] = None,
                                reply_markup: Optional[Dict] = None):
        """Edit message media"""
        return await self.api.edit_message_media(
            media, chat_id, message_id, inline_message_id, reply_markup
        )

    async def edit_message_reply_markup(self, chat_id: Optional[int] = None,
                                       message_id: Optional[int] = None,
                                       inline_message_id: Optional[str] = None,
                                       reply_markup: Optional[Dict] = None):
        """Edit message reply markup"""
        return await self.api.edit_message_reply_markup(
            chat_id, message_id, inline_message_id, reply_markup
        )

    async def stop_poll(self, chat_id: int, message_id: int,
                       reply_markup: Optional[Dict] = None):
        """Stop poll"""
        return await self.api.stop_poll(chat_id, message_id, reply_markup)

    async def delete_message(self, chat_id: int, message_id: int):
        """Delete message"""
        return await self.api.delete_message(chat_id, message_id)

    # ============= Stickers =============

    async def send_sticker(self, chat_id: int, sticker,
                          disable_notification: bool = False, protect_content: bool = False,
                          reply_to_message_id: Optional[int] = None,
                          allow_sending_without_reply: bool = False,
                          reply_markup: Optional[Dict] = None):
        """Send sticker"""
        return await self.api.send_sticker(
            chat_id, sticker, disable_notification, protect_content,
            reply_to_message_id, allow_sending_without_reply, reply_markup
        )

    async def get_sticker_set(self, name: str):
        """Get sticker set"""
        return await self.api.get_sticker_set(name)

    async def get_custom_emoji_stickers(self, custom_emoji_ids: List[str]):
        """Get custom emoji stickers"""
        return await self.api.get_custom_emoji_stickers(custom_emoji_ids)

    async def upload_sticker_file(self, user_id: int, png_sticker):
        """Upload sticker file"""
        return await self.api.upload_sticker_file(user_id, png_sticker)

    async def create_new_sticker_set(self, user_id: int, name: str, title: str,
                                    emojis: str, png_sticker = None, tgs_sticker = None,
                                    webm_sticker = None, sticker_type: str = "regular",
                                    mask_position: Optional[Dict] = None):
        """Create new sticker set"""
        return await self.api.create_new_sticker_set(
            user_id, name, title, emojis, png_sticker, tgs_sticker, webm_sticker,
            sticker_type, mask_position
        )

    async def add_sticker_to_set(self, user_id: int, name: str, emojis: str,
                                png_sticker = None, tgs_sticker = None,
                                webm_sticker = None, mask_position: Optional[Dict] = None):
        """Add sticker to set"""
        return await self.api.add_sticker_to_set(
            user_id, name, emojis, png_sticker, tgs_sticker, webm_sticker, mask_position
        )

    async def set_sticker_position_in_set(self, sticker: str, position: int):
        """Set sticker position in set"""
        return await self.api.set_sticker_position_in_set(sticker, position)

    async def delete_sticker_from_set(self, sticker: str):
        """Delete sticker from set"""
        return await self.api.delete_sticker_from_set(sticker)

    async def set_sticker_set_thumb(self, name: str, user_id: int, thumb = None):
        """Set sticker set thumbnail"""
        return await self.api.set_sticker_set_thumb(name, user_id, thumb)

    # ============= Inline Mode =============

    async def answer_inline_query(self, inline_query_id: str, results: List[Dict],
                                  cache_time: int = 300, is_personal: bool = False,
                                  next_offset: Optional[str] = None,
                                  switch_pm_text: Optional[str] = None,
                                  switch_pm_parameter: Optional[str] = None):
        """Answer inline query"""
        return await self.api.answer_inline_query(
            inline_query_id, results, cache_time, is_personal, next_offset,
            switch_pm_text, switch_pm_parameter
        )

    async def answer_web_app_query(self, web_app_query_id: str, result: Dict):
        """Answer web app query"""
        return await self.api.answer_web_app_query(web_app_query_id, result)

    # ============= Callback Queries =============

    async def answer_callback_query(self, callback_query_id: str, text: Optional[str] = None,
                                    show_alert: bool = False, url: Optional[str] = None,
                                    cache_time: int = 0):
        """Answer callback query"""
        return await self.api.answer_callback_query(
            callback_query_id, text, show_alert, url, cache_time
        )

    # ============= User/Chat Information =============

    async def get_user_profile_photos(self, user_id: int, offset: int = 0, limit: int = 100):
        """Get user profile photos"""
        return await self.api.get_user_profile_photos(user_id, offset, limit)

    async def get_file(self, file_id: str):
        """Get file info"""
        return await self.api.get_file(file_id)

    async def ban_chat_member(self, chat_id: int, user_id: int,
                             until_date: Optional[int] = None,
                             revoke_messages: bool = False):
        """Ban chat member"""
        return await self.api.ban_chat_member(chat_id, user_id, until_date, revoke_messages)

    async def unban_chat_member(self, chat_id: int, user_id: int, only_if_banned: bool = False):
        """Unban chat member"""
        return await self.api.unban_chat_member(chat_id, user_id, only_if_banned)

    async def restrict_chat_member(self, chat_id: int, user_id: int, permissions: Dict,
                                   until_date: Optional[int] = None):
        """Restrict chat member"""
        return await self.api.restrict_chat_member(chat_id, user_id, permissions, until_date)

    async def promote_chat_member(self, chat_id: int, user_id: int,
                                 is_anonymous: bool = False,
                                 can_manage_chat: bool = False,
                                 can_post_messages: bool = False,
                                 can_edit_messages: bool = False,
                                 can_delete_messages: bool = False,
                                 can_manage_video_chats: bool = False,
                                 can_restrict_members: bool = False,
                                 can_promote_members: bool = False,
                                 can_change_info: bool = False,
                                 can_invite_users: bool = False,
                                 can_pin_messages: bool = False):
        """Promote chat member"""
        return await self.api.promote_chat_member(
            chat_id, user_id, is_anonymous, can_manage_chat, can_post_messages,
            can_edit_messages, can_delete_messages, can_manage_video_chats,
            can_restrict_members, can_promote_members, can_change_info,
            can_invite_users, can_pin_messages
        )

    async def set_chat_administrator_custom_title(self, chat_id: int, user_id: int,
                                                  custom_title: str):
        """Set chat administrator custom title"""
        return await self.api.set_chat_administrator_custom_title(
            chat_id, user_id, custom_title
        )

    async def ban_chat_sender_chat(self, chat_id: int, sender_chat_id: int):
        """Ban chat sender chat"""
        return await self.api.ban_chat_sender_chat(chat_id, sender_chat_id)

    async def unban_chat_sender_chat(self, chat_id: int, sender_chat_id: int):
        """Unban chat sender chat"""
        return await self.api.unban_chat_sender_chat(chat_id, sender_chat_id)

    async def set_chat_permissions(self, chat_id: int, permissions: Dict):
        """Set chat permissions"""
        return await self.api.set_chat_permissions(chat_id, permissions)

    async def export_chat_invite_link(self, chat_id: int):
        """Export chat invite link"""
        return await self.api.export_chat_invite_link(chat_id)

    async def create_chat_invite_link(self, chat_id: int, name: Optional[str] = None,
                                     expire_date: Optional[int] = None,
                                     member_limit: Optional[int] = None,
                                     creates_join_request: bool = False):
        """Create chat invite link"""
        return await self.api.create_chat_invite_link(
            chat_id, name, expire_date, member_limit, creates_join_request
        )

    async def edit_chat_invite_link(self, chat_id: int, invite_link: str,
                                   name: Optional[str] = None,
                                   expire_date: Optional[int] = None,
                                   member_limit: Optional[int] = None,
                                   creates_join_request: bool = False):
        """Edit chat invite link"""
        return await self.api.edit_chat_invite_link(
            chat_id, invite_link, name, expire_date, member_limit, creates_join_request
        )

    async def revoke_chat_invite_link(self, chat_id: int, invite_link: str):
        """Revoke chat invite link"""
        return await self.api.revoke_chat_invite_link(chat_id, invite_link)

    async def approve_chat_join_request(self, chat_id: int, user_id: int):
        """Approve chat join request"""
        return await self.api.approve_chat_join_request(chat_id, user_id)

    async def decline_chat_join_request(self, chat_id: int, user_id: int):
        """Decline chat join request"""
        return await self.api.decline_chat_join_request(chat_id, user_id)

    async def set_chat_photo(self, chat_id: int, photo):
        """Set chat photo"""
        return await self.api.set_chat_photo(chat_id, photo)

    async def delete_chat_photo(self, chat_id: int):
        """Delete chat photo"""
        return await self.api.delete_chat_photo(chat_id)

    async def set_chat_title(self, chat_id: int, title: str):
        """Set chat title"""
        return await self.api.set_chat_title(chat_id, title)

    async def set_chat_description(self, chat_id: int, description: Optional[str] = None):
        """Set chat description"""
        return await self.api.set_chat_description(chat_id, description)

    async def pin_chat_message(self, chat_id: int, message_id: int,
                               disable_notification: bool = False):
        """Pin chat message"""
        return await self.api.pin_chat_message(chat_id, message_id, disable_notification)

    async def unpin_chat_message(self, chat_id: int, message_id: Optional[int] = None):
        """Unpin chat message"""
        return await self.api.unpin_chat_message(chat_id, message_id)

    async def unpin_all_chat_messages(self, chat_id: int):
        """Unpin all chat messages"""
        return await self.api.unpin_all_chat_messages(chat_id)

    async def leave_chat(self, chat_id: int):
        """Leave chat"""
        return await self.api.leave_chat(chat_id)

    async def get_chat(self, chat_id: int):
        """Get chat information"""
        return await self.api.get_chat(chat_id)

    async def get_chat_administrators(self, chat_id: int):
        """Get chat administrators"""
        return await self.api.get_chat_administrators(chat_id)

    async def get_chat_member_count(self, chat_id: int):
        """Get chat member count"""
        return await self.api.get_chat_member_count(chat_id)

    async def get_chat_member(self, chat_id: int, user_id: int):
        """Get chat member"""
        return await self.api.get_chat_member(chat_id, user_id)

    async def set_chat_sticker_set(self, chat_id: int, sticker_set_name: str):
        """Set chat sticker set"""
        return await self.api.set_chat_sticker_set(chat_id, sticker_set_name)

    async def delete_chat_sticker_set(self, chat_id: int):
        """Delete chat sticker set"""
        return await self.api.delete_chat_sticker_set(chat_id)

    # ============= Forum Topics (Telegram Topics) =============

    async def get_forum_topic_icon_stickers(self):
        """Get forum topic icon stickers"""
        return await self.api.get_forum_topic_icon_stickers()

    async def create_forum_topic(self, chat_id: int, name: str,
                                icon_color: Optional[int] = None,
                                icon_custom_emoji_id: Optional[str] = None):
        """Create forum topic"""
        return await self.api.create_forum_topic(
            chat_id, name, icon_color, icon_custom_emoji_id
        )

    async def edit_forum_topic(self, chat_id: int, message_thread_id: int,
                              name: Optional[str] = None,
                              icon_custom_emoji_id: Optional[str] = None):
        """Edit forum topic"""
        return await self.api.edit_forum_topic(
            chat_id, message_thread_id, name, icon_custom_emoji_id
        )

    async def close_forum_topic(self, chat_id: int, message_thread_id: int):
        """Close forum topic"""
        return await self.api.close_forum_topic(chat_id, message_thread_id)

    async def reopen_forum_topic(self, chat_id: int, message_thread_id: int):
        """Reopen forum topic"""
        return await self.api.reopen_forum_topic(chat_id, message_thread_id)

    async def delete_forum_topic(self, chat_id: int, message_thread_id: int):
        """Delete forum topic"""
        return await self.api.delete_forum_topic(chat_id, message_thread_id)

    async def unpin_all_forum_topic_messages(self, chat_id: int, message_thread_id: int):
        """Unpin all forum topic messages"""
        return await self.api.unpin_all_forum_topic_messages(chat_id, message_thread_id)

    async def edit_general_forum_topic(self, chat_id: int, name: str):
        """Edit general forum topic"""
        return await self.api.edit_general_forum_topic(chat_id, name)

    async def close_general_forum_topic(self, chat_id: int):
        """Close general forum topic"""
        return await self.api.close_general_forum_topic(chat_id)

    async def reopen_general_forum_topic(self, chat_id: int):
        """Reopen general forum topic"""
        return await self.api.reopen_general_forum_topic(chat_id)

    async def hide_general_forum_topic(self, chat_id: int):
        """Hide general forum topic"""
        return await self.api.hide_general_forum_topic(chat_id)

    async def unhide_general_forum_topic(self, chat_id: int):
        """Unhide general forum topic"""
        return await self.api.unhide_general_forum_topic(chat_id)

    # ============= Payments =============

    async def send_invoice(self, chat_id: int, title: str, description: str,
                          payload: str, provider_token: str, currency: str,
                          prices: List[Dict], max_tip_amount: Optional[int] = None,
                          suggested_tip_amounts: Optional[List[int]] = None,
                          start_parameter: Optional[str] = None,
                          provider_data: Optional[str] = None,
                          photo_url: Optional[str] = None, photo_size: Optional[int] = None,
                          photo_width: Optional[int] = None, photo_height: Optional[int] = None,
                          need_name: bool = False, need_phone_number: bool = False,
                          need_email: bool = False, need_shipping_address: bool = False,
                          send_phone_number_to_provider: bool = False,
                          send_email_to_provider: bool = False, is_flexible: bool = False,
                          disable_notification: bool = False, protect_content: bool = False,
                          reply_to_message_id: Optional[int] = None,
                          allow_sending_without_reply: bool = False,
                          reply_markup: Optional[Dict] = None):
        """Send invoice"""
        return await self.api.send_invoice(
            chat_id, title, description, payload, provider_token, currency, prices,
            max_tip_amount, suggested_tip_amounts, start_parameter, provider_data,
            photo_url, photo_size, photo_width, photo_height, need_name, need_phone_number,
            need_email, need_shipping_address, send_phone_number_to_provider,
            send_email_to_provider, is_flexible, disable_notification, protect_content,
            reply_to_message_id, allow_sending_without_reply, reply_markup
        )

    async def create_invoice_link(self, title: str, description: str, payload: str,
                                 provider_token: str, currency: str, prices: List[Dict],
                                 max_tip_amount: Optional[int] = None,
                                 suggested_tip_amounts: Optional[List[int]] = None,
                                 provider_data: Optional[str] = None,
                                 photo_url: Optional[str] = None, photo_size: Optional[int] = None,
                                 photo_width: Optional[int] = None, photo_height: Optional[int] = None,
                                 need_name: bool = False, need_phone_number: bool = False,
                                 need_email: bool = False, need_shipping_address: bool = False,
                                 send_phone_number_to_provider: bool = False,
                                 send_email_to_provider: bool = False, is_flexible: bool = False):
        """Create invoice link"""
        return await self.api.create_invoice_link(
            title, description, payload, provider_token, currency, prices,
            max_tip_amount, suggested_tip_amounts, provider_data, photo_url, photo_size,
            photo_width, photo_height, need_name, need_phone_number, need_email,
            need_shipping_address, send_phone_number_to_provider, send_email_to_provider,
            is_flexible
        )

    async def answer_shipping_query(self, shipping_query_id: str, ok: bool,
                                    shipping_options: Optional[List[Dict]] = None,
                                    error_message: Optional[str] = None):
        """Answer shipping query"""
        return await self.api.answer_shipping_query(
            shipping_query_id, ok, shipping_options, error_message
        )

    async def answer_pre_checkout_query(self, pre_checkout_query_id: str, ok: bool,
                                       error_message: Optional[str] = None):
        """Answer pre-checkout query"""
        return await self.api.answer_pre_checkout_query(
            pre_checkout_query_id, ok, error_message
        )

    # ============= Games =============

    async def send_game(self, chat_id: int, game_short_name: str,
                       disable_notification: bool = False, protect_content: bool = False,
                       reply_to_message_id: Optional[int] = None,
                       allow_sending_without_reply: bool = False,
                       reply_markup: Optional[Dict] = None):
        """Send game"""
        return await self.api.send_game(
            chat_id, game_short_name, disable_notification, protect_content,
            reply_to_message_id, allow_sending_without_reply, reply_markup
        )

    async def set_game_score(self, user_id: int, score: int, force: bool = False,
                            disable_edit_message: bool = False,
                            chat_id: Optional[int] = None, message_id: Optional[int] = None,
                            inline_message_id: Optional[str] = None):
        """Set game score"""
        return await self.api.set_game_score(
            user_id, score, force, disable_edit_message, chat_id, message_id, inline_message_id
        )

    async def get_game_high_scores(self, user_id: int, chat_id: Optional[int] = None,
                                  message_id: Optional[int] = None,
                                  inline_message_id: Optional[str] = None):
        """Get game high scores"""
        return await self.api.get_game_high_scores(user_id, chat_id, message_id, inline_message_id)

    # ============= Webhook =============

    async def set_webhook(self, url: str, certificate = None,
                         ip_address: Optional[str] = None,
                         max_connections: int = 40,
                         allowed_updates: Optional[List[str]] = None,
                         drop_pending_updates: bool = False,
                         secret_token: Optional[str] = None):
        """Set webhook"""
        return await self.api.set_webhook(
            url, certificate, ip_address, max_connections, allowed_updates,
            drop_pending_updates, secret_token
        )

    async def delete_webhook(self, drop_pending_updates: bool = False):
        """Delete webhook"""
        return await self.api.delete_webhook(drop_pending_updates)

    async def get_webhook_info(self):
        """Get webhook info"""
        return await self.api.get_webhook_info()

    # ============= My Commands =============

    async def set_my_commands(self, commands: List[Dict], scope: Optional[Dict] = None,
                             language_code: Optional[str] = None):
        """Set bot commands"""
        return await self.api.set_my_commands(commands, scope, language_code)

    async def delete_my_commands(self, scope: Optional[Dict] = None,
                                language_code: Optional[str] = None):
        """Delete bot commands"""
        return await self.api.delete_my_commands(scope, language_code)

    async def get_my_commands(self, scope: Optional[Dict] = None,
                             language_code: Optional[str] = None):
        """Get bot commands"""
        return await self.api.get_my_commands(scope, language_code)

    async def set_my_name(self, name: Optional[str] = None, language_code: Optional[str] = None):
        """Set bot name"""
        return await self.api.set_my_name(name, language_code)

    async def get_my_name(self, language_code: Optional[str] = None):
        """Get bot name"""
        return await self.api.get_my_name(language_code)

    async def set_my_description(self, description: Optional[str] = None,
                                language_code: Optional[str] = None):
        """Set bot description"""
        return await self.api.set_my_description(description, language_code)

    async def get_my_description(self, language_code: Optional[str] = None):
        """Get bot description"""
        return await self.api.get_my_description(language_code)

    async def set_my_short_description(self, short_description: Optional[str] = None,
                                      language_code: Optional[str] = None):
        """Set bot short description"""
        return await self.api.set_my_short_description(short_description, language_code)

    async def get_my_short_description(self, language_code: Optional[str] = None):
        """Get bot short description"""
        return await self.api.get_my_short_description(language_code)

    async def set_chat_menu_button(self, chat_id: Optional[int] = None,
                                  menu_button: Optional[Dict] = None):
        """Set chat menu button"""
        return await self.api.set_chat_menu_button(chat_id, menu_button)

    async def get_chat_menu_button(self, chat_id: Optional[int] = None):
        """Get chat menu button"""
        return await self.api.get_chat_menu_button(chat_id)

    async def set_my_default_administrator_rights(self, rights: Optional[Dict] = None,
                                                  for_channels: bool = False):
        """Set default administrator rights"""
        return await self.api.set_my_default_administrator_rights(rights, for_channels)

    async def get_my_default_administrator_rights(self, for_channels: bool = False):
        """Get default administrator rights"""
        return await self.api.get_my_default_administrator_rights(for_channels)

    # ============= Utility Property =============
    
    @property
    def telegram_api(self):
        """Direct access to TelegramAPI for advanced usage"""
        return self.api

