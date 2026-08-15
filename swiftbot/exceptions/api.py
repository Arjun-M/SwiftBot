"""
API related exceptions for SwiftBot
Copyright (c) 2025 Arjun-M/SwiftBot
"""

from .base import SwiftBotException


class APIError(SwiftBotException):
    """Base class for API related errors"""

    def __init__(self, message: str, response_code: int = None, response_data: dict = None):
        self.response_code = response_code
        self.response_data = response_data or {}
        super().__init__(message, f"API_{response_code}" if response_code else "API_ERROR")


class RateLimitError(APIError):
    """Rate limit exceeded error"""

    def __init__(self, message: str = "Rate limit exceeded", retry_after: int = None):
        self.retry_after = retry_after
        super().__init__(message, 429)


class NetworkError(SwiftBotException):
    """Network connectivity errors"""
    pass


class TimeoutError(NetworkError):
    """Request timeout errors"""
    pass


class AuthenticationError(APIError):
    """Authentication related errors"""

    def __init__(self, message: str = "Authentication failed"):
        super().__init__(message, 401)
