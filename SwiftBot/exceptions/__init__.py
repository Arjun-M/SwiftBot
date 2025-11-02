"""
SwiftBot Exceptions Module
Copyright (c) 2025 Arjun-M/SwiftBot
"""

from .base import SwiftBotException, SwiftBotError, ConfigurationError, ValidationError
from .handlers import CentralizedExceptionHandler
from .api import APIError, NetworkError

__all__ = [
    'SwiftBotException',
    'SwiftBotError', 
    'ConfigurationError',
    'ValidationError',
    'CentralizedExceptionHandler',
    'APIError',
    'NetworkError'
]
