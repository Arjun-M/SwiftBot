"""
Logging middleware
Copyright (c) 2025 Arjun-M/SwiftBot
"""

import logging
import json
from datetime import datetime
from .base import Middleware


class Logger(Middleware):
    """
    Logging middleware for tracking updates and responses.

    Supports multiple formats (text, JSON, colored) and destinations.

    Copyright (c) 2025 Arjun-M/SwiftBot
    """

    def __init__(
        self,
        level: str = "INFO",
        format: str = "text",
        include_updates: bool = True,
        include_responses: bool = False,
        destinations: list = None
    ):
        """
        Initialize logger middleware.

        Args:
            level: Logging level (DEBUG, INFO, WARNING, ERROR)
            format: Log format (text, json, colored)
            include_updates: Log incoming updates
            include_responses: Log outgoing responses
            destinations: List of log handlers
        """
        self.logger = logging.getLogger("SwiftBot")
        self.logger.setLevel(getattr(logging, level.upper()))

        self.format = format
        self.include_updates = include_updates
        self.include_responses = include_responses

        # Setup handlers
        if destinations:
            for handler in destinations:
                self.logger.addHandler(handler)
        elif not self.logger.handlers:
            handler = logging.StreamHandler()
            handler.setFormatter(logging.Formatter(
                '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
            ))
            self.logger.addHandler(handler)

    async def on_update(self, ctx, next_handler):
        """Log incoming update and execution"""
        if self.include_updates:
            self._log_update(ctx)

        start_time = datetime.now()

        try:
            await next_handler()
            duration = (datetime.now() - start_time).total_seconds()
            self.logger.info(f"Handler executed in {duration:.3f}s")
        except Exception as e:
            duration = (datetime.now() - start_time).total_seconds()
            self.logger.error(f"Handler failed after {duration:.3f}s: {e}")
            raise

    def _log_update(self, ctx):
        """Log update details"""
        if self.format == "json":
            log_data = {
                "timestamp": datetime.now().isoformat(),
                "user_id": ctx.user.id if ctx.user else None,
                "chat_id": ctx.chat.id if ctx.chat else None,
                "text": ctx.text,
                "update_type": type(ctx._update).__name__
            }
            self.logger.info(json.dumps(log_data))
        else:
            user_id = ctx.user.id if ctx.user else "Unknown"
            chat_id = ctx.chat.id if ctx.chat else "Unknown"
            text = ctx.text or "(no text)"
            self.logger.info(f"Update from user {user_id} in chat {chat_id}: {text}")

    async def on_error(self, ctx, error):
        """Log error"""
        self.logger.error(f"Error in handler: {error}", exc_info=True)
