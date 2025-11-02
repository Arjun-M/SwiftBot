"""
Centralized exception handling for SwiftBot
Copyright (c) 2025 Arjun-M/SwiftBot
"""

import asyncio
import logging
import traceback
from datetime import datetime
from typing import Dict, List, Callable, Optional, Any
from .base import SwiftBotException


class CentralizedExceptionHandler:
    """
    Centralized exception handling system for SwiftBot.

    Features:
    - Exception categorization and routing
    - Custom error handlers
    - Error statistics and monitoring
    - Automatic recovery strategies
    - Error reporting and logging
    """

    def __init__(self, 
                 enable_auto_recovery: bool = True,
                 max_retries: int = 3,
                 enable_detailed_logging: bool = True):
        self.enable_auto_recovery = enable_auto_recovery
        self.max_retries = max_retries
        self.enable_detailed_logging = enable_detailed_logging

        # Error handlers by exception type
        self.error_handlers: Dict[type, List[Callable]] = {}

        # Statistics
        self.error_stats = {
            'total_errors': 0,
            'errors_by_type': {},
            'errors_by_context': {},
            'recovered_errors': 0,
            'unrecovered_errors': 0,
            'last_error_time': None
        }

        # Logger for exception handling
        self.logger = logging.getLogger('SwiftBot.ExceptionHandler')

        # Default error handlers
        self._setup_default_handlers()

    def _setup_default_handlers(self):
        """Setup default error handlers for common exceptions"""

        async def handle_network_error(exception, context):
            """Handle network related errors with retry logic"""
            if self.enable_auto_recovery:
                retry_count = context.get('retry_count', 0)
                if retry_count < self.max_retries:
                    await asyncio.sleep(2 ** retry_count)  # Exponential backoff
                    context['retry_count'] = retry_count + 1
                    self.error_stats['recovered_errors'] += 1
                    return True  # Indicate recovery attempted
            return False

        async def handle_api_error(exception, context):
            """Handle API related errors"""
            # Log API errors for debugging
            if hasattr(exception, 'response_code'):
                self.logger.error(f"API Error {exception.response_code}: {exception}")
            return False

        async def handle_validation_error(exception, context):
            """Handle validation errors"""
            # Validation errors are usually not recoverable
            self.logger.warning(f"Validation error in {context.get('function', 'unknown')}: {exception}")
            return False

        # Register default handlers
        from .api import NetworkError, APIError
        from .base import ValidationError

        self.register_handler(NetworkError, handle_network_error)
        self.register_handler(APIError, handle_api_error) 
        self.register_handler(ValidationError, handle_validation_error)

    def register_handler(self, exception_type: type, handler: Callable):
        """
        Register a custom error handler for specific exception types.

        Args:
            exception_type: Exception class to handle
            handler: Async function to handle the exception
        """
        if exception_type not in self.error_handlers:
            self.error_handlers[exception_type] = []
        self.error_handlers[exception_type].append(handler)

    async def handle_exception_async(self, exception: Exception, context: str = "unknown", **kwargs):
        """
        Handle exception asynchronously with full error processing.

        Args:
            exception: The exception to handle
            context: Context where the exception occurred
            **kwargs: Additional context information
        """
        # Update statistics
        self.error_stats['total_errors'] += 1
        self.error_stats['last_error_time'] = datetime.now()

        exc_type = type(exception).__name__
        self.error_stats['errors_by_type'][exc_type] = self.error_stats['errors_by_type'].get(exc_type, 0) + 1
        self.error_stats['errors_by_context'][context] = self.error_stats['errors_by_context'].get(context, 0) + 1

        # Log the exception
        if self.enable_detailed_logging:
            self.logger.error(
                f"Exception in {context}: {exception}",
                exc_info=True,
                extra={'context': context, 'kwargs': kwargs}
            )

        # Try to handle with registered handlers
        recovery_attempted = False
        for exception_type, handlers in self.error_handlers.items():
            if isinstance(exception, exception_type):
                for handler in handlers:
                    try:
                        result = await handler(exception, {'context': context, **kwargs})
                        if result:
                            recovery_attempted = True
                            break
                    except Exception as handler_error:
                        self.logger.error(f"Error in exception handler: {handler_error}")

        if not recovery_attempted:
            self.error_stats['unrecovered_errors'] += 1

        return recovery_attempted

    def handle_exception(self, exception: Exception, context: str = "unknown", **kwargs):
        """
        Synchronous wrapper for exception handling.

        Args:
            exception: The exception to handle
            context: Context where the exception occurred
            **kwargs: Additional context information
        """
        # For synchronous contexts, we just log and update stats
        self.error_stats['total_errors'] += 1
        self.error_stats['last_error_time'] = datetime.now()

        exc_type = type(exception).__name__
        self.error_stats['errors_by_type'][exc_type] = self.error_stats['errors_by_type'].get(exc_type, 0) + 1
        self.error_stats['errors_by_context'][context] = self.error_stats['errors_by_context'].get(context, 0) + 1

        if self.enable_detailed_logging:
            self.logger.error(
                f"Exception in {context}: {exception}",
                exc_info=True,
                extra={'context': context, 'kwargs': kwargs}
            )

    def get_error_statistics(self) -> Dict[str, Any]:
        """Get current error statistics"""
        return {
            **self.error_stats,
            'recovery_rate': (
                self.error_stats['recovered_errors'] / max(self.error_stats['total_errors'], 1) * 100
            ),
            'handlers_registered': len(self.error_handlers)
        }

    def reset_statistics(self):
        """Reset error statistics"""
        self.error_stats = {
            'total_errors': 0,
            'errors_by_type': {},
            'errors_by_context': {},
            'recovered_errors': 0,
            'unrecovered_errors': 0,
            'last_error_time': None
        }
