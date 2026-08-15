"""
SwiftBot - Ultra-Fast Telegram Bot Framework
Copyright (c) 2025 Arjun-M/SwiftBot
Licensed under MIT License

A Telegram bot framework with Telethon-inspired syntax, HTTP/2 connection
pooling, persistent FSM storage, a test harness with a fake bot, typed
callback data, deep linking utilities, and full Bot API 2026 support.
"""

__version__ = "1.4.0"
__author__ = "Arjun-M"
__license__ = "MIT"

from .client import SwiftBot
from .context import Context
from .types import Message, CallbackQuery, InlineQuery, EditedMessage, ChatMemberUpdated, EventType
from .exceptions import SwiftBotException, SwiftBotError, ConfigurationError
from .filters import Filters
from .update_types import Update
from .button import Button, InlineKeyboard, ReplyKeyboard, RemoveKeyboard
from .callback_data import CallbackData, CallbackDataInvalid
from . import deep_linking
from . import models
from .testing import FakePool, TestClient


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
    "CallbackData",
    "CallbackDataInvalid",
    "deep_linking",
    "models",
    "FakePool",
    "TestClient",
]
