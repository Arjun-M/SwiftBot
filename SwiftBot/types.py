"""
Telegram event types for decorators
Copyright (c) 2025 Arjun-M/SwiftBot
"""

import re
from typing import Union, List, Callable, Optional, Pattern
from dataclasses import dataclass


@dataclass
class User:
    """Telegram user object"""
    id: int
    is_bot: bool
    first_name: str
    last_name: Optional[str] = None
    username: Optional[str] = None
    language_code: Optional[str] = None


@dataclass
class Chat:
    """Telegram chat object"""
    id: int
    type: str  # private, group, supergroup, channel
    title: Optional[str] = None
    username: Optional[str] = None
    first_name: Optional[str] = None
    last_name: Optional[str] = None


class EventType:
    """
    Base class for all event types used in decorators.
    Provides pattern matching and filtering capabilities.

    Copyright (c) 2025 Arjun-M/SwiftBot
    """

    def __init__(
        self,
        text: Optional[str] = None,
        pattern: Optional[Union[str, Pattern, List[Union[str, Pattern]]]] = None,
        func: Optional[Callable] = None,
        incoming: bool = True,
        outgoing: bool = False,
        **kwargs
    ):
        """
        Initialize event type with filters.

        Args:
            text: Exact text to match
            pattern: Regex pattern(s) to match
            func: Custom filter function
            incoming: Match incoming messages
            outgoing: Match outgoing messages
            **kwargs: Additional filters (chat_id, user_id, etc.)
        """
        self.text = text
        self.patterns = self._compile_patterns(pattern)
        self.func = func
        self.incoming = incoming
        self.outgoing = outgoing
        self.filters = kwargs

    def _compile_patterns(self, pattern):
        """Compile regex patterns for efficient matching"""
        if pattern is None:
            return []

        if isinstance(pattern, (str, Pattern)):
            pattern = [pattern]

        compiled = []
        for p in pattern:
            if isinstance(p, str):
                compiled.append(re.compile(p))
            else:
                compiled.append(p)
        return compiled

    def matches(self, update) -> Optional[re.Match]:
        """
        Check if update matches this event type.
        Returns regex match object if applicable.
        """
        # Text exact match
        if self.text and hasattr(update, 'text'):
            if update.text != self.text:
                return None

        # Pattern matching
        if self.patterns and hasattr(update, 'text') and update.text:
            for pattern in self.patterns:
                match = pattern.match(update.text)
                if match:
                    return match
            if self.text is None:  # If patterns exist but none match
                return None

        # Custom filter function
        if self.func and not self.func(update):
            return None

        # Additional filters
        for key, value in self.filters.items():
            if not hasattr(update, key):
                return None

            update_value = getattr(update, key)
            if isinstance(value, list):
                if update_value not in value:
                    return None
            elif update_value != value:
                return None

        return True  # Matches


class Message(EventType):
    """
    Message event type for @client.on(Message()) decorator.
    Matches incoming messages with optional filters.

    Example:
        @client.on(Message(text="hello"))
        @client.on(Message(pattern=r"^/start"))
        @client.on(Message(func=lambda m: len(m.text) > 10))

    Copyright (c) 2025 Arjun-M/SwiftBot
    """
    pass


class EditedMessage(EventType):
    """
    Edited message event type.
    Matches when a message is edited.

    Copyright (c) 2025 Arjun-M/SwiftBot
    """
    pass


class CallbackQuery(EventType):
    """
    Callback query event type for inline keyboard buttons.

    Example:
        @client.on(CallbackQuery(data="button_1"))
        @client.on(CallbackQuery(pattern=r"page_(\d+)"))

    Copyright (c) 2025 Arjun-M/SwiftBot
    """

    def __init__(self, data: Optional[str] = None, **kwargs):
        """
        Args:
            data: Exact callback data to match
        """
        if data:
            kwargs['data'] = data
        super().__init__(**kwargs)


class InlineQuery(EventType):
    """
    Inline query event type for inline mode.

    Example:
        @client.on(InlineQuery())
        @client.on(InlineQuery(pattern=r"^search (.+)"))

    Copyright (c) 2025 Arjun-M/SwiftBot
    """
    pass


class ChatMemberUpdated(EventType):
    """
    Chat member status update event.
    Triggered when a user joins, leaves, or has their status changed.

    Copyright (c) 2025 Arjun-M/SwiftBot
    """
    pass


class PollAnswer(EventType):
    """
    Poll answer event type.
    Triggered when a user answers a poll.

    Copyright (c) 2025 Arjun-M/SwiftBot
    """
    pass


class PreCheckoutQuery(EventType):
    """
    Pre-checkout query for payments.

    Copyright (c) 2025 Arjun-M/SwiftBot
    """
    pass


class ShippingQuery(EventType):
    """
    Shipping query for payments.

    Copyright (c) 2025 Arjun-M/SwiftBot
    """
    pass


class ChosenInlineResult(EventType):
    """
    Chosen inline result event.
    Triggered when user chooses an inline query result.

    Copyright (c) 2025 Arjun-M/SwiftBot
    """
    pass
