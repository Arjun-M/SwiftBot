"""
SwiftBot - Typed Bot API models (v1.3)

Dataclass models for the most-used Telegram Bot API types, with
``from_dict``/``to_dict`` that tolerate unknown and missing fields so they
keep working across Bot API versions.

Usage:
    from swiftbot.models import Message, User, Chat

    msg = Message.from_dict(update["message"])
    print(msg.from_user.first_name, "->", msg.text)

Only the fields a typical bot actually reads are modelled here; everything
else remains accessible through ``msg.raw``. This mirrors how PTB and
Extend as the API grows — prefer completeness over churn.

Copyright (c) 2026 Arjun-M/SwiftBot
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Sequence


def _safe_get(data: Dict, *keys, default=None):
    """Traverse nested dicts without KeyError/AttributeError."""
    cur: Any = data
    for k in keys:
        if not isinstance(cur, dict):
            return default
        cur = cur.get(k, default)
        if cur is None:
            return default
    return cur


@dataclass
class User:
    """Telegram user or bot (https://core.telegram.org/bots/api#user)"""
    id: int = 0
    is_bot: bool = False
    first_name: str = ""
    last_name: Optional[str] = None
    username: Optional[str] = None
    language_code: Optional[str] = None
    is_premium: bool = False
    added_to_attachment_menu: bool = False
    raw: Dict = field(default_factory=dict, repr=False)

    @classmethod
    def from_dict(cls, data: Optional[Dict[str, Any]]) -> Optional[User]:
        """Build a ``User`` from a raw API dict; returns ``None`` for missing
        input so call sites can chain ``.from_dict(data.get("from"))`` safely."""
        if not isinstance(data, dict):
            return None
        return cls(
            id=data.get("id", 0),
            is_bot=bool(data.get("is_bot", False)),
            first_name=data.get("first_name", ""),
            last_name=data.get("last_name"),
            username=data.get("username"),
            language_code=data.get("language_code"),
            is_premium=bool(data.get("is_premium", False)),
            added_to_attachment_menu=bool(data.get("added_to_attachment_menu", False)),
            raw=data,
        )


@dataclass
class Chat:
    """Chat info (https://core.telegram.org/bots/api#chat)"""
    id: int = 0
    type: str = ""
    title: Optional[str] = None
    username: Optional[str] = None
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    raw: Dict = field(default_factory=dict, repr=False)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> Chat:
        if not isinstance(data, dict):
            return cls()
        return cls(
            id=data.get("id", 0),
            type=data.get("type", ""),
            title=data.get("title"),
            username=data.get("username"),
            first_name=data.get("first_name"),
            last_name=data.get("last_name"),
            raw=data,
        )

    @property
    def is_private(self) -> bool:
        return self.type == "private"

    @property
    def is_group(self) -> bool:
        return self.type == "group"

    @property
    def is_supergroup(self) -> bool:
        return self.type == "supergroup"

    @property
    def is_channel(self) -> bool:
        return self.type == "channel"

    @property
    def user(self) -> Optional[User]:
        """For group chats created by a user the payload may contain a top-level
        ``user`` field; expose it as a typed attribute (often ``None``)."""
        return User.from_dict(self.raw.get("user")) if "user" in self.raw else None


@dataclass
class MessageEntity:
    """Message entity (link, bold, mention, ...)"""
    type: str = ""
    offset: int = 0
    length: int = 0
    url: Optional[str] = None
    user: Optional[User] = None
    raw: Dict = field(default_factory=dict, repr=False)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> MessageEntity:
        if not isinstance(data, dict):
            return cls()
        return cls(
            type=data.get("type", ""),
            offset=data.get("offset", 0),
            length=data.get("length", 0),
            url=data.get("url"),
            user=User.from_dict(data["user"]) if "user" in data else None,
            raw=data,
        )


@dataclass
class PhotoSize:
    id: str = ""
    width: int = 0
    height: int = 0
    file_size: Optional[int] = None
    file_id: Optional[str] = None

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> PhotoSize:
        if not isinstance(data, dict):
            return cls()
        return cls(
            id=data.get("file_id", ""),
            width=data.get("width", 0),
            height=data.get("height", 0),
            file_size=data.get("file_size"),
            file_id=data.get("file_id"),
        )


@dataclass
class Document:
    file_id: str = ""
    file_unique_id: str = ""
    file_name: Optional[str] = None
    mime_type: Optional[str] = None
    file_size: Optional[int] = None
    thumbnail: Optional[PhotoSize] = None

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> Document:
        if not isinstance(data, dict):
            return cls()
        return cls(
            file_id=data.get("file_id", ""),
            file_unique_id=data.get("file_unique_id", ""),
            file_name=data.get("file_name"),
            mime_type=data.get("mime_type"),
            file_size=data.get("file_size"),
            thumbnail=PhotoSize.from_dict(data["thumbnail"]) if "thumbnail" in data else None,
        )


@dataclass
class Message:
    """
    Telegram Message (https://core.telegram.org/bots/api#message).

    Covers the fields bots actually touch. ``raw`` always holds the full
    payload, so future API additions never break you.
    """
    message_id: int = 0
    date: int = 0
    chat: Chat = field(default_factory=Chat)
    from_user: User = field(default_factory=User)
    text: Optional[str] = None
    caption: Optional[str] = None
    entities: List[MessageEntity] = field(default_factory=list)
    reply_to_message: Optional[Message] = None
    new_chat_members: List[User] = field(default_factory=list)
    left_chat_member: Optional[User] = None
    photo: List[PhotoSize] = field(default_factory=list)
    document: Optional[Document] = None
    sticker: Optional[Dict] = None
    poll: Optional[Dict] = None
    business_connection_id: Optional[str] = None
    message_thread_id: Optional[int] = None
    rich_message: Optional[Dict] = None
    live_photo: Optional[Dict] = None
    ephemeral_message_id: Optional[int] = None
    receiver_user: Optional[User] = None
    guest_query_id: Optional[str] = None
    paid_media: Optional[Dict] = None
    checklist: Optional[Dict] = None
    suggested_post_info: Optional[Dict] = None
    raw: Dict = field(default_factory=dict, repr=False)

    @classmethod
    def from_dict(cls, data: Dict[str, Any], depth: int = 0) -> Message:
        if not isinstance(data, dict):
            return cls()
        if depth > 8:
            return cls(message_id=data.get("message_id", 0),
                       date=data.get("date", 0), raw=data)
        return cls(
            message_id=data.get("message_id", 0),
            date=data.get("date", 0),
            chat=Chat.from_dict(data.get("chat", {})),
            from_user=User.from_dict(data.get("from", {})),
            text=data.get("text"),
            caption=data.get("caption"),
            entities=[MessageEntity.from_dict(e) for e in data.get("entities", [])],
            reply_to_message=Message.from_dict(data["reply_to_message"], depth + 1)
            if "reply_to_message" in data else None,
            new_chat_members=[User.from_dict(m) for m in data.get("new_chat_members", [])],
            left_chat_member=User.from_dict(data["left_chat_member"])
            if "left_chat_member" in data else None,
            photo=[PhotoSize.from_dict(p) for p in data.get("photo", [])],
            document=Document.from_dict(data["document"]) if "document" in data else None,
            sticker=data.get("sticker"),
            poll=data.get("poll"),
            business_connection_id=data.get("business_connection_id"),
            message_thread_id=data.get("message_thread_id"),
            rich_message=data.get("rich_message"),
            live_photo=data.get("live_photo"),
            ephemeral_message_id=data.get("ephemeral_message_id"),
            receiver_user=User.from_dict(data.get("receiver_user")),
            guest_query_id=data.get("guest_query_id"),
            paid_media=data.get("paid_media"),
            checklist=data.get("checklist"),
            suggested_post_info=data.get("suggested_post_info"),
            raw=data,
        )


@dataclass
class CallbackQuery:
    id: str = ""
    from_user: User = field(default_factory=User)
    message: Optional[Message] = None
    data: Optional[str] = None
    chat_instance: Optional[str] = None
    raw: Dict = field(default_factory=dict, repr=False)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> CallbackQuery:
        if not isinstance(data, dict):
            return cls()
        return cls(
            id=data.get("id", ""),
            from_user=User.from_dict(data.get("from", {})),
            message=Message.from_dict(data["message"]) if "message" in data else None,
            data=data.get("data"),
            chat_instance=data.get("chat_instance"),
            raw=data,
        )


@dataclass
class InlineKeyboardMarkup:
    """Typed inline keyboard. Interoperates with ``button.InlineKeyboard``."""
    inline_keyboard: List[List[Dict[str, Any]]] = field(default_factory=list)
    is_personal: bool = False

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> InlineKeyboardMarkup:
        if not isinstance(data, dict):
            return cls()
        return cls(
            inline_keyboard=data.get("inline_keyboard", []),
            is_personal=bool(data.get("is_personal", False)),
        )

    def to_dict(self) -> Dict[str, Any]:
        data: Dict[str, Any] = {"inline_keyboard": self.inline_keyboard}
        if self.is_personal:
            data["is_personal"] = True
        return data


@dataclass
class RichText:
    """Generic typed rich-text node accepted by Bot API Rich Messages."""
    type: str = "text"
    text: Optional[str] = None
    fields: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        result = dict(self.fields)
        result["type"] = self.type
        if self.text is not None:
            result["text"] = self.text
        return result

    @classmethod
    def from_dict(cls, data: Optional[Dict[str, Any]]) -> Optional["RichText"]:
        if not isinstance(data, dict):
            return None
        fields = dict(data)
        node_type = fields.pop("type", "text")
        text = fields.pop("text", None)
        return cls(type=node_type, text=text, fields=fields)


@dataclass
class RichBlock:
    """Generic typed rich-message block with forward-compatible fields."""
    type: str = "paragraph"
    fields: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        result = dict(self.fields)
        result["type"] = self.type
        return result

    @classmethod
    def from_dict(cls, data: Optional[Dict[str, Any]]) -> Optional["RichBlock"]:
        if not isinstance(data, dict):
            return None
        fields = dict(data)
        node_type = fields.pop("type", "paragraph")
        return cls(type=node_type, fields=fields)


@dataclass
class RichMessage:
    """Typed, forward-compatible representation of an outgoing Rich Message."""
    text: Optional[RichText] = None
    blocks: List[RichBlock] = field(default_factory=list)
    media: Optional[Dict[str, Any]] = None
    fields: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        result = dict(self.fields)
        if self.text is not None:
            result["text"] = self.text.to_dict() if hasattr(self.text, "to_dict") else self.text
        if self.blocks:
            result["blocks"] = [
                block.to_dict() if hasattr(block, "to_dict") else block
                for block in self.blocks
            ]
        if self.media is not None:
            result["media"] = self.media
        return result

    @classmethod
    def from_dict(cls, data: Optional[Dict[str, Any]]) -> Optional["RichMessage"]:
        if not isinstance(data, dict):
            return None
        fields = dict(data)
        text_data = fields.pop("text", None)
        blocks_data = fields.pop("blocks", [])
        media = fields.pop("media", None)
        text = RichText.from_dict(text_data) if isinstance(text_data, dict) else text_data
        blocks = [RichBlock.from_dict(item) for item in blocks_data if isinstance(item, dict)]
        return cls(text=text, blocks=blocks, media=media, fields=fields)
