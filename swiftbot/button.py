"""
SwiftBot - Button and Markup System
Complete keyboard and button support for Telegram Bot API
Copyright (c) 2025 Arjun-M/SwiftBot
"""

from typing import List, Dict, Optional, Any, Union
from dataclasses import dataclass
from enum import Enum


# =====================================================
# INLINE BUTTON CLASS
# =====================================================

@dataclass
class InlineButton:
    """Inline button for inline keyboards"""
    text: str
    callback_data: Optional[str] = None
    url: Optional[str] = None
    web_app: Optional[Dict] = None
    switch_inline_query: Optional[str] = None
    switch_inline_query_current_chat: Optional[str] = None
    login_url: Optional[Dict] = None
    pay: bool = False
    request_user: Optional[Dict] = None
    request_chat: Optional[Dict] = None
    copy_text: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert to Telegram API format"""
        data = {"text": self.text}
        if self.callback_data:
            data["callback_data"] = self.callback_data
        elif self.url:
            data["url"] = self.url
        elif self.web_app:
            data["web_app"] = self.web_app
        elif self.switch_inline_query is not None:
            data["switch_inline_query"] = self.switch_inline_query
        elif self.switch_inline_query_current_chat is not None:
            data["switch_inline_query_current_chat"] = self.switch_inline_query_current_chat
        elif self.login_url:
            data["login_url"] = self.login_url
        elif self.pay:
            data["pay"] = True
        elif self.request_user:
            data["request_user"] = self.request_user
        elif self.request_chat:
            data["request_chat"] = self.request_chat
        elif self.copy_text:
            data["copy_text"] = self.copy_text
        return data


@dataclass
class ReplyButton:
    """Reply button for reply keyboards"""
    text: str
    request_location: bool = False
    request_contact: bool = False
    request_poll: Optional[Dict] = None
    request_user: Optional[Dict] = None
    request_chat: Optional[Dict] = None
    web_app: Optional[Dict] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert to Telegram API format"""
        data = {"text": self.text}
        if self.request_location:
            data["request_location"] = True
        elif self.request_contact:
            data["request_contact"] = True
        elif self.request_poll:
            data["request_poll"] = self.request_poll
        elif self.request_user:
            data["request_user"] = self.request_user
        elif self.request_chat:
            data["request_chat"] = self.request_chat
        elif self.web_app:
            data["web_app"] = self.web_app
        return data


# =====================================================
# KEYBOARD CLASSES
# =====================================================

@dataclass
class InlineKeyboard:
    """Inline keyboard (buttons above message input)"""
    buttons: List[List[InlineButton]]

    def add_row(self, *buttons: InlineButton) -> 'InlineKeyboard':
        """Add a row of buttons"""
        self.buttons.append(list(buttons))
        return self

    def add_button(self, button: InlineButton, row: int = -1) -> 'InlineKeyboard':
        """Add button to specific row"""
        if row == -1:
            if self.buttons:
                self.buttons[-1].append(button)
            else:
                self.buttons.append([button])
        else:
            self.buttons[row].append(button)
        return self

    def to_dict(self) -> Dict[str, Any]:
        """Convert to Telegram API format"""
        return {
            "inline_keyboard": [
                [btn.to_dict() for btn in row]
                for row in self.buttons
            ]
        }


@dataclass
class ReplyKeyboard:
    """Reply keyboard (buttons as keyboard layout)"""
    buttons: List[List[ReplyButton]]
    one_time_keyboard: bool = False
    resize_keyboard: bool = False
    selective: bool = False
    input_field_placeholder: Optional[str] = None

    def add_row(self, *buttons: ReplyButton) -> 'ReplyKeyboard':
        """Add a row of buttons"""
        self.buttons.append(list(buttons))
        return self

    def to_dict(self) -> Dict[str, Any]:
        """Convert to Telegram API format"""
        return {
            "keyboard": [
                [btn.to_dict() for btn in row]
                for row in self.buttons
            ],
            "one_time_keyboard": self.one_time_keyboard,
            "resize_keyboard": self.resize_keyboard,
            "selective": self.selective,
        }


@dataclass
class RemoveKeyboard:
    """Remove keyboard"""
    selective: bool = False

    def to_dict(self) -> Dict[str, Any]:
        """Convert to Telegram API format"""
        return {
            "remove_keyboard": True,
            "selective": self.selective
        }


# =====================================================
# BUTTON BUILDER - Main Class
# =====================================================

class Button:
    """
    Utility class for building buttons - Telethon style for SwiftBot.
    
    Features:
    - Inline buttons with callbacks
    - URL buttons and Web Apps
    - User/Chat request buttons (Bot API 9.0+)
    - Payment buttons
    - Inline query buttons
    - Login buttons
    - Copy text buttons
    - Reply buttons with location/contact
    
    Copyright (c) 2025 Arjun-M/SwiftBot
    """

    # INLINE BUTTONS

    @staticmethod
    def inline(text: str, data: Union[str, bytes]) -> InlineButton:
        """Create inline button with callback data"""
        if isinstance(data, bytes):
            data = data.decode('utf-8')
        return InlineButton(text=text, callback_data=data)

    @staticmethod
    def url(text: str, url: str) -> InlineButton:
        """Create URL button"""
        return InlineButton(text=text, url=url)

    @staticmethod
    def web_app(text: str, url: str) -> InlineButton:
        """Create Web App button (Bot API 6.4+)"""
        return InlineButton(text=text, web_app={"url": url})

    @staticmethod
    def switch_inline(text: str, query: str = "", same_peer: bool = False) -> InlineButton:
        """Create switch inline button"""
        if same_peer:
            return InlineButton(text=text, switch_inline_query_current_chat=query)
        return InlineButton(text=text, switch_inline_query=query)

    @staticmethod
    def login(text: str, url: str, bot_username: Optional[str] = None) -> InlineButton:
        """Create login button (Bot API 5.0+)"""
        login_data = {"url": url}
        if bot_username:
            login_data["bot_username"] = bot_username
        return InlineButton(text=text, login_url=login_data)

    @staticmethod
    def pay(text: str = "💰 Pay") -> InlineButton:
        """Create payment button (Bot API 4.0+)"""
        return InlineButton(text=text, pay=True)

    @staticmethod
    def request_user(text: str, request_id: int) -> InlineButton:
        """Create user request button (Bot API 9.0+)"""
        return InlineButton(text=text, request_user={"request_id": request_id})

    @staticmethod
    def request_chat(text: str, request_id: int) -> InlineButton:
        """Create chat request button (Bot API 9.0+)"""
        return InlineButton(text=text, request_chat={"request_id": request_id})

    @staticmethod
    def copy_text(text: str, copy_text: str) -> InlineButton:
        """Create copy text button (Bot API 7.0+)"""
        return InlineButton(text=text, copy_text=copy_text)

    # REPLY BUTTONS

    @staticmethod
    def text(text: str) -> ReplyButton:
        """Create simple text reply button"""
        return ReplyButton(text=text)

    @staticmethod
    def location(text: str = "📍 Share Location") -> ReplyButton:
        """Create location request button"""
        return ReplyButton(text=text, request_location=True)

    @staticmethod
    def contact(text: str = "👤 Share Contact") -> ReplyButton:
        """Create contact request button"""
        return ReplyButton(text=text, request_contact=True)

    @staticmethod
    def poll(text: str = "🗳 Create Poll", is_quiz: bool = False) -> ReplyButton:
        """Create poll request button (Bot API 5.0+)"""
        poll_type = "quiz" if is_quiz else "regular"
        return ReplyButton(text=text, request_poll={"type": poll_type})

