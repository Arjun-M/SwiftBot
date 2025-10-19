"""
Complete Telegram Update Types with class-based structure
Copyright (c) 2025 Arjun-M/SwiftBot
"""

from typing import Optional, List, Any, Dict
from dataclasses import dataclass
from datetime import datetime


@dataclass
class User:
    """
    Telegram User object.
    Represents a Telegram user or bot.
    """
    id: int
    is_bot: bool
    first_name: str
    last_name: Optional[str] = None
    username: Optional[str] = None
    language_code: Optional[str] = None
    is_premium: Optional[bool] = None
    added_to_attachment_menu: Optional[bool] = None
    can_join_groups: Optional[bool] = None
    can_read_all_group_messages: Optional[bool] = None
    supports_inline_queries: Optional[bool] = None

    @classmethod
    def from_dict(cls, data: Optional[Dict]) -> Optional['User']:
        """Create User from dictionary"""
        if not data:
            return None
        return cls(
            id=data.get('id'),
            is_bot=data.get('is_bot', False),
            first_name=data.get('first_name', ''),
            last_name=data.get('last_name'),
            username=data.get('username'),
            language_code=data.get('language_code'),
            is_premium=data.get('is_premium'),
            added_to_attachment_menu=data.get('added_to_attachment_menu'),
            can_join_groups=data.get('can_join_groups'),
            can_read_all_group_messages=data.get('can_read_all_group_messages'),
            supports_inline_queries=data.get('supports_inline_queries'),
        )


@dataclass
class Chat:
    """
    Telegram Chat object.
    Represents a chat.
    """
    id: int
    type: str  # private, group, supergroup, channel
    title: Optional[str] = None
    username: Optional[str] = None
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    is_forum: Optional[bool] = None
    photo: Optional[Dict] = None
    active_usernames: Optional[List[str]] = None
    emoji_status_custom_emoji_id: Optional[str] = None
    bio: Optional[str] = None
    has_private_forwards: Optional[bool] = None
    has_restricted_voice_and_video_messages: Optional[bool] = None
    join_to_send_messages: Optional[bool] = None
    join_by_request: Optional[bool] = None
    description: Optional[str] = None
    invite_link: Optional[str] = None
    pinned_message: Optional['Message'] = None
    permissions: Optional[Dict] = None
    slow_mode_delay: Optional[int] = None
    message_auto_delete_time: Optional[int] = None
    has_aggressive_anti_spam_enabled: Optional[bool] = None
    has_hidden_members: Optional[bool] = None
    has_protected_content: Optional[bool] = None
    sticker_set_name: Optional[str] = None
    can_set_sticker_set: Optional[bool] = None
    linked_chat_id: Optional[int] = None
    location: Optional[Dict] = None

    @classmethod
    def from_dict(cls, data: Optional[Dict]) -> Optional['Chat']:
        """Create Chat from dictionary"""
        if not data:
            return None
        return cls(
            id=data.get('id'),
            type=data.get('type', 'private'),
            title=data.get('title'),
            username=data.get('username'),
            first_name=data.get('first_name'),
            last_name=data.get('last_name'),
            is_forum=data.get('is_forum'),
            photo=data.get('photo'),
            active_usernames=data.get('active_usernames'),
            emoji_status_custom_emoji_id=data.get('emoji_status_custom_emoji_id'),
            bio=data.get('bio'),
            has_private_forwards=data.get('has_private_forwards'),
            has_restricted_voice_and_video_messages=data.get('has_restricted_voice_and_video_messages'),
            join_to_send_messages=data.get('join_to_send_messages'),
            join_by_request=data.get('join_by_request'),
            description=data.get('description'),
            invite_link=data.get('invite_link'),
            pinned_message=None,  # TODO: Handle recursive Message
            permissions=data.get('permissions'),
            slow_mode_delay=data.get('slow_mode_delay'),
            message_auto_delete_time=data.get('message_auto_delete_time'),
            has_aggressive_anti_spam_enabled=data.get('has_aggressive_anti_spam_enabled'),
            has_hidden_members=data.get('has_hidden_members'),
            has_protected_content=data.get('has_protected_content'),
            sticker_set_name=data.get('sticker_set_name'),
            can_set_sticker_set=data.get('can_set_sticker_set'),
            linked_chat_id=data.get('linked_chat_id'),
            location=data.get('location'),
        )


@dataclass
class Message:
    """
    Telegram Message object.
    Represents a message.
    """
    message_id: int
    date: int
    chat: Chat
    from_user: Optional[User] = None
    sender_chat: Optional[Chat] = None
    forward_from: Optional[User] = None
    forward_from_chat: Optional[Chat] = None
    forward_from_message_id: Optional[int] = None
    forward_signature: Optional[str] = None
    forward_sender_name: Optional[str] = None
    forward_date: Optional[int] = None
    is_topic_message: Optional[bool] = None
    is_automatic_forward: Optional[bool] = None
    reply_to_message: Optional['Message'] = None
    via_bot: Optional[User] = None
    edit_date: Optional[int] = None
    has_protected_content: Optional[bool] = None
    media_group_id: Optional[str] = None
    author_signature: Optional[str] = None
    text: Optional[str] = None
    entities: Optional[List[Dict]] = None
    animation: Optional[Dict] = None
    audio: Optional[Dict] = None
    document: Optional[Dict] = None
    photo: Optional[List[Dict]] = None
    sticker: Optional[Dict] = None
    video: Optional[Dict] = None
    video_note: Optional[Dict] = None
    voice: Optional[Dict] = None
    caption: Optional[str] = None
    caption_entities: Optional[List[Dict]] = None
    has_media_spoiler: Optional[bool] = None
    contact: Optional[Dict] = None
    dice: Optional[Dict] = None
    game: Optional[Dict] = None
    poll: Optional[Dict] = None
    venue: Optional[Dict] = None
    location: Optional[Dict] = None
    new_chat_members: Optional[List[User]] = None
    left_chat_member: Optional[User] = None
    new_chat_title: Optional[str] = None
    new_chat_photo: Optional[List[Dict]] = None
    delete_chat_photo: Optional[bool] = None
    group_chat_created: Optional[bool] = None
    supergroup_chat_created: Optional[bool] = None
    channel_chat_created: Optional[bool] = None
    message_auto_delete_timer_changed: Optional[Dict] = None
    migrate_to_chat_id: Optional[int] = None
    migrate_from_chat_id: Optional[int] = None
    pinned_message: Optional['Message'] = None
    invoice: Optional[Dict] = None
    successful_payment: Optional[Dict] = None
    user_shared: Optional[Dict] = None
    chat_shared: Optional[Dict] = None
    connected_website: Optional[str] = None
    write_access_allowed: Optional[Dict] = None
    passport_data: Optional[Dict] = None
    proximity_alert_triggered: Optional[Dict] = None
    forum_topic_created: Optional[Dict] = None
    forum_topic_edited: Optional[Dict] = None
    forum_topic_closed: Optional[Dict] = None
    forum_topic_reopened: Optional[Dict] = None
    general_forum_topic_hidden: Optional[Dict] = None
    general_forum_topic_unhidden: Optional[Dict] = None
    video_chat_scheduled: Optional[Dict] = None
    video_chat_started: Optional[Dict] = None
    video_chat_ended: Optional[Dict] = None
    video_chat_participants_invited: Optional[Dict] = None
    web_app_data: Optional[Dict] = None
    reply_markup: Optional[Dict] = None

    @classmethod
    def from_dict(cls, data: Optional[Dict]) -> Optional['Message']:
        """Create Message from dictionary"""
        if not data:
            return None

        return cls(
            message_id=data.get('message_id'),
            date=data.get('date'),
            chat=Chat.from_dict(data.get('chat')),
            from_user=User.from_dict(data.get('from')),
            sender_chat=Chat.from_dict(data.get('sender_chat')),
            forward_from=User.from_dict(data.get('forward_from')),
            forward_from_chat=Chat.from_dict(data.get('forward_from_chat')),
            forward_from_message_id=data.get('forward_from_message_id'),
            forward_signature=data.get('forward_signature'),
            forward_sender_name=data.get('forward_sender_name'),
            forward_date=data.get('forward_date'),
            is_topic_message=data.get('is_topic_message'),
            is_automatic_forward=data.get('is_automatic_forward'),
            reply_to_message=cls.from_dict(data.get('reply_to_message')),
            via_bot=User.from_dict(data.get('via_bot')),
            edit_date=data.get('edit_date'),
            has_protected_content=data.get('has_protected_content'),
            media_group_id=data.get('media_group_id'),
            author_signature=data.get('author_signature'),
            text=data.get('text'),
            entities=data.get('entities'),
            animation=data.get('animation'),
            audio=data.get('audio'),
            document=data.get('document'),
            photo=data.get('photo'),
            sticker=data.get('sticker'),
            video=data.get('video'),
            video_note=data.get('video_note'),
            voice=data.get('voice'),
            caption=data.get('caption'),
            caption_entities=data.get('caption_entities'),
            has_media_spoiler=data.get('has_media_spoiler'),
            contact=data.get('contact'),
            dice=data.get('dice'),
            game=data.get('game'),
            poll=data.get('poll'),
            venue=data.get('venue'),
            location=data.get('location'),
            new_chat_members=[User.from_dict(u) for u in data.get('new_chat_members', [])],
            left_chat_member=User.from_dict(data.get('left_chat_member')),
            new_chat_title=data.get('new_chat_title'),
            new_chat_photo=data.get('new_chat_photo'),
            delete_chat_photo=data.get('delete_chat_photo'),
            group_chat_created=data.get('group_chat_created'),
            supergroup_chat_created=data.get('supergroup_chat_created'),
            channel_chat_created=data.get('channel_chat_created'),
            message_auto_delete_timer_changed=data.get('message_auto_delete_timer_changed'),
            migrate_to_chat_id=data.get('migrate_to_chat_id'),
            migrate_from_chat_id=data.get('migrate_from_chat_id'),
            pinned_message=cls.from_dict(data.get('pinned_message')),
            invoice=data.get('invoice'),
            successful_payment=data.get('successful_payment'),
            user_shared=data.get('user_shared'),
            chat_shared=data.get('chat_shared'),
            connected_website=data.get('connected_website'),
            write_access_allowed=data.get('write_access_allowed'),
            passport_data=data.get('passport_data'),
            proximity_alert_triggered=data.get('proximity_alert_triggered'),
            forum_topic_created=data.get('forum_topic_created'),
            forum_topic_edited=data.get('forum_topic_edited'),
            forum_topic_closed=data.get('forum_topic_closed'),
            forum_topic_reopened=data.get('forum_topic_reopened'),
            general_forum_topic_hidden=data.get('general_forum_topic_hidden'),
            general_forum_topic_unhidden=data.get('general_forum_topic_unhidden'),
            video_chat_scheduled=data.get('video_chat_scheduled'),
            video_chat_started=data.get('video_chat_started'),
            video_chat_ended=data.get('video_chat_ended'),
            video_chat_participants_invited=data.get('video_chat_participants_invited'),
            web_app_data=data.get('web_app_data'),
            reply_markup=data.get('reply_markup'),
        )


@dataclass
class CallbackQuery:
    """Telegram CallbackQuery object"""
    id: str
    from_user: User
    chat_instance: str
    message: Optional[Message] = None
    inline_message_id: Optional[str] = None
    data: Optional[str] = None
    game_short_name: Optional[str] = None

    @classmethod
    def from_dict(cls, data: Optional[Dict]) -> Optional['CallbackQuery']:
        """Create CallbackQuery from dictionary"""
        if not data:
            return None
        return cls(
            id=data.get('id'),
            from_user=User.from_dict(data.get('from')),
            chat_instance=data.get('chat_instance', ''),
            message=Message.from_dict(data.get('message')),
            inline_message_id=data.get('inline_message_id'),
            data=data.get('data'),
            game_short_name=data.get('game_short_name'),
        )


@dataclass
class InlineQuery:
    """Telegram InlineQuery object"""
    id: str
    from_user: User
    query: str
    offset: str
    chat_type: Optional[str] = None
    location: Optional[Dict] = None

    @classmethod
    def from_dict(cls, data: Optional[Dict]) -> Optional['InlineQuery']:
        """Create InlineQuery from dictionary"""
        if not data:
            return None
        return cls(
            id=data.get('id'),
            from_user=User.from_dict(data.get('from')),
            query=data.get('query', ''),
            offset=data.get('offset', ''),
            chat_type=data.get('chat_type'),
            location=data.get('location'),
        )


@dataclass
class ChosenInlineResult:
    """Telegram ChosenInlineResult object"""
    result_id: str
    from_user: User
    query: str
    location: Optional[Dict] = None
    inline_message_id: Optional[str] = None

    @classmethod
    def from_dict(cls, data: Optional[Dict]) -> Optional['ChosenInlineResult']:
        """Create ChosenInlineResult from dictionary"""
        if not data:
            return None
        return cls(
            result_id=data.get('result_id'),
            from_user=User.from_dict(data.get('from')),
            query=data.get('query', ''),
            location=data.get('location'),
            inline_message_id=data.get('inline_message_id'),
        )


@dataclass
class ShippingQuery:
    """Telegram ShippingQuery object"""
    id: str
    from_user: User
    invoice_payload: str
    shipping_address: Dict

    @classmethod
    def from_dict(cls, data: Optional[Dict]) -> Optional['ShippingQuery']:
        """Create ShippingQuery from dictionary"""
        if not data:
            return None
        return cls(
            id=data.get('id'),
            from_user=User.from_dict(data.get('from')),
            invoice_payload=data.get('invoice_payload', ''),
            shipping_address=data.get('shipping_address', {}),
        )


@dataclass
class PreCheckoutQuery:
    """Telegram PreCheckoutQuery object"""
    id: str
    from_user: User
    currency: str
    total_amount: int
    invoice_payload: str
    shipping_option_id: Optional[str] = None
    order_info: Optional[Dict] = None

    @classmethod
    def from_dict(cls, data: Optional[Dict]) -> Optional['PreCheckoutQuery']:
        """Create PreCheckoutQuery from dictionary"""
        if not data:
            return None
        return cls(
            id=data.get('id'),
            from_user=User.from_dict(data.get('from')),
            currency=data.get('currency', ''),
            total_amount=data.get('total_amount', 0),
            invoice_payload=data.get('invoice_payload', ''),
            shipping_option_id=data.get('shipping_option_id'),
            order_info=data.get('order_info'),
        )


@dataclass
class Poll:
    """Telegram Poll object"""
    id: str
    question: str
    options: List[Dict]
    total_voter_count: int
    is_closed: bool
    is_anonymous: bool
    type: str
    allows_multiple_answers: bool
    correct_option_id: Optional[int] = None
    explanation: Optional[str] = None
    explanation_entities: Optional[List[Dict]] = None
    open_period: Optional[int] = None
    close_date: Optional[int] = None

    @classmethod
    def from_dict(cls, data: Optional[Dict]) -> Optional['Poll']:
        """Create Poll from dictionary"""
        if not data:
            return None
        return cls(
            id=data.get('id'),
            question=data.get('question', ''),
            options=data.get('options', []),
            total_voter_count=data.get('total_voter_count', 0),
            is_closed=data.get('is_closed', False),
            is_anonymous=data.get('is_anonymous', True),
            type=data.get('type', 'regular'),
            allows_multiple_answers=data.get('allows_multiple_answers', False),
            correct_option_id=data.get('correct_option_id'),
            explanation=data.get('explanation'),
            explanation_entities=data.get('explanation_entities'),
            open_period=data.get('open_period'),
            close_date=data.get('close_date'),
        )


@dataclass
class PollAnswer:
    """Telegram PollAnswer object"""
    poll_id: str
    user: User
    option_ids: List[int]

    @classmethod
    def from_dict(cls, data: Optional[Dict]) -> Optional['PollAnswer']:
        """Create PollAnswer from dictionary"""
        if not data:
            return None
        return cls(
            poll_id=data.get('poll_id'),
            user=User.from_dict(data.get('user')),
            option_ids=data.get('option_ids', []),
        )


@dataclass
class ChatMemberUpdated:
    """Telegram ChatMemberUpdated object"""
    chat: Chat
    from_user: User
    date: int
    old_chat_member: Dict
    new_chat_member: Dict
    invite_link: Optional[Dict] = None
    via_chat_folder_invite_link: Optional[bool] = None

    @classmethod
    def from_dict(cls, data: Optional[Dict]) -> Optional['ChatMemberUpdated']:
        """Create ChatMemberUpdated from dictionary"""
        if not data:
            return None
        return cls(
            chat=Chat.from_dict(data.get('chat')),
            from_user=User.from_dict(data.get('from')),
            date=data.get('date', 0),
            old_chat_member=data.get('old_chat_member', {}),
            new_chat_member=data.get('new_chat_member', {}),
            invite_link=data.get('invite_link'),
            via_chat_folder_invite_link=data.get('via_chat_folder_invite_link'),
        )


@dataclass
class ChatJoinRequest:
    """Telegram ChatJoinRequest object"""
    chat: Chat
    from_user: User
    user_chat_id: int
    date: int
    bio: Optional[str] = None
    invite_link: Optional[Dict] = None

    @classmethod
    def from_dict(cls, data: Optional[Dict]) -> Optional['ChatJoinRequest']:
        """Create ChatJoinRequest from dictionary"""
        if not data:
            return None
        return cls(
            chat=Chat.from_dict(data.get('chat')),
            from_user=User.from_dict(data.get('from')),
            user_chat_id=data.get('user_chat_id', 0),
            date=data.get('date', 0),
            bio=data.get('bio'),
            invite_link=data.get('invite_link'),
        )


@dataclass
class Update:
    """
    Complete Telegram Update object.

    Contains all possible update types and provides:
    - Structured access to update data
    - Raw JSON access via .raw
    - Type detection
    """
    update_id: int
    message: Optional[Message] = None
    edited_message: Optional[Message] = None
    channel_post: Optional[Message] = None
    edited_channel_post: Optional[Message] = None
    inline_query: Optional[InlineQuery] = None
    chosen_inline_result: Optional[ChosenInlineResult] = None
    callback_query: Optional[CallbackQuery] = None
    shipping_query: Optional[ShippingQuery] = None
    pre_checkout_query: Optional[PreCheckoutQuery] = None
    poll: Optional[Poll] = None
    poll_answer: Optional[PollAnswer] = None
    my_chat_member: Optional[ChatMemberUpdated] = None
    chat_member: Optional[ChatMemberUpdated] = None
    chat_join_request: Optional[ChatJoinRequest] = None

    # Raw JSON data
    raw: Optional[Dict] = None

    @classmethod
    def from_dict(cls, data: Dict) -> 'Update':
        """
        Create Update from dictionary.
        Parses all update types and stores raw data.
        """
        return cls(
            update_id=data.get('update_id', 0),
            message=Message.from_dict(data.get('message')),
            edited_message=Message.from_dict(data.get('edited_message')),
            channel_post=Message.from_dict(data.get('channel_post')),
            edited_channel_post=Message.from_dict(data.get('edited_channel_post')),
            inline_query=InlineQuery.from_dict(data.get('inline_query')),
            chosen_inline_result=ChosenInlineResult.from_dict(data.get('chosen_inline_result')),
            callback_query=CallbackQuery.from_dict(data.get('callback_query')),
            shipping_query=ShippingQuery.from_dict(data.get('shipping_query')),
            pre_checkout_query=PreCheckoutQuery.from_dict(data.get('pre_checkout_query')),
            poll=Poll.from_dict(data.get('poll')),
            poll_answer=PollAnswer.from_dict(data.get('poll_answer')),
            my_chat_member=ChatMemberUpdated.from_dict(data.get('my_chat_member')),
            chat_member=ChatMemberUpdated.from_dict(data.get('chat_member')),
            chat_join_request=ChatJoinRequest.from_dict(data.get('chat_join_request')),
            raw=data,  # Store raw JSON
        )

    def get_update_type(self) -> Optional[str]:
        """Get the type of this update"""
        if self.message:
            return 'message'
        elif self.edited_message:
            return 'edited_message'
        elif self.channel_post:
            return 'channel_post'
        elif self.edited_channel_post:
            return 'edited_channel_post'
        elif self.inline_query:
            return 'inline_query'
        elif self.chosen_inline_result:
            return 'chosen_inline_result'
        elif self.callback_query:
            return 'callback_query'
        elif self.shipping_query:
            return 'shipping_query'
        elif self.pre_checkout_query:
            return 'pre_checkout_query'
        elif self.poll:
            return 'poll'
        elif self.poll_answer:
            return 'poll_answer'
        elif self.my_chat_member:
            return 'my_chat_member'
        elif self.chat_member:
            return 'chat_member'
        elif self.chat_join_request:
            return 'chat_join_request'
        return None

    def get_update_object(self):
        """Get the actual update object (message, callback_query, etc.)"""
        update_type = self.get_update_type()
        if update_type:
            return getattr(self, update_type)
        return None
