"""
SwiftBot - Ultra-Fast Telegram Bot Framework
Copyright (c) 2025 Arjun-M/SwiftBot
Licensed under MIT License

A blazing-fast Telegram bot framework with Telethon-inspired syntax,
30× faster routing, enterprise-grade middleware, and HTTP/2 connection pooling.
"""

__version__ = "1.0.1"
__author__ = "Arjun-M"
__license__ = "MIT"

from .client import SwiftBot
from .context import Context
from .types import Message, CallbackQuery, InlineQuery, EditedMessage, ChatMemberUpdated, EventType
from .exceptions import SwiftBotException, SwiftBotError, ConfigurationError
from .filters import Filters
from .update_types import Update
from .button import Button, InlineKeyboard, ReplyKeyboard, RemoveKeyboard


__all__ = [
    "SwiftBot",
    "Context", 
    "Message",
    "CallbackQuery",
    "InlineQuery", 
    "EditedMessage",
    "ChatMemberUpdated",
    "EventType",
    "Filters",
    "Update",

    "Button",
    "InlineKeyboard", 
    "ReplyKeyboard",
    "RemoveKeyboard",
]
