"""
Centralized exception handling for SwiftBot
Copyright (c) 2025 Arjun-M/SwiftBot
"""

import asyncio
import logging
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
    """

    def __init__(self, 
                 enable_auto_recovery: bool = True,
                 max_retries: int = 3):
        self.enable_auto_recovery = enable_auto_recovery
        self.max_retries = max_retries

        # Error handlers by exception type
        self.error_handlers: Dict[type, List[Callable]] = {}

        # Statistics
        self.error_stats = {
            'total_errors': 0,
            'errors_by_type': {},
            'errors_by_context': {},
            'recovered_errors': 0,
            'last_error_time': None
        }

        # Logger
        self.logger = logging.getLogger('SwiftBot.ExceptionHandler')

    def register_handler(self, exception_type: type, handler: Callable):
        """Register a custom error handler for specific exception types."""
        if exception_type not in self.error_handlers:
            self.error_handlers[exception_type] = []
        self.error_handlers[exception_type].append(handler)

    async def handle_exception_async(self, exception: Exception, context: str = "unknown", **kwargs):
        """Handle exception asynchronously."""
        # Update statistics
        self.error_stats['total_errors'] += 1
        self.error_stats['last_error_time'] = datetime.now()

        exc_type = type(exception).__name__
        self.error_stats['errors_by_type'][exc_type] = self.error_stats['errors_by_type'].get(exc_type, 0) + 1
        self.error_stats['errors_by_context'][context] = self.error_stats['errors_by_context'].get(context, 0) + 1

        # Log the exception
        self.logger.error(f"Exception in {context}: {exception}", exc_info=True)

        # Try to handle with registered handlers
        recovery_attempted = False
        for exception_type, handlers in self.error_handlers.items():
            if isinstance(exception, exception_type):
                for handler in handlers:
                    try:
                        result = await handler(exception, {'context': context, **kwargs})
                        if result:
                            recovery_attempted = True
                            self.error_stats['recovered_errors'] += 1
                            break
                    except Exception as handler_error:
                        self.logger.error(f"Error in exception handler: {handler_error}")

        return recovery_attempted

    def handle_exception(self, exception: Exception, context: str = "unknown", **kwargs):
        """Synchronous wrapper for exception handling."""
        self.error_stats['total_errors'] += 1
        self.error_stats['last_error_time'] = datetime.now()

        exc_type = type(exception).__name__
        self.error_stats['errors_by_type'][exc_type] = self.error_stats['errors_by_type'].get(exc_type, 0) + 1
        self.error_stats['errors_by_context'][context] = self.error_stats['errors_by_context'].get(context, 0) + 1

        self.logger.error(f"Exception in {context}: {exception}", exc_info=True)

    def get_error_statistics(self) -> Dict[str, Any]:
        """Get current error statistics"""
        return {
            **self.error_stats,
            'recovery_rate': (
                self.error_stats['recovered_errors'] / max(self.error_stats['total_errors'], 1) * 100
            ),
        }
