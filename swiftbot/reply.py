"""
Reply — a fluent builder for sending messages through a ``Context``.

Instead of remembering long keyword-argument lists, chain the options you
want and finish with ``send()``:

    await Reply(ctx).text("Hello").silent().protect().send()
    await Reply(ctx).photo(file).caption("Look at this").markup(kb).send()

Builds on the existing ``ctx.reply(...)``, ``ctx.answer(...)`` and the Bot API
``send_*`` methods on the context.

Copyright (c) 2026 Arjun-M/SwiftBot
"""

import logging
from typing import Any, Dict, Optional

logger = logging.getLogger(__name__)


class Reply:
    """
    Fluent reply builder. All option methods return ``self``; ``send()``
    transmits the message and returns the API result.
    """

    def __init__(self, ctx: Any) -> None:
        self._ctx = ctx
        self._kind: Optional[str] = None      # text, photo, etc.
        self._content: Optional[Any] = None   # text body / file
        self._caption: Optional[str] = None
        self._markup: Optional[Any] = None
        self._reply_to: Optional[int] = None
        self._silent: bool = False
        self._protected: bool = False
        self._parse_mode: Optional[str] = None
        self._extra: Dict[str, Any] = {}

    # ------------------------------------------------------------------
    # Content
    # ------------------------------------------------------------------

    def text(self, message: str) -> "Reply":
        self._kind = "text"
        self._content = message
        return self

    def answer(self, message: str) -> "Reply":
        """Same as ``text`` — reads naturally for callback answers."""
        return self.text(message)

    def photo(self, file: Any) -> "Reply":
        self._kind = "photo"
        self._content = file
        return self

    def document(self, file: Any) -> "Reply":
        self._kind = "document"
        self._content = file
        return self

    def voice(self, file: Any) -> "Reply":
        self._kind = "voice"
        self._content = file
        return self

    def caption(self, text: str) -> "Reply":
        self._caption = text
        return self

    # ------------------------------------------------------------------
    # Options
    # ------------------------------------------------------------------

    def markup(self, keyboard: Any) -> "Reply":
        """Attach an inline or reply keyboard."""
        self._markup = keyboard
        return self

    def silent(self, notify: bool = True) -> "Reply":
        """Disable the notification sound."""
        self._silent = notify
        return self

    def protect(self, protected: bool = True) -> "Reply":
        """Enable content protection (no forwarding/saving)."""
        self._protected = protected
        return self

    def reply_to(self, message_id: int) -> "Reply":
        self._reply_to = message_id
        return self

    def parse_mode(self, mode: str) -> "Reply":
        self._parse_mode = mode
        return self

    def option(self, key: str, value: Any) -> "Reply":
        """Pass any raw Bot API parameter."""
        self._extra[key] = value
        return self

    # ------------------------------------------------------------------
    # Send
    # ------------------------------------------------------------------

    async def send(self) -> Any:
        """Transmit the built message via the context."""
        ctx = self._ctx
        method = self._kind or "text"
        kwargs: Dict[str, Any] = dict(self._extra)

        if self._reply_to:
            # telegram.py send_* methods accept the Bot API 2026
            # ``reply_parameters`` dict (``reply_to_message_id`` is nested).
            kwargs["reply_parameters"] = {"message_id": self._reply_to}
        if self._silent:
            kwargs["disable_notification"] = True
        if self._protected:
            kwargs["protect_content"] = True
        if self._parse_mode:
            kwargs["parse_mode"] = self._parse_mode
        if self._markup is not None:
            if hasattr(self._markup, "to_dict"):
                kwargs["reply_markup"] = self._markup.to_dict()
            else:
                kwargs["reply_markup"] = self._markup
        if self._caption is not None:
            kwargs["caption"] = self._caption

        chat_id = self._resolve_chat_id(ctx)

        if method == "text":
            result = await ctx.reply(self._content, **kwargs)
        elif method == "photo":
            result = await ctx.bot.api.send_photo(chat_id, self._content, **kwargs)
        elif method == "document":
            result = await ctx.bot.api.send_document(chat_id, self._content, **kwargs)
        elif method == "voice":
            result = await ctx.bot.api.send_voice(chat_id, self._content, **kwargs)
        else:
            result = await ctx.reply(self._content, **kwargs)
        return result

    @staticmethod
    def _resolve_chat_id(ctx: Any) -> Optional[int]:
        chat = getattr(ctx, "chat", None)
        if chat is None:
            return None
        if isinstance(chat, dict):
            return chat.get("id")
        return getattr(chat, "id", None)

    def __repr__(self) -> str:
        return f"Reply(kind={self._kind!r}, chat={self._resolve_chat_id(self._ctx)})"
