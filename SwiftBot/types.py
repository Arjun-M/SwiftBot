"""
Telegram event types for decorators with integrated filtering
Copyright (c) 2025 Arjun-M/SwiftBot
"""

import re
from typing import Union, List, Callable, Optional, Pattern, Any
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
    Now properly integrated with the filter system.

    Copyright (c) 2025 Arjun-M/SwiftBot
    """

    def __init__(
        self,
        text: Optional[str] = None,
        pattern: Optional[Union[str, Pattern, List[Union[str, Pattern]]]] = None,
        func: Optional[Callable] = None,
        incoming: bool = True,
        outgoing: bool = False,
        filter_func: Optional[Callable] = None,
        **kwargs
    ):
        """
        Initialize event type with filters.

        Args:
            text: Exact text to match
            pattern: Regex pattern(s) to match
            func: Custom filter function (legacy)
            filter_func: New unified filter function
            incoming: Match incoming messages
            outgoing: Match outgoing messages
            **kwargs: Additional filters (chat_id, user_id, etc.)
        """
        self.text = text
        self.patterns = self._compile_patterns(pattern)
        self.func = func  # Legacy support
        self.filter_func = filter_func  # New unified filter
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

    def matches(self, update_obj: Any) -> Optional[re.Match]:
        """
        Check if update matches this event type.
        Returns regex match object if applicable.

        Args:
            update_obj: The specific update object (Message, CallbackQuery, etc.)
        """
        # Apply unified filter first (from Filters system)
        if self.filter_func and not self.filter_func(update_obj):
            return None

        # Text exact match
        if self.text:
            obj_text = None
            if hasattr(update_obj, 'text'):
                obj_text = update_obj.text
            elif hasattr(update_obj, 'data'):  # CallbackQuery
                obj_text = update_obj.data
            elif hasattr(update_obj, 'query'):  # InlineQuery
                obj_text = update_obj.query

            if obj_text != self.text:
                return None

        # Pattern matching
        if self.patterns:
            obj_text = None
            if hasattr(update_obj, 'text'):
                obj_text = update_obj.text
            elif hasattr(update_obj, 'data'):  # CallbackQuery
                obj_text = update_obj.data  
            elif hasattr(update_obj, 'query'):  # InlineQuery
                obj_text = update_obj.query

            if obj_text:
                for pattern in self.patterns:
                    match = pattern.search(obj_text)  # Use search instead of match for flexibility
                    if match:
                        return match

            # If patterns exist but none match and no text filter
            if self.text is None:
                return None

        # Legacy custom filter function
        if self.func and not self.func(update_obj):
            return None

        # Additional filters (more robust checking)
        for key, value in self.filters.items():
            obj_value = None

            # Handle nested attributes like chat.type
            if '.' in key:
                obj = update_obj
                for attr in key.split('.'):
                    if hasattr(obj, attr):
                        obj = getattr(obj, attr)
                    else:
                        return None
                obj_value = obj
            else:
                if not hasattr(update_obj, key):
                    return None
                obj_value = getattr(update_obj, key)

            if isinstance(value, list):
                if obj_value not in value:
                    return None
            elif obj_value != value:
                return None

        return True  # Matches


class Message(EventType):
    """
    Message event type for @client.on(Message()) decorator.
    Matches incoming messages with optional filters.

    Example:
        @client.on(Message(text="hello"))
        @client.on(Message(pattern=r"^/start"))
        @client.on(Message(func=lambda m: len(m.text or '') > 10))

    Copyright (c) 2025 Arjun-M/SwiftBot
    """

    def __init__(self, filter_func=None, **kwargs):
        """Initialize Message event type with optional filter"""
        super().__init__(filter_func=filter_func, **kwargs)


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
