"""
Enhanced composable filter system with EventType integration
Copyright (c) 2025 Arjun-M/SwiftBot
"""

import re
import logging
from typing import Union, List, Callable, Optional, Any
from functools import wraps

logger = logging.getLogger(__name__)


class Filter:
    """
    Base filter class supporting composition with & (AND), | (OR), ~ (NOT).
    Allows building complex filters like: F.text & F.private & ~F.forwarded
    Now integrated with EventType system for seamless usage.

    Copyright (c) 2025 Arjun-M/SwiftBot
    """

    def __call__(self, message):
        raise NotImplementedError

    def __and__(self, other):
        return AndFilter(self, other)

    def __or__(self, other):
        return OrFilter(self, other)

    def __invert__(self):
        return NotFilter(self)


class AndFilter(Filter):
    def __init__(self, filter1: Filter, filter2: Filter):
        self.filter1 = filter1
        self.filter2 = filter2

    def __call__(self, message):
        try:
            return bool(self.filter1(message)) and bool(self.filter2(message))
        except Exception as e:
            logger.error(f"Error in AndFilter: {e}")
            return False

class OrFilter(Filter):
    def __init__(self, filter1: Filter, filter2: Filter):
        self.filter1 = filter1
        self.filter2 = filter2

    def __call__(self, message):
        try:
            return bool(self.filter1(message)) or bool(self.filter2(message))
        except Exception as e:
            logger.error(f"Error in OrFilter: {e}")
            return False

class NotFilter(Filter):
    def __init__(self, filter: Filter):
        self.filter = filter

    def __call__(self, message):
        try:
            return not bool(self.filter(message))
        except Exception as e:
            logger.error(f"Error in NotFilter: {e}")
            return True
            

class TextFilter(Filter):
    """Filters messages that have text"""

    def __call__(self, message):
        try:
            return hasattr(message, 'text') and message.text is not None and message.text.strip() != ''
        except Exception:
            return False


class PrivateFilter(Filter):
    """Filters private chat messages"""

    def __call__(self, message):
        try:
            return hasattr(message, 'chat') and message.chat and message.chat.type == 'private'
        except Exception:
            return False


class GroupFilter(Filter):
    """Filters group/supergroup chat messages"""

    def __call__(self, message):
        try:
            return (hasattr(message, 'chat') and message.chat and 
                   message.chat.type in ('group', 'supergroup'))
        except Exception:
            return False


class ChannelFilter(Filter):
    """Filters channel messages"""

    def __call__(self, message):
        try:
            return hasattr(message, 'chat') and message.chat and message.chat.type == 'channel'
        except Exception:
            return False


class ForwardedFilter(Filter):
    """Filters forwarded messages"""

    def __call__(self, message):
        try:
            return (hasattr(message, 'forward_from') and message.forward_from is not None) or \
                   (hasattr(message, 'forward_from_chat') and message.forward_from_chat is not None)
        except Exception:
            return False


class ReplyFilter(Filter):
    """Filters messages that are replies"""

    def __call__(self, message):
        try:
            return hasattr(message, 'reply_to_message') and message.reply_to_message is not None
        except Exception:
            return False


class PhotoFilter(Filter):
    """Filters photo messages"""

    def __call__(self, message):
        try:
            return hasattr(message, 'photo') and message.photo is not None
        except Exception:
            return False


class VideoFilter(Filter):
    """Filters video messages"""

    def __call__(self, message):
        try:
            return hasattr(message, 'video') and message.video is not None
        except Exception:
            return False


class AudioFilter(Filter):
    """Filters audio messages"""

    def __call__(self, message):
        try:
            return hasattr(message, 'audio') and message.audio is not None
        except Exception:
            return False


class DocumentFilter(Filter):
    """Filters document messages"""

    def __call__(self, message):
        try:
            return hasattr(message, 'document') and message.document is not None
        except Exception:
            return False


class VoiceFilter(Filter):
    """Filters voice messages"""

    def __call__(self, message):
        try:
            return hasattr(message, 'voice') and message.voice is not None
        except Exception:
            return False


class StickerFilter(Filter):
    """Filters sticker messages"""

    def __call__(self, message):
        try:
            return hasattr(message, 'sticker') and message.sticker is not None
        except Exception:
            return False


class AnimationFilter(Filter):
    """Filters animation/GIF messages"""

    def __call__(self, message):
        try:
            return hasattr(message, 'animation') and message.animation is not None
        except Exception:
            return False


class VideoNoteFilter(Filter):
    """Filters video note messages"""

    def __call__(self, message):
        try:
            return hasattr(message, 'video_note') and message.video_note is not None
        except Exception:
            return False


class LocationFilter(Filter):
    """Filters location messages"""

    def __call__(self, message):
        try:
            return hasattr(message, 'location') and message.location is not None
        except Exception:
            return False


class ContactFilter(Filter):
    """Filters contact messages"""

    def __call__(self, message):
        try:
            return hasattr(message, 'contact') and message.contact is not None
        except Exception:
            return False


class MediaFilter(Filter):
    """Filters any media messages (photo, video, audio, document, etc.)"""

    def __call__(self, message):
        try:
            media_types = ['photo', 'video', 'audio', 'document', 'voice', 
                          'sticker', 'animation', 'video_note']
            return any(hasattr(message, media_type) and getattr(message, media_type) is not None 
                      for media_type in media_types)
        except Exception:
            return False


class CommandFilter(Filter):
    """
    Filters command messages.
    Supports single command or list of commands.
    Enhanced with better command parsing.
    """

    def __init__(self, commands: Union[str, List[str]]):
        """
        Args:
            commands: Command name(s) without '/' prefix
        """
        if isinstance(commands, str):
            commands = [commands]
        # Normalize commands - ensure they start with /
        self.commands = [f'/{cmd}' if not cmd.startswith('/') else cmd for cmd in commands]
        # Store lowercase versions for case-insensitive matching
        self.commands_lower = [cmd.lower() for cmd in self.commands]

    def __call__(self, message):
        try:
            if not hasattr(message, 'text') or not message.text:
                return False

            text = message.text.strip()
            if not text.startswith('/'):
                return False

            # Extract command part (before space and @)
            command_part = text.split()[0].split('@')[0].lower()

            return command_part in self.commands_lower
        except Exception:
            return False


class RegexFilter(Filter):
    """
    Filters messages matching a regex pattern.
    Enhanced with better error handling and compilation caching.
    """

    def __init__(self, pattern: Union[str, re.Pattern], flags: int = 0):
        """
        Args:
            pattern: Regex pattern to match
            flags: Regex flags (re.IGNORECASE, etc.)
        """
        try:
            if isinstance(pattern, str):
                self.pattern = re.compile(pattern, flags)
            else:
                self.pattern = pattern
        except re.error as e:
            logger.error(f"Invalid regex pattern '{pattern}': {e}")
            raise

    def __call__(self, message):
        try:
            if not hasattr(message, 'text') or not message.text:
                return False
            return self.pattern.search(message.text) is not None
        except Exception:
            return False


class CaptionRegexFilter(Filter):
    """Filters media messages with caption matching regex"""

    def __init__(self, pattern: Union[str, re.Pattern], flags: int = 0):
        try:
            if isinstance(pattern, str):
                self.pattern = re.compile(pattern, flags)
            else:
                self.pattern = pattern
        except re.error as e:
            logger.error(f"Invalid regex pattern '{pattern}': {e}")
            raise

    def __call__(self, message):
        try:
            if not hasattr(message, 'caption') or not message.caption:
                return False
            return self.pattern.search(message.caption) is not None
        except Exception:
            return False


class CommandFilter(Filter):
    """
    Filters command messages with proper validation.
    BUG FIX: Added input validation for command strings
    """
    def __init__(self, commands: Union[str, List[str]]):
        if isinstance(commands, str):
            commands = [commands]
        
        # Validate commands
        validated_commands = []
        for cmd in commands:
            if not isinstance(cmd, str):
                logger.warning(f"Skipping non-string command: {cmd}")
                continue
            # Ensure command starts with /
            if not cmd.startswith('/'):
                cmd = '/' + cmd
            validated_commands.append(cmd)
        
        if not validated_commands:
            raise ValueError("At least one valid command string required")
        
        self.commands = validated_commands
        self.commands_lower = [cmd.lower() for cmd in self.commands]

    def __call__(self, message):
        try:
            if not hasattr(message, 'text') or not message.text:
                return False

            text = message.text.strip()
            if not text.startswith('/'):
                return False

            # Extract command part (before space and @)
            command_part = text.split()[0].split('@')[0].lower()

            return command_part in self.commands_lower
        except Exception as e:
            logger.error(f"Error in CommandFilter: {e}")
            return False

class UserFilter(Filter):
    """
    Filters messages from specific users with ID validation.
    BUG FIX: Added validation of user IDs
    """
    def __init__(self, user_ids: Union[int, List[int]]):
        if isinstance(user_ids, int):
            user_ids = [user_ids]
        
        # Validate IDs
        validated_ids = []
        for uid in user_ids:
            if not isinstance(uid, int):
                logger.warning(f"Skipping non-integer user ID: {uid}")
                continue
            if uid <= 0:
                logger.warning(f"Skipping invalid user ID: {uid}")
                continue
            validated_ids.append(uid)
        
        if not validated_ids:
            raise ValueError("At least one valid user ID required")
        
        self.user_ids = set(validated_ids)

    def __call__(self, message):
        try:
            return (hasattr(message, 'from_user') and 
                   message.from_user and 
                   message.from_user.id in self.user_ids)
        except Exception as e:
            logger.error(f"Error in UserFilter: {e}")
            return False

class ChatFilter(Filter):
    """
    Filters messages from specific chats with ID validation.
    BUG FIX: Added validation of chat IDs
    """
    def __init__(self, chat_ids: Union[int, List[int]]):
        if isinstance(chat_ids, int):
            chat_ids = [chat_ids]
        
        # Validate IDs
        validated_ids = []
        for cid in chat_ids:
            if not isinstance(cid, int):
                logger.warning(f"Skipping non-integer chat ID: {cid}")
                continue
            validated_ids.append(cid)
        
        if not validated_ids:
            raise ValueError("At least one valid chat ID required")
        
        self.chat_ids = set(validated_ids)

    def __call__(self, message):
        try:
            return (hasattr(message, 'chat') and 
                   message.chat and 
                   message.chat.id in self.chat_ids)
        except Exception as e:
            logger.error(f"Error in ChatFilter: {e}")
            return False

class CustomFilter(Filter):
    """
    Custom filter with improved exception handling.
    BUG FIX: Better logging with filter name context
    """
    def __init__(self, func: Callable, name: str = "CustomFilter"):
        self.func = func
        self.name = name

    def __call__(self, message):
        try:
            result = self.func(message)
            return bool(result)
        except Exception as e:
            logger.error(f"Error in {self.name}: {e}", exc_info=True)
            return False
 

class Filters:
    """
    Collection of built-in filters for easy access.
    Enhanced with better integration and additional filters.

    Example usage:
        from SwiftBot.filters import Filters as F

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
    channel = ChannelFilter()
    forwarded = ForwardedFilter()
    reply = ReplyFilter()

    # Media filters
    photo = PhotoFilter()
    video = VideoFilter()
    audio = AudioFilter()
    document = DocumentFilter()
    voice = VoiceFilter()
    sticker = StickerFilter()
    animation = AnimationFilter()
    video_note = VideoNoteFilter()
    location = LocationFilter()
    contact = ContactFilter()
    media = MediaFilter()  # Any media

    # Convenience combinations
    media_group = photo | video | audio | document  # Common media types

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
    def regex(pattern: Union[str, re.Pattern], flags: int = 0) -> RegexFilter:
        """
        Create regex filter for message text.

        Args:
            pattern: Regex pattern
            flags: Regex flags

        Returns:
            RegexFilter instance
        """
        return RegexFilter(pattern, flags)

    @staticmethod
    def caption_regex(pattern: Union[str, re.Pattern], flags: int = 0) -> CaptionRegexFilter:
        """
        Create regex filter for media caption.

        Args:
            pattern: Regex pattern
            flags: Regex flags

        Returns:
            CaptionRegexFilter instance
        """
        return CaptionRegexFilter(pattern, flags)

    @staticmethod
    def user(user_ids: Union[int, List[int]]) -> UserFilter:
        """
        Create user filter.

        Args:
            user_ids: User ID(s) to match

        Returns:
            UserFilter instance
        """
        return UserFilter(user_ids)

    @staticmethod
    def chat(chat_ids: Union[int, List[int]]) -> ChatFilter:
        """
        Create chat filter.

        Args:
            chat_ids: Chat ID(s) to match

        Returns:
            ChatFilter instance
        """
        return ChatFilter(chat_ids)

    @staticmethod
    def custom(func: Callable, name: str = "CustomFilter") -> CustomFilter:
        """
        Create custom filter from function.

        Args:
            func: Function that takes message and returns bool
            name: Name for debugging

        Returns:
            CustomFilter instance
        """
        return CustomFilter(func, name)

    @staticmethod
    def all(*filters: Filter) -> Filter:
        """
        Create filter that matches when ALL provided filters match.
        BUG FIX: Proper handling of edge cases
        """
        if not filters:
            return CustomFilter(lambda x: True, "AllowAll")
        if len(filters) == 1:
            return filters[0]
        
        result = filters[0]
        for f in filters[1:]:
            result = result & f
        return result

    @staticmethod
    def any(*filters: Filter) -> Filter:
        """
        Create filter that matches when ANY provided filter matches.
        BUG FIX: Proper handling of edge cases
        """
        if not filters:
            return CustomFilter(lambda x: False, "DenyAll")
        if len(filters) == 1:
            return filters[0]
        
        result = filters[0]
        for f in filters[1:]:
            result = result | f
        return result
