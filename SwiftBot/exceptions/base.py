"""
Base exception classes for SwiftBot
Copyright (c) 2025 Arjun-M/SwiftBot
"""

class SwiftBotException(Exception):
    """Base exception class for all SwiftBot exceptions"""

    def __init__(self, message: str, error_code: str = None, context: dict = None):
        self.message = message
        self.error_code = error_code
        self.context = context or {}
        super().__init__(self.message)

    def __str__(self):
        if self.error_code:
            return f"[{self.error_code}] {self.message}"
        return self.message

    def to_dict(self):
        return {
            'type': self.__class__.__name__,
            'message': self.message,
            'error_code': self.error_code,
            'context': self.context
        }


class SwiftBotError(SwiftBotException):
    """General SwiftBot error"""
    pass


class ConfigurationError(SwiftBotException):
    """Configuration related errors"""
    pass


class ValidationError(SwiftBotException):
    """Input validation errors"""
    pass
