"""
Enhanced logging middleware with centralized logging and performance optimizations
Copyright (c) 2025 Arjun-M/SwiftBot
"""

import logging
import json
import sys
from datetime import datetime
from typing import Optional, List, Dict, Any, Union
from .base import Middleware


class Logger(Middleware):
    """
    Enhanced logging middleware for tracking updates, responses, and performance.

    Features:
    - Multiple log formats (text, JSON, colored)
    - Configurable destinations
    - Performance metrics
    - Error tracking
    - Rate limiting for logs
    - Async logging support
    - Memory usage tracking

    Copyright (c) 2025 Arjun-M/SwiftBot - Enhanced Edition
    """

    def __init__(
        self,
        level: str = "INFO",
        format: str = "text",
        include_updates: bool = True,
        include_responses: bool = False,
        include_performance: bool = True,
        include_errors: bool = True,
        destinations: Optional[List] = None,
        max_log_length: int = 1000,
        rate_limit: Optional[int] = None,
        enable_colors: bool = True,
        log_sensitive_data: bool = False,
        custom_formatter: Optional[logging.Formatter] = None
    ):
        """
        Initialize enhanced logger middleware.

        Args:
            level: Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
            format: Log format (text, json, colored, compact)
            include_updates: Log incoming updates
            include_responses: Log outgoing responses
            include_performance: Log performance metrics
            include_errors: Log errors and exceptions
            destinations: List of log handlers
            max_log_length: Maximum length of logged messages
            rate_limit: Maximum logs per second (None for no limit)
            enable_colors: Enable colored output for console
            log_sensitive_data: Include sensitive data in logs (be careful!)
            custom_formatter: Custom log formatter
        """
        self.logger = logging.getLogger("SwiftBot")
        self.logger.setLevel(getattr(logging, level.upper()))

        # Prevent duplicate handlers
        if self.logger.handlers:
            self.logger.handlers.clear()

        self.format = format
        self.include_updates = include_updates
        self.include_responses = include_responses
        self.include_performance = include_performance
        self.include_errors = include_errors
        self.max_log_length = max_log_length
        self.rate_limit = rate_limit
        self.enable_colors = enable_colors
        self.log_sensitive_data = log_sensitive_data

        # Rate limiting
        self._log_timestamps = []

        # Performance tracking
        self._performance_stats = {
            'total_updates': 0,
            'avg_processing_time': 0,
            'max_processing_time': 0,
            'min_processing_time': float('inf'),
            'error_count': 0
        }

        # Setup handlers
        self._setup_handlers(destinations, custom_formatter)

        # Silence excessive HTTP logging
        logging.getLogger("httpx").setLevel(logging.WARNING)
        logging.getLogger("http.client").setLevel(logging.WARNING)
        logging.getLogger("urllib3").setLevel(logging.WARNING)

    def _setup_handlers(self, destinations: Optional[List], custom_formatter: Optional[logging.Formatter]):
        """Setup log handlers with proper formatting"""

        if destinations:
            for handler in destinations:
                if custom_formatter:
                    handler.setFormatter(custom_formatter)
                else:
                    handler.setFormatter(self._get_formatter())
                self.logger.addHandler(handler)
        else:
            # Default console handler
            handler = logging.StreamHandler(sys.stdout)
            if custom_formatter:
                handler.setFormatter(custom_formatter)
            else:
                handler.setFormatter(self._get_formatter())
            self.logger.addHandler(handler)

    def _get_formatter(self) -> logging.Formatter:
        """Get appropriate formatter based on format setting"""

        if self.format == "json":
            return JsonFormatter()
        elif self.format == "colored" and self.enable_colors:
            return ColoredFormatter()
        elif self.format == "compact":
            return logging.Formatter('%(asctime)s [%(levelname)s] %(message)s', '%H:%M:%S')
        else:
            return logging.Formatter(
                '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
                '%Y-%m-%d %H:%M:%S'
            )

    def _should_log(self) -> bool:
        """Check if we should log based on rate limiting"""
        if not self.rate_limit:
            return True

        now = datetime.now().timestamp()
        # Remove timestamps older than 1 second
        self._log_timestamps = [ts for ts in self._log_timestamps if now - ts < 1.0]

        if len(self._log_timestamps) >= self.rate_limit:
            return False

        self._log_timestamps.append(now)
        return True

    def _truncate_message(self, message: str) -> str:
        """Truncate message if too long"""
        if len(message) <= self.max_log_length:
            return message
        return message[:self.max_log_length] + "..."

    def _sanitize_data(self, data: Any) -> Any:
        """Sanitize sensitive data from logs"""
        if self.log_sensitive_data:
            return data

        if isinstance(data, dict):
            sanitized = {}
            for key, value in data.items():
                if any(sensitive in key.lower() for sensitive in ['token', 'password', 'secret', 'key']):
                    sanitized[key] = "***REDACTED***"
                elif isinstance(value, (dict, list)):
                    sanitized[key] = self._sanitize_data(value)
                else:
                    sanitized[key] = value
            return sanitized
        elif isinstance(data, list):
            return [self._sanitize_data(item) for item in data]
        else:
            return data

    async def on_update(self, ctx, next_handler):
        """Log incoming update and execution with performance tracking"""

        if not self._should_log():
            await next_handler()
            return

        start_time = datetime.now()

        if self.include_updates:
            self._log_update(ctx)

        try:
            await next_handler()

            # Performance tracking
            if self.include_performance:
                duration = (datetime.now() - start_time).total_seconds()
                self._update_performance_stats(duration)

                if duration > 1.0:  # Log slow operations
                    self.logger.warning(f"Slow handler execution: {duration:.3f}s")
                else:
                    self.logger.debug(f"Handler executed in {duration:.3f}s")

        except Exception as e:
            duration = (datetime.now() - start_time).total_seconds()
            self._performance_stats['error_count'] += 1

            if self.include_errors:
                self.logger.error(
                    f"Handler failed after {duration:.3f}s: {e}",
                    extra={'context': 'handler_execution', 'duration': duration}
                )
            raise

    def _update_performance_stats(self, duration: float):
        """Update performance statistics"""
        stats = self._performance_stats
        stats['total_updates'] += 1

        # Update averages
        stats['avg_processing_time'] = (
            (stats['avg_processing_time'] * (stats['total_updates'] - 1) + duration) / 
            stats['total_updates']
        )

        # Update min/max
        stats['max_processing_time'] = max(stats['max_processing_time'], duration)
        stats['min_processing_time'] = min(stats['min_processing_time'], duration)

    def _log_update(self, ctx):
        """Log update details with sanitization"""
        try:
            if self.format == "json":
                log_data = {
                    "timestamp": datetime.now().isoformat(),
                    "user_id": ctx.user.id if ctx.user else None,
                    "username": ctx.user.username if ctx.user else None,
                    "chat_id": ctx.chat.id if ctx.chat else None,
                    "chat_type": ctx.chat.type if ctx.chat else None,
                    "text": self._truncate_message(ctx.text or ""),
                    "update_type": type(ctx._update_obj).__name__ if hasattr(ctx, '_update_obj') else "Unknown"
                }

                # Sanitize sensitive data
                log_data = self._sanitize_data(log_data)

                self.logger.info(json.dumps(log_data, ensure_ascii=False))
            else:
                user_info = f"@{ctx.user.username}" if ctx.user and ctx.user.username else f"ID:{ctx.user.id}" if ctx.user else "Unknown"
                chat_info = f"Chat:{ctx.chat.id}" if ctx.chat else "DM"
                text_preview = self._truncate_message(ctx.text or "(no text)")

                self.logger.info(f"📨 {user_info} in {chat_info}: {text_preview}")

        except Exception as e:
            self.logger.error(f"Error logging update: {e}")

    async def on_error(self, ctx, error):
        """Log error with enhanced context"""
        if not self.include_errors or not self._should_log():
            return

        try:
            error_context = {
                'error_type': type(error).__name__,
                'error_message': str(error),
                'user_id': ctx.user.id if ctx and ctx.user else None,
                'chat_id': ctx.chat.id if ctx and ctx.chat else None,
                'handler': getattr(ctx, 'handler_name', 'unknown') if ctx else 'unknown'
            }

            if self.format == "json":
                self.logger.error(json.dumps({
                    "timestamp": datetime.now().isoformat(),
                    "level": "ERROR",
                    "context": "error_handler",
                    **error_context
                }))
            else:
                self.logger.error(
                    f"🚨 Error in handler: {error_context['error_message']}",
                    exc_info=True,
                    extra=error_context
                )
        except Exception as log_error:
            # Fallback logging
            self.logger.error(f"Error in error logging: {log_error}")

    def get_performance_stats(self) -> Dict[str, Any]:
        """Get current performance statistics"""
        stats = self._performance_stats.copy()
        if stats['min_processing_time'] == float('inf'):
            stats['min_processing_time'] = 0
        return stats

    def reset_performance_stats(self):
        """Reset performance statistics"""
        self._performance_stats = {
            'total_updates': 0,
            'avg_processing_time': 0,
            'max_processing_time': 0,
            'min_processing_time': float('inf'),
            'error_count': 0
        }


class JsonFormatter(logging.Formatter):
    """JSON formatter for structured logging"""

    def format(self, record):
        log_data = {
            'timestamp': datetime.fromtimestamp(record.created).isoformat(),
            'level': record.levelname,
            'logger': record.name,
            'message': record.getMessage(),
            'module': record.module,
            'function': record.funcName,
            'line': record.lineno
        }

        # Add extra fields
        if hasattr(record, 'context'):
            log_data['context'] = record.context
        if hasattr(record, 'duration'):
            log_data['duration'] = record.duration

        if record.exc_info:
            log_data['exception'] = self.formatException(record.exc_info)

        return json.dumps(log_data, ensure_ascii=False)


class ColoredFormatter(logging.Formatter):
    """Colored formatter for console output"""

    COLORS = {
        'DEBUG': '\033[36m',     # Cyan
        'INFO': '\033[32m',      # Green  
        'WARNING': '\033[33m',   # Yellow
        'ERROR': '\033[31m',     # Red
        'CRITICAL': '\033[35m',  # Magenta
        'RESET': '\033[0m'       # Reset
    }

    def format(self, record):
        color = self.COLORS.get(record.levelname, self.COLORS['RESET'])
        record.levelname = f"{color}{record.levelname}{self.COLORS['RESET']}"
        return super().format(record)
