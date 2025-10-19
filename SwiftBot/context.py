"""
Rich context object passed to all event handlers
Copyright (c) 2025 Arjun-M/SwiftBot
"""

from typing import Optional, Any, Dict
import re


class Context:
    """
    Context object providing easy access to update data and bot methods.
    Passed to all event handlers as the first parameter.

    Example:
        @client.on(Message())
        async def handler(ctx):
            await ctx.reply("Hello!")
            user_name = ctx.user.first_name
            chat_id = ctx.chat.id

    Copyright (c) 2025 Arjun-M/SwiftBot
    """

    def __init__(self, bot, update, match: Optional[re.Match] = None):
        """
        Initialize context with update data.

        Args:
            bot: SwiftBot instance
            update: Telegram update object
            match: Regex match object if pattern matched
        """
        self.bot = bot
        self.client = bot  # Alias
        self._update = update
        self.match = match

        # Extract common fields
        self.message = getattr(update, 'message', None) or update
        self.user = getattr(self.message, 'from_user', None)
        self.chat = getattr(self.message, 'chat', None)
        self.text = getattr(self.message, 'text', None)
        self.caption = getattr(self.message, 'caption', None)

        # For callback queries
        if hasattr(update, 'callback_query'):
            self.callback_query = update.callback_query
            self.user = self.callback_query.from_user
            self.message = self.callback_query.message
            if self.message:
                self.chat = self.message.chat

        # For inline queries
        if hasattr(update, 'inline_query'):
            self.inline_query = update.inline_query
            self.user = self.inline_query.from_user
            self.query = self.inline_query.query

        # Parse command arguments
        self.args = []
        if self.text and self.text.startswith('/'):
            parts = self.text.split(maxsplit=1)
            if len(parts) > 1:
                self.args = parts[1].split()

        # Middleware data storage
        self.middleware_data: Dict[str, Any] = {}

        # User/chat data (populated by middleware)
        self.user_data = None
        self.chat_data = None
        self.state = None

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

        return await self.bot.api.send_message(
            chat_id=self.chat.id,
            text=text,
            **kwargs
        )

    async def edit(self, text: str, **kwargs):
        """
        Edit the current message.

        Args:
            text: New message text
            **kwargs: Additional parameters

        Returns:
            Edited message object
        """
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
        raise ValueError("No message to edit")

    async def delete(self):
        """Delete the current message"""
        if not self.message:
            raise ValueError("No message to delete")

        return await self.bot.api.delete_message(
            chat_id=self.chat.id,
            message_id=self.message.message_id
        )

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

        return await self.bot.api.forward_message(
            chat_id=chat_id,
            from_chat_id=self.chat.id,
            message_id=self.message.message_id
        )

    async def answer_callback(self, text: Optional[str] = None, show_alert: bool = False):
        """
        Answer callback query (for inline keyboard buttons).

        Args:
            text: Notification text
            show_alert: Show alert instead of notification

        Returns:
            True if successful
        """
        if not hasattr(self, 'callback_query'):
            raise ValueError("Not a callback query")

        return await self.bot.api.answer_callback_query(
            callback_query_id=self.callback_query.id,
            text=text,
            show_alert=show_alert
        )

    async def send_photo(self, photo, caption: Optional[str] = None, **kwargs):
        """
        Send a photo to the current chat.

        Args:
            photo: Photo file_id or URL
            caption: Photo caption
            **kwargs: Additional parameters
        """
        return await self.bot.api.send_photo(
            chat_id=self.chat.id,
            photo=photo,
            caption=caption,
            **kwargs
        )

    async def send_document(self, document, caption: Optional[str] = None, **kwargs):
        """
        Send a document to the current chat.

        Args:
            document: Document file_id or URL
            caption: Document caption
            **kwargs: Additional parameters
        """
        return await self.bot.api.send_document(
            chat_id=self.chat.id,
            document=document,
            caption=caption,
            **kwargs
        )

    async def send_video(self, video, caption: Optional[str] = None, **kwargs):
        """Send a video to the current chat"""
        return await self.bot.api.send_video(
            chat_id=self.chat.id,
            video=video,
            caption=caption,
            **kwargs
        )

    # State management methods (requires UserDataMiddleware)
    async def set_state(self, state):
        """Set user state for FSM (Finite State Machine)"""
        if self.user_data:
            await self.user_data.set("state", state)
            self.state = state

    async def get_state(self):
        """Get current user state"""
        if self.user_data:
            self.state = await self.user_data.get("state")
            return self.state
        return None

    async def clear_state(self):
        """Clear user state"""
        if self.user_data:
            await self.user_data.delete("state")
            self.state = None

    async def update_data(self, **kwargs):
        """Update user data"""
        if self.user_data:
            for key, value in kwargs.items():
                await self.user_data.set(key, value)

    async def get_data(self, key: str, default=None):
        """Get user data"""
        if self.user_data:
            return await self.user_data.get(key, default)
        return default
