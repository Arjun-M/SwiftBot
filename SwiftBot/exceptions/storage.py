"""
Storage related exceptions for SwiftBot
Copyright (c) 2025 Arjun-M/SwiftBot
"""

from .base import SwiftBotException


class StorageError(SwiftBotException):
    """Base class for storage related errors"""
    pass


class ConnectionError(StorageError):
    """Storage connection errors"""
    pass


class SerializationError(StorageError):
    """Data serialization/deserialization errors"""
    pass


class ValidationError(StorageError):
    """Storage validation errors"""
    pass
