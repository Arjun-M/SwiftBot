"""
Composable filter system for message filtering
Copyright (c) 2025 Arjun-M/SwiftBot
"""

import re
from typing import Union, List, Callable, Optional


class Filter:
    """
    Base filter class supporting composition with & (AND), | (OR), ~ (NOT).
    Allows building complex filters like: F.text & F.private & ~F.forwarded

    Copyright (c) 2025 Arjun-M/SwiftBot
    """

    def __call__(self, message):
        """Check if message passes this filter"""
        raise NotImplementedError

    def __and__(self, other):
        """Combine filters with AND: filter1 & filter2"""
        return AndFilter(self, other)

    def __or__(self, other):
        """Combine filters with OR: filter1 | filter2"""
        return OrFilter(self, other)

    def __invert__(self):
        """Negate filter with NOT: ~filter"""
        return NotFilter(self)


class AndFilter(Filter):
    """Combines two filters with AND logic"""

    def __init__(self, filter1: Filter, filter2: Filter):
        self.filter1 = filter1
        self.filter2 = filter2

    def __call__(self, message):
        return self.filter1(message) and self.filter2(message)


class OrFilter(Filter):
    """Combines two filters with OR logic"""

    def __init__(self, filter1: Filter, filter2: Filter):
        self.filter1 = filter1
        self.filter2 = filter2

    def __call__(self, message):
        return self.filter1(message) or self.filter2(message)


class NotFilter(Filter):
    """Negates a filter with NOT logic"""

    def __init__(self, filter: Filter):
        self.filter = filter

    def __call__(self, message):
        return not self.filter(message)


class TextFilter(Filter):
    """Filters messages that have text"""

    def __call__(self, message):
        return hasattr(message, 'text') and message.text is not None


class PrivateFilter(Filter):
    """Filters private chat messages"""

    def __call__(self, message):
        return hasattr(message, 'chat') and message.chat.type == 'private'


class GroupFilter(Filter):
    """Filters group/supergroup chat messages"""

    def __call__(self, message):
        return hasattr(message, 'chat') and message.chat.type in ('group', 'supergroup')


class ForwardedFilter(Filter):
    """Filters forwarded messages"""

    def __call__(self, message):
        return hasattr(message, 'forward_from') and message.forward_from is not None


class ReplyFilter(Filter):
    """Filters messages that are replies"""

    def __call__(self, message):
        return hasattr(message, 'reply_to_message') and message.reply_to_message is not None


class PhotoFilter(Filter):
    """Filters photo messages"""

    def __call__(self, message):
        return hasattr(message, 'photo') and message.photo is not None


class VideoFilter(Filter):
    """Filters video messages"""

    def __call__(self, message):
        return hasattr(message, 'video') and message.video is not None


class AudioFilter(Filter):
    """Filters audio messages"""

    def __call__(self, message):
        return hasattr(message, 'audio') and message.audio is not None


class DocumentFilter(Filter):
    """Filters document messages"""

    def __call__(self, message):
        return hasattr(message, 'document') and message.document is not None


class VoiceFilter(Filter):
    """Filters voice messages"""

    def __call__(self, message):
        return hasattr(message, 'voice') and message.voice is not None


class StickerFilter(Filter):
    """Filters sticker messages"""

    def __call__(self, message):
        return hasattr(message, 'sticker') and message.sticker is not None


class CommandFilter(Filter):
    """
    Filters command messages.
    Supports single command or list of commands.
    """

    def __init__(self, commands: Union[str, List[str]]):
        """
        Args:
            commands: Command name(s) without '/' prefix
        """
        if isinstance(commands, str):
            commands = [commands]
        self.commands = [f'/{cmd}' if not cmd.startswith('/') else cmd for cmd in commands]

    def __call__(self, message):
        if not hasattr(message, 'text') or not message.text:
            return False

        text = message.text.strip()
        for cmd in self.commands:
            if text == cmd or text.startswith(f'{cmd} ') or text.startswith(f'{cmd}@'):
                return True
        return False


class RegexFilter(Filter):
    """
    Filters messages matching a regex pattern.
    """

    def __init__(self, pattern: Union[str, re.Pattern]):
        """
        Args:
            pattern: Regex pattern to match
        """
        self.pattern = re.compile(pattern) if isinstance(pattern, str) else pattern

    def __call__(self, message):
        if not hasattr(message, 'text') or not message.text:
            return False
        return self.pattern.match(message.text) is not None


class CaptionRegexFilter(Filter):
    """Filters media messages with caption matching regex"""

    def __init__(self, pattern: Union[str, re.Pattern]):
        self.pattern = re.compile(pattern) if isinstance(pattern, str) else pattern

    def __call__(self, message):
        if not hasattr(message, 'caption') or not message.caption:
            return False
        return self.pattern.match(message.caption) is not None


class CustomFilter(Filter):
    """Custom filter using a callable function"""

    def __init__(self, func: Callable):
        """
        Args:
            func: Function that takes message and returns bool
        """
        self.func = func

    def __call__(self, message):
        return self.func(message)


class Filters:
    """
    Collection of built-in filters for easy access.

    Example usage:
        from swiftbot.filters import Filters as F

        @client.on(Message(F.text & F.private))
        @client.on(Message(F.photo | F.video))
        @client.on(Message(F.command("start")))
        @client.on(Message(F.regex(r"^\d+$")))

    Copyright (c) 2025 Arjun-M/SwiftBot
    """

    # Basic filters
    text = TextFilter()
    private = PrivateFilter()
    group = GroupFilter()
    forwarded = ForwardedFilter()
    reply = ReplyFilter()

    # Media filters
    photo = PhotoFilter()
    video = VideoFilter()
    audio = AudioFilter()
    document = DocumentFilter()
    voice = VoiceFilter()
    sticker = StickerFilter()

    @staticmethod
    def command(commands: Union[str, List[str]]) -> CommandFilter:
        """
        Create command filter.

        Args:
            commands: Command name(s) without '/' prefix

        Returns:
            CommandFilter instance
        """
        return CommandFilter(commands)

    @staticmethod
    def regex(pattern: Union[str, re.Pattern]) -> RegexFilter:
        """
        Create regex filter for message text.

        Args:
            pattern: Regex pattern

        Returns:
            RegexFilter instance
        """
        return RegexFilter(pattern)

    @staticmethod
    def caption_regex(pattern: Union[str, re.Pattern]) -> CaptionRegexFilter:
        """
        Create regex filter for media caption.

        Args:
            pattern: Regex pattern

        Returns:
            CaptionRegexFilter instance
        """
        return CaptionRegexFilter(pattern)

    @staticmethod
    def custom(func: Callable) -> CustomFilter:
        """
        Create custom filter from function.

        Args:
            func: Function that takes message and returns bool

        Returns:
            CustomFilter instance
        """
        return CustomFilter(func)
