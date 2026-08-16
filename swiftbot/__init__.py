"""
SwiftBot - Ultra-Fast Telegram Bot Framework
Copyright (c) 2025 Arjun-M/SwiftBot
Licensed under MIT License

A Telegram bot framework with Telethon-inspired syntax, HTTP/2 connection
pooling, persistent FSM storage, a test harness with a fake bot, typed
callback data, deep linking utilities, full Bot API 2026 support — and the
v1.5 standout set: declarative dependency-injected pipelines (teloxide
dptree-style), typed command specs with auto ``/help``, grammy-style outbound
transformers, composable middleware bundles with error boundaries, update-kind
dispatch routing, typed wizards, graceful shutdown and first-party plugins.
"""

__version__ = "1.5.0"
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
from .pipeline import Pipeline
from .commands import BotCommands, CommandsMiddleware
from . import transformer
from .composer import Composer
from .wizard import Wizard
from . import plugins
from .filters import F


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
    "Pipeline",
    "BotCommands",
    "CommandsMiddleware",
    "transformer",
    "Composer",
    "Wizard",
    "plugins",
    "F",
]
