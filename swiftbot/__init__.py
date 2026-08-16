"""
SwiftBot - Ultra-Fast Telegram Bot Framework
Copyright (c) 2025 Arjun-M/SwiftBot
Licensed under MIT License

A Telegram bot framework with clean decorator syntax, HTTP/2 connection
pooling, persistent FSM storage, a test harness with a fake pool, typed
callback data, deep linking utilities, full Bot API 2026 support — plus an
advanced feature set: dependency-injected handler pipelines, declarative
command specs with auto ``/help``, an outbound API transformer layer, composable
middleware bundles with error boundaries, update-kind dispatch routing, typed
wizards, state-carrying dialogues, scoped middleware, outgoing throttling, a
fluent reply builder, fallback handlers, graceful shutdown and first-party
plugins.
"""

__version__ = "1.6.0"
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
from .dialogue import Dialogue, DialogueTransitionError
from .scopes import Scope
from .throttle import throttle
from .reply import Reply


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
    "Dialogue",
    "DialogueTransitionError",
    "Scope",
    "throttle",
    "Reply",
]
