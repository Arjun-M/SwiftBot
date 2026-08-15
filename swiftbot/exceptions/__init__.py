"""
SwiftBot Exceptions Module
Copyright (c) 2025 Arjun-M/SwiftBot
"""

from .base import SwiftBotException, SwiftBotError, ConfigurationError, ValidationError
from .handlers import CentralizedExceptionHandler
from .api import APIError, NetworkError
from .telegram import (
    TelegramError,
    BadRequest,
    Unauthorized,
    Forbidden,
    UserNotFound,
    ChatNotFound,
    MessageNotModified,
    MessageToDeleteNotFound,
    MessageToEditNotFound,
    MessageIdInvalid,
    ChatWriteForbidden,
    ButtonDataInvalid,
    MessageCaptionTooLong,
    MessageTextIsEmpty,
    TooManyRequests,
    MigrateToChat,
    raise_telegram_error,
)

__all__ = [
    'SwiftBotException',
    'SwiftBotError', 
    'ConfigurationError',
    'ValidationError',
    'CentralizedExceptionHandler',
    'APIError',
    'NetworkError',
    'TelegramError',
    'BadRequest',
    'Unauthorized',
    'Forbidden',
    'UserNotFound',
    'ChatNotFound',
    'MessageNotModified',
    'MessageToDeleteNotFound',
    'MessageToEditNotFound',
    'MessageIdInvalid',
    'ChatWriteForbidden',
    'ButtonDataInvalid',
    'MessageCaptionTooLong',
    'MessageTextIsEmpty',
    'TooManyRequests',
    'MigrateToChat',
    'raise_telegram_error',
]
