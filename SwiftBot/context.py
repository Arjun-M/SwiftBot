"""
Rich context object passed to all event handlers with proper initialization
Copyright (c) 2025 Arjun-M/SwiftBot
"""

from typing import Optional, Any, Dict, List
import re
import logging
from .update_types import Update, Message as MessageType, User, Chat

logger = logging.getLogger(__name__)

class MemoryStorage:
    def __init__(self):
        self.data = {}

    async def set(self, key, value):
        self.data[key] = value

    async def get(self, key):
        return self.data.get(key)

    async def delete(self, key):
        self.data.pop(key, None)

class Context:
    """
    Context object providing easy access to update data and bot methods.
    Passed to all event handlers as the first parameter.

    Features:
    - Access to complete Update object via ctx.update
    - Raw JSON via ctx.update.raw
    - Convenient shortcuts for common data
    - Helper methods for sending messages
    - State management
    - User data access

    Example:
        @client.on(Message())
        async def handler(ctx):
            # Access complete update
            update_type = ctx.update.get_update_type()
            raw_json = ctx.update.raw

            # Use shortcuts
            await ctx.reply("Hello!")
            user_name = ctx.user.first_name
            chat_id = ctx.chat.id

    Copyright (c) 2025 Arjun-M/SwiftBot
    """

    def __init__(self, bot, update: Update, update_obj: Any, match: Optional[re.Match] = None):
        """
        Initialize context with update data.
        FIXED: Proper parameter handling and field extraction.

        Args:
            bot: SwiftBot instance
            update: Complete Update object
            update_obj: Specific update object (message, callback_query, etc.)
            match: Regex match object if pattern matched
        """
        self.bot = bot
        self.client = bot  # Alias

        # Store complete update object
        self.update = update  # Complete Update with all types
        self._update_obj = update_obj  # Specific object (message, callback, etc.)
        self.match = match

        # Initialize common fields with safe defaults
        self.message = None
        self.user = None
        self.chat = None
        self.text = None
        self.caption = None
        self.callback_query = None
        self.inline_query = None
        self.data = None  # For callback queries
        self.query = None  # For inline queries

        # Extract common fields based on update type
        try:
            self._extract_common_fields(update_obj)
        except Exception as e:
            logger.error(f"Error extracting fields from update: {e}")

        # Parse command arguments
        self.args = []
        if self.text and self.text.startswith('/'):
            try:
                parts = self.text.split(maxsplit=1)
                if len(parts) > 1:
                    self.args = parts[1].split()
            except Exception as e:
                logger.error(f"Error parsing command arguments: {e}")

        # Middleware data storage
        self.middleware_data: Dict[str, Any] = {}

        self.user_data = MemoryStorage()
        self.chat_data = MemoryStorage()
        self.state = None

    def _extract_common_fields(self, update_obj):
        """Extract common fields from update object with robust error handling"""
        if not update_obj:
            return

        try:
            # Handle Message objects
            if isinstance(update_obj, MessageType):
                self.message = update_obj
                self.user = update_obj.from_user
                self.chat = update_obj.chat
                self.text = update_obj.text
                self.caption = update_obj.caption

            # Handle CallbackQuery objects
            elif hasattr(update_obj, 'message') and hasattr(update_obj, 'data'):
                self.callback_query = update_obj
                self.message = update_obj.message
                self.user = update_obj.from_user
                self.chat = update_obj.message.chat if update_obj.message else None
                self.text = update_obj.message.text if update_obj.message else None
                self.caption = update_obj.message.caption if update_obj.message else None
                self.data = update_obj.data  # Callback data

            # Handle InlineQuery objects
            elif hasattr(update_obj, 'query') and hasattr(update_obj, 'from_user'):
                self.inline_query = update_obj
                self.user = update_obj.from_user
                self.query = update_obj.query
                self.chat = None
                self.text = update_obj.query
                self.caption = None

            # Handle ChatMemberUpdated objects
            elif hasattr(update_obj, 'new_chat_member'):
                self.chat_member = update_obj
                self.user = update_obj.from_user
                self.chat = update_obj.chat
                self.old_member = update_obj.old_chat_member
                self.new_member = update_obj.new_chat_member
                self.text = None
                self.caption = None

            # Handle PollAnswer objects
            elif hasattr(update_obj, 'poll_id'):
                self.poll_answer = update_obj
                self.user = update_obj.user
                self.poll_id = update_obj.poll_id
                self.option_ids = update_obj.option_ids
                self.chat = None
                self.text = None
                self.caption = None

            # Generic fallback for other types
            else:
                # Try to extract common fields safely
                self.message = getattr(update_obj, 'message', None)

                # Try multiple ways to get user
                self.user = (getattr(update_obj, 'from_user', None) or 
                           getattr(update_obj, 'user', None) or
                           getattr(getattr(update_obj, 'message', None), 'from_user', None))

                # Try to get chat
                self.chat = (getattr(update_obj, 'chat', None) or
                           getattr(getattr(update_obj, 'message', None), 'chat', None))

                # Try to get text
                self.text = (getattr(update_obj, 'text', None) or
                           getattr(getattr(update_obj, 'message', None), 'text', None))

                # Try to get caption
                self.caption = (getattr(update_obj, 'caption', None) or
                              getattr(getattr(update_obj, 'message', None), 'caption', None))

        except Exception as e:
            logger.error(f"Error in _extract_common_fields: {e}")
            # Set safe defaults
            self.message = None
            self.user = None
            self.chat = None
            self.text = None
            self.caption = None

    # ===================
    # Message Methods
    # ===================

    async def reply(self, text: str, **kwargs):
        """
        Reply to the current message.

        Args:
            text: Message text
            **kwargs: Additional parameters (parse_mode, reply_markup, etc.)

        Returns:
            Sent message object
        """
        if not self.chat:
            raise ValueError("No chat to reply to")

        try:
            return await self.bot.api.send_message(
                chat_id=self.chat.id,
                text=text,
                **kwargs
            )
        except Exception as e:
            logger.error(f"Error sending reply: {e}")
            raise

    async def edit(self, text: str, **kwargs):
        """
        Edit the current message.

        Args:
            text: New message text
            **kwargs: Additional parameters

        Returns:
            Edited message object
        """
        try:
            if hasattr(self, 'callback_query') and self.callback_query:
                return await self.bot.api.edit_message_text(
                    text=text,
                    chat_id=self.chat.id,
                    message_id=self.message.message_id,
                    **kwargs
                )
            elif self.message:
                return await self.bot.api.edit_message_text(
                    text=text,
                    chat_id=self.chat.id,
                    message_id=self.message.message_id,
                    **kwargs
                )
            else:
                raise ValueError("No message to edit")
        except Exception as e:
            logger.error(f"Error editing message: {e}")
            raise

    async def delete(self):
        """Delete the current message"""
        if not self.message:
            raise ValueError("No message to delete")

        try:
            return await self.bot.api.delete_message(
                chat_id=self.chat.id,
                message_id=self.message.message_id
            )
        except Exception as e:
            logger.error(f"Error deleting message: {e}")
            raise

    async def forward_to(self, chat_id: int):
        """
        Forward the current message to another chat.

        Args:
            chat_id: Target chat ID

        Returns:
            Forwarded message object
        """
        if not self.message:
            raise ValueError("No message to forward")

        try:
            return await self.bot.api.forward_message(
                chat_id=chat_id,
                from_chat_id=self.chat.id,
                message_id=self.message.message_id
            )
        except Exception as e:
            logger.error(f"Error forwarding message: {e}")
            raise

    async def answer_callback(self, text: Optional[str] = None, show_alert: bool = False):
        """
        Answer callback query (for inline keyboard buttons).

        Args:
            text: Notification text
            show_alert: Show alert instead of notification

        Returns:
            True if successful
        """
        if not hasattr(self, 'callback_query') or not self.callback_query:
            raise ValueError("Not a callback query")

        try:
            return await self.bot.api.answer_callback_query(
                callback_query_id=self.callback_query.id,
                text=text,
                show_alert=show_alert
            )
        except Exception as e:
            logger.error(f"Error answering callback query: {e}")
            raise

    # ===================
    # Media Methods
    # ===================

    async def send_photo(self, photo, caption: Optional[str] = None, **kwargs):
        """Send a photo to the current chat"""
        if not self.chat:
            raise ValueError("No chat to send photo to")

        try:
            return await self.bot.api.send_photo(
                chat_id=self.chat.id,
                photo=photo,
                caption=caption,
                **kwargs
            )
        except Exception as e:
            logger.error(f"Error sending photo: {e}")
            raise

    async def send_document(self, document, caption: Optional[str] = None, **kwargs):
        """Send a document to the current chat"""
        if not self.chat:
            raise ValueError("No chat to send document to")

        try:
            return await self.bot.api.send_document(
                chat_id=self.chat.id,
                document=document,
                caption=caption,
                **kwargs
            )
        except Exception as e:
            logger.error(f"Error sending document: {e}")
            raise

    async def send_video(self, video, caption: Optional[str] = None, **kwargs):
        """Send a video to the current chat"""
        if not self.chat:
            raise ValueError("No chat to send video to")

        try:
            return await self.bot.api.send_video(
                chat_id=self.chat.id,
                video=video,
                caption=caption,
                **kwargs
            )
        except Exception as e:
            logger.error(f"Error sending video: {e}")
            raise

    async def send_audio(self, audio, caption: Optional[str] = None, **kwargs):
        """Send audio to the current chat"""
        if not self.chat:
            raise ValueError("No chat to send audio to")

        try:
            return await self.bot.api.send_audio(
                chat_id=self.chat.id,
                audio=audio,
                caption=caption,
                **kwargs
            )
        except Exception as e:
            logger.error(f"Error sending audio: {e}")
            raise

    async def send_voice(self, voice, caption: Optional[str] = None, **kwargs):
        """Send voice message to the current chat"""
        if not self.chat:
            raise ValueError("No chat to send voice to")

        try:
            return await self.bot.api.send_voice(
                chat_id=self.chat.id,
                voice=voice,
                caption=caption,
                **kwargs
            )
        except Exception as e:
            logger.error(f"Error sending voice: {e}")
            raise

    async def send_animation(self, animation, caption: Optional[str] = None, **kwargs):
        """Send animation to the current chat"""
        if not self.chat:
            raise ValueError("No chat to send animation to")

        try:
            return await self.bot.api.send_animation(
                chat_id=self.chat.id,
                animation=animation,
                caption=caption,
                **kwargs
            )
        except Exception as e:
            logger.error(f"Error sending animation: {e}")
            raise

    async def send_sticker(self, sticker, **kwargs):
        """Send sticker to the current chat"""
        if not self.chat:
            raise ValueError("No chat to send sticker to")

        try:
            return await self.bot.api.send_sticker(
                chat_id=self.chat.id,
                sticker=sticker,
                **kwargs
            )
        except Exception as e:
            logger.error(f"Error sending sticker: {e}")
            raise

    async def send_poll(self, question: str, options: List[str], **kwargs):
        """Send poll to the current chat"""
        if not self.chat:
            raise ValueError("No chat to send poll to")

        try:
            return await self.bot.api.send_poll(
                chat_id=self.chat.id,
                question=question,
                options=options,
                **kwargs
            )
        except Exception as e:
            logger.error(f"Error sending poll: {e}")
            raise

    async def send_location(self, latitude: float, longitude: float, **kwargs):
        """Send location to the current chat"""
        if not self.chat:
            raise ValueError("No chat to send location to")

        try:
            return await self.bot.api.send_location(
                chat_id=self.chat.id,
                latitude=latitude,
                longitude=longitude,
                **kwargs
            )
        except Exception as e:
            logger.error(f"Error sending location: {e}")
            raise

    # ===================
    # State Management (FSM)
    # ===================

    async def set_state(self, state):
        """Set user state for FSM (Finite State Machine)"""
        if self.user_data:
            try:
                await self.user_data.set("state", state)
                self.state = state
            except Exception as e:
                logger.error(f"Error setting state: {e}")

    async def get_state(self):
        """Get current user state"""
        if self.user_data:
            try:
                self.state = await self.user_data.get("state")
                return self.state
            except Exception as e:
                logger.error(f"Error getting state: {e}")
        return None

    async def clear_state(self):
        """Clear user state"""
        if self.user_data:
            try:
                await self.user_data.delete("state")
                self.state = None
            except Exception as e:
                logger.error(f"Error clearing state: {e}")

    
