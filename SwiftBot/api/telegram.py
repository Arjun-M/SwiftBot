"""
Complete Telegram Bot API wrapper - Part 1: Core & Messaging
Copyright (c) 2025 Arjun-M/SwiftBot

Complete implementation of Telegram Bot API 7.0+
Reference: https://core.telegram.org/bots/api
"""

from typing import Optional, List, Union, Any, Dict
import json


class TelegramAPI:
    """
    Complete Telegram Bot API implementation with ALL methods.

    Covers:
    - Getting Updates
    - Sending Messages (text, media, files)
    - Editing & Deleting
    - Inline Mode
    - Callback Queries
    - Chat Management
    - User Management
    - Stickers
    - Payments
    - Games
    - Forum Topics
    - And more...

    Copyright (c) 2025 Arjun-M/SwiftBot
    """

    def __init__(self, token: str, connection_pool, base_url: str = "https://api.telegram.org"):
        """
        Initialize Telegram API wrapper.

        Args:
            token: Bot token from @BotFather
            connection_pool: HTTP connection pool
            base_url: API base URL
        """
        self.token = token
        self.pool = connection_pool
        self.base_url = f"{base_url}/bot{token}"

    async def _request(self, method: str, **params) -> Any:
        """
        Make API request with automatic error handling.

        Args:
            method: API method name
            **params: Method parameters

        Returns:
            API response result

        Raises:
            Exception: If API returns error
        """
        url = f"{self.base_url}/{method}"

        # Remove None values
        params = {k: v for k, v in params.items() if v is not None}

        # Convert objects to JSON
        for key, value in params.items():
            if isinstance(value, (dict, list)):
                params[key] = json.dumps(value)

        response = await self.pool.post(url, json=params)
        data = response.json()

        if not data.get('ok'):
            error_code = data.get('error_code', 'unknown')
            description = data.get('description', 'No description')
            raise Exception(f"Telegram API error {error_code}: {description}")

        return data.get('result')

    # ==========================================
    # Getting Updates
    # ==========================================

    async def get_updates(
        self,
        offset: Optional[int] = None,
        limit: int = 100,
        timeout: int = 30,
        allowed_updates: Optional[List[str]] = None,
    ):
        """
        Get incoming updates using long polling.

        Args:
            offset: Identifier of the first update to be returned
            limit: Limits the number of updates (1-100, default 100)
            timeout: Timeout in seconds for long polling (default 30)
            allowed_updates: List of update types to receive

        Returns:
            Array of Update objects
        """
        return await self._request(
            "getUpdates",
            offset=offset,
            limit=limit,
            timeout=timeout,
            allowed_updates=allowed_updates,
        )

    async def set_webhook(
        self,
        url: str,
        certificate: Optional[Any] = None,
        ip_address: Optional[str] = None,
        max_connections: int = 40,
        allowed_updates: Optional[List[str]] = None,
        drop_pending_updates: bool = False,
        secret_token: Optional[str] = None,
    ):
        """
        Set webhook to receive updates.

        Args:
            url: HTTPS URL to send updates to
            certificate: Upload your public key certificate
            ip_address: Fixed IP address for webhook
            max_connections: Maximum allowed simultaneous connections (1-100)
            allowed_updates: List of update types to receive
            drop_pending_updates: Pass True to drop all pending updates
            secret_token: Secret token for webhook verification

        Returns:
            True on success
        """
        return await self._request(
            "setWebhook",
            url=url,
            certificate=certificate,
            ip_address=ip_address,
            max_connections=max_connections,
            allowed_updates=allowed_updates,
            drop_pending_updates=drop_pending_updates,
            secret_token=secret_token,
        )

    async def delete_webhook(self, drop_pending_updates: bool = False):
        """
        Remove webhook integration.

        Args:
            drop_pending_updates: Pass True to drop all pending updates

        Returns:
            True on success
        """
        return await self._request(
            "deleteWebhook",
            drop_pending_updates=drop_pending_updates,
        )

    async def get_webhook_info(self):
        """
        Get current webhook status.

        Returns:
            WebhookInfo object
        """
        return await self._request("getWebhookInfo")

    # ==========================================
    # Available Methods - Basic
    # ==========================================

    async def get_me(self):
        """
        Get basic information about the bot.

        Returns:
            User object
        """
        return await self._request("getMe")

    async def log_out(self):
        """
        Log out from the cloud Bot API server.

        Returns:
            True on success
        """
        return await self._request("logOut")

    async def close(self):
        """
        Close the bot instance before moving it to another server.

        Returns:
            True on success
        """
        return await self._request("close")

    # ==========================================
    # Sending Messages
    # ==========================================

    async def send_message(
        self,
        chat_id: Union[int, str],
        text: str,
        parse_mode: Optional[str] = None,
        entities: Optional[List[Dict]] = None,
        link_preview_options: Optional[Dict] = None,
        disable_notification: Optional[bool] = None,
        protect_content: Optional[bool] = None,
        reply_parameters: Optional[Dict] = None,
        reply_markup: Optional[Dict] = None,
        message_thread_id: Optional[int] = None,
        business_connection_id: Optional[str] = None,
    ):
        """
        Send text message.

        Args:
            chat_id: Target chat ID or username
            text: Message text (1-4096 characters)
            parse_mode: Parse mode (HTML, Markdown, MarkdownV2)
            entities: List of MessageEntity objects
            link_preview_options: Link preview generation options
            disable_notification: Send message silently
            protect_content: Protect content from forwarding
            reply_parameters: Description of the message to reply to
            reply_markup: Additional interface options
            message_thread_id: Forum topic ID
            business_connection_id: Business connection identifier

        Returns:
            Sent Message object
        """
        return await self._request(
            "sendMessage",
            chat_id=chat_id,
            text=text,
            parse_mode=parse_mode,
            entities=entities,
            link_preview_options=link_preview_options,
            disable_notification=disable_notification,
            protect_content=protect_content,
            reply_parameters=reply_parameters,
            reply_markup=reply_markup,
            message_thread_id=message_thread_id,
            business_connection_id=business_connection_id,
        )

    async def forward_message(
        self,
        chat_id: Union[int, str],
        from_chat_id: Union[int, str],
        message_id: int,
        disable_notification: Optional[bool] = None,
        protect_content: Optional[bool] = None,
        message_thread_id: Optional[int] = None,
    ):
        """
        Forward message from one chat to another.

        Returns:
            Sent Message object
        """
        return await self._request(
            "forwardMessage",
            chat_id=chat_id,
            from_chat_id=from_chat_id,
            message_id=message_id,
            disable_notification=disable_notification,
            protect_content=protect_content,
            message_thread_id=message_thread_id,
        )

    async def forward_messages(
        self,
        chat_id: Union[int, str],
        from_chat_id: Union[int, str],
        message_ids: List[int],
        disable_notification: Optional[bool] = None,
        protect_content: Optional[bool] = None,
        message_thread_id: Optional[int] = None,
    ):
        """
        Forward multiple messages at once.

        Returns:
            Array of MessageId objects
        """
        return await self._request(
            "forwardMessages",
            chat_id=chat_id,
            from_chat_id=from_chat_id,
            message_ids=message_ids,
            disable_notification=disable_notification,
            protect_content=protect_content,
            message_thread_id=message_thread_id,
        )

    async def copy_message(
        self,
        chat_id: Union[int, str],
        from_chat_id: Union[int, str],
        message_id: int,
        caption: Optional[str] = None,
        parse_mode: Optional[str] = None,
        caption_entities: Optional[List[Dict]] = None,
        disable_notification: Optional[bool] = None,
        protect_content: Optional[bool] = None,
        reply_parameters: Optional[Dict] = None,
        reply_markup: Optional[Dict] = None,
        message_thread_id: Optional[int] = None,
    ):
        """
        Copy message to another chat.

        Returns:
            MessageId object
        """
        return await self._request(
            "copyMessage",
            chat_id=chat_id,
            from_chat_id=from_chat_id,
            message_id=message_id,
            caption=caption,
            parse_mode=parse_mode,
            caption_entities=caption_entities,
            disable_notification=disable_notification,
            protect_content=protect_content,
            reply_parameters=reply_parameters,
            reply_markup=reply_markup,
            message_thread_id=message_thread_id,
        )

    async def copy_messages(
        self,
        chat_id: Union[int, str],
        from_chat_id: Union[int, str],
        message_ids: List[int],
        disable_notification: Optional[bool] = None,
        protect_content: Optional[bool] = None,
        remove_caption: Optional[bool] = None,
        message_thread_id: Optional[int] = None,
    ):
        """
        Copy multiple messages at once.

        Returns:
            Array of MessageId objects
        """
        return await self._request(
            "copyMessages",
            chat_id=chat_id,
            from_chat_id=from_chat_id,
            message_ids=message_ids,
            disable_notification=disable_notification,
            protect_content=protect_content,
            remove_caption=remove_caption,
            message_thread_id=message_thread_id,
        )

    # ==========================================
    # Sending Media
    # ==========================================

    async def send_photo(
        self,
        chat_id: Union[int, str],
        photo: Union[str, Any],
        caption: Optional[str] = None,
        parse_mode: Optional[str] = None,
        caption_entities: Optional[List[Dict]] = None,
        has_spoiler: Optional[bool] = None,
        disable_notification: Optional[bool] = None,
        protect_content: Optional[bool] = None,
        reply_parameters: Optional[Dict] = None,
        reply_markup: Optional[Dict] = None,
        message_thread_id: Optional[int] = None,
        business_connection_id: Optional[str] = None,
    ):
        """Send photo"""
        return await self._request(
            "sendPhoto",
            chat_id=chat_id,
            photo=photo,
            caption=caption,
            parse_mode=parse_mode,
            caption_entities=caption_entities,
            has_spoiler=has_spoiler,
            disable_notification=disable_notification,
            protect_content=protect_content,
            reply_parameters=reply_parameters,
            reply_markup=reply_markup,
            message_thread_id=message_thread_id,
            business_connection_id=business_connection_id,
        )

    async def send_audio(
        self,
        chat_id: Union[int, str],
        audio: Union[str, Any],
        caption: Optional[str] = None,
        parse_mode: Optional[str] = None,
        caption_entities: Optional[List[Dict]] = None,
        duration: Optional[int] = None,
        performer: Optional[str] = None,
        title: Optional[str] = None,
        thumbnail: Optional[Any] = None,
        disable_notification: Optional[bool] = None,
        protect_content: Optional[bool] = None,
        reply_parameters: Optional[Dict] = None,
        reply_markup: Optional[Dict] = None,
        message_thread_id: Optional[int] = None,
        business_connection_id: Optional[str] = None,
    ):
        """Send audio file"""
        return await self._request(
            "sendAudio",
            chat_id=chat_id,
            audio=audio,
            caption=caption,
            parse_mode=parse_mode,
            caption_entities=caption_entities,
            duration=duration,
            performer=performer,
            title=title,
            thumbnail=thumbnail,
            disable_notification=disable_notification,
            protect_content=protect_content,
            reply_parameters=reply_parameters,
            reply_markup=reply_markup,
            message_thread_id=message_thread_id,
            business_connection_id=business_connection_id,
        )

    async def send_document(
        self,
        chat_id: Union[int, str],
        document: Union[str, Any],
        thumbnail: Optional[Any] = None,
        caption: Optional[str] = None,
        parse_mode: Optional[str] = None,
        caption_entities: Optional[List[Dict]] = None,
        disable_content_type_detection: Optional[bool] = None,
        disable_notification: Optional[bool] = None,
        protect_content: Optional[bool] = None,
        reply_parameters: Optional[Dict] = None,
        reply_markup: Optional[Dict] = None,
        message_thread_id: Optional[int] = None,
        business_connection_id: Optional[str] = None,
    ):
        """Send document"""
        return await self._request(
            "sendDocument",
            chat_id=chat_id,
            document=document,
            thumbnail=thumbnail,
            caption=caption,
            parse_mode=parse_mode,
            caption_entities=caption_entities,
            disable_content_type_detection=disable_content_type_detection,
            disable_notification=disable_notification,
            protect_content=protect_content,
            reply_parameters=reply_parameters,
            reply_markup=reply_markup,
            message_thread_id=message_thread_id,
            business_connection_id=business_connection_id,
        )

    async def send_video(
        self,
        chat_id: Union[int, str],
        video: Union[str, Any],
        duration: Optional[int] = None,
        width: Optional[int] = None,
        height: Optional[int] = None,
        thumbnail: Optional[Any] = None,
        caption: Optional[str] = None,
        parse_mode: Optional[str] = None,
        caption_entities: Optional[List[Dict]] = None,
        has_spoiler: Optional[bool] = None,
        supports_streaming: Optional[bool] = None,
        disable_notification: Optional[bool] = None,
        protect_content: Optional[bool] = None,
        reply_parameters: Optional[Dict] = None,
        reply_markup: Optional[Dict] = None,
        message_thread_id: Optional[int] = None,
        business_connection_id: Optional[str] = None,
    ):
        """Send video"""
        return await self._request(
            "sendVideo",
            chat_id=chat_id,
            video=video,
            duration=duration,
            width=width,
            height=height,
            thumbnail=thumbnail,
            caption=caption,
            parse_mode=parse_mode,
            caption_entities=caption_entities,
            has_spoiler=has_spoiler,
            supports_streaming=supports_streaming,
            disable_notification=disable_notification,
            protect_content=protect_content,
            reply_parameters=reply_parameters,
            reply_markup=reply_markup,
            message_thread_id=message_thread_id,
            business_connection_id=business_connection_id,
        )

    async def send_animation(
        self,
        chat_id: Union[int, str],
        animation: Union[str, Any],
        duration: Optional[int] = None,
        width: Optional[int] = None,
        height: Optional[int] = None,
        thumbnail: Optional[Any] = None,
        caption: Optional[str] = None,
        parse_mode: Optional[str] = None,
        caption_entities: Optional[List[Dict]] = None,
        has_spoiler: Optional[bool] = None,
        disable_notification: Optional[bool] = None,
        protect_content: Optional[bool] = None,
        reply_parameters: Optional[Dict] = None,
        reply_markup: Optional[Dict] = None,
        message_thread_id: Optional[int] = None,
        business_connection_id: Optional[str] = None,
    ):
        """Send animation (GIF or H.264/MPEG-4 AVC video without sound)"""
        return await self._request(
            "sendAnimation",
            chat_id=chat_id,
            animation=animation,
            duration=duration,
            width=width,
            height=height,
            thumbnail=thumbnail,
            caption=caption,
            parse_mode=parse_mode,
            caption_entities=caption_entities,
            has_spoiler=has_spoiler,
            disable_notification=disable_notification,
            protect_content=protect_content,
            reply_parameters=reply_parameters,
            reply_markup=reply_markup,
            message_thread_id=message_thread_id,
            business_connection_id=business_connection_id,
        )

    async def send_voice(
        self,
        chat_id: Union[int, str],
        voice: Union[str, Any],
        caption: Optional[str] = None,
        parse_mode: Optional[str] = None,
        caption_entities: Optional[List[Dict]] = None,
        duration: Optional[int] = None,
        disable_notification: Optional[bool] = None,
        protect_content: Optional[bool] = None,
        reply_parameters: Optional[Dict] = None,
        reply_markup: Optional[Dict] = None,
        message_thread_id: Optional[int] = None,
        business_connection_id: Optional[str] = None,
    ):
        """Send voice message"""
        return await self._request(
            "sendVoice",
            chat_id=chat_id,
            voice=voice,
            caption=caption,
            parse_mode=parse_mode,
            caption_entities=caption_entities,
            duration=duration,
            disable_notification=disable_notification,
            protect_content=protect_content,
            reply_parameters=reply_parameters,
            reply_markup=reply_markup,
            message_thread_id=message_thread_id,
            business_connection_id=business_connection_id,
        )

    async def send_video_note(
        self,
        chat_id: Union[int, str],
        video_note: Union[str, Any],
        duration: Optional[int] = None,
        length: Optional[int] = None,
        thumbnail: Optional[Any] = None,
        disable_notification: Optional[bool] = None,
        protect_content: Optional[bool] = None,
        reply_parameters: Optional[Dict] = None,
        reply_markup: Optional[Dict] = None,
        message_thread_id: Optional[int] = None,
        business_connection_id: Optional[str] = None,
    ):
        """Send video note (round video)"""
        return await self._request(
            "sendVideoNote",
            chat_id=chat_id,
            video_note=video_note,
            duration=duration,
            length=length,
            thumbnail=thumbnail,
            disable_notification=disable_notification,
            protect_content=protect_content,
            reply_parameters=reply_parameters,
            reply_markup=reply_markup,
            message_thread_id=message_thread_id,
            business_connection_id=business_connection_id,
        )

    async def send_media_group(
        self,
        chat_id: Union[int, str],
        media: List[Dict],
        disable_notification: Optional[bool] = None,
        protect_content: Optional[bool] = None,
        reply_parameters: Optional[Dict] = None,
        message_thread_id: Optional[int] = None,
        business_connection_id: Optional[str] = None,
    ):
        """Send group of photos, videos, documents or audios as an album"""
        return await self._request(
            "sendMediaGroup",
            chat_id=chat_id,
            media=media,
            disable_notification=disable_notification,
            protect_content=protect_content,
            reply_parameters=reply_parameters,
            message_thread_id=message_thread_id,
            business_connection_id=business_connection_id,
        )

    async def send_location(
        self,
        chat_id: Union[int, str],
        latitude: float,
        longitude: float,
        horizontal_accuracy: Optional[float] = None,
        live_period: Optional[int] = None,
        heading: Optional[int] = None,
        proximity_alert_radius: Optional[int] = None,
        disable_notification: Optional[bool] = None,
        protect_content: Optional[bool] = None,
        reply_parameters: Optional[Dict] = None,
        reply_markup: Optional[Dict] = None,
        message_thread_id: Optional[int] = None,
        business_connection_id: Optional[str] = None,
    ):
        """Send point on the map"""
        return await self._request(
            "sendLocation",
            chat_id=chat_id,
            latitude=latitude,
            longitude=longitude,
            horizontal_accuracy=horizontal_accuracy,
            live_period=live_period,
            heading=heading,
            proximity_alert_radius=proximity_alert_radius,
            disable_notification=disable_notification,
            protect_content=protect_content,
            reply_parameters=reply_parameters,
            reply_markup=reply_markup,
            message_thread_id=message_thread_id,
            business_connection_id=business_connection_id,
        )

    async def send_venue(
        self,
        chat_id: Union[int, str],
        latitude: float,
        longitude: float,
        title: str,
        address: str,
        foursquare_id: Optional[str] = None,
        foursquare_type: Optional[str] = None,
        google_place_id: Optional[str] = None,
        google_place_type: Optional[str] = None,
        disable_notification: Optional[bool] = None,
        protect_content: Optional[bool] = None,
        reply_parameters: Optional[Dict] = None,
        reply_markup: Optional[Dict] = None,
        message_thread_id: Optional[int] = None,
        business_connection_id: Optional[str] = None,
    ):
        """Send information about a venue"""
        return await self._request(
            "sendVenue",
            chat_id=chat_id,
            latitude=latitude,
            longitude=longitude,
            title=title,
            address=address,
            foursquare_id=foursquare_id,
            foursquare_type=foursquare_type,
            google_place_id=google_place_id,
            google_place_type=google_place_type,
            disable_notification=disable_notification,
            protect_content=protect_content,
            reply_parameters=reply_parameters,
            reply_markup=reply_markup,
            message_thread_id=message_thread_id,
            business_connection_id=business_connection_id,
        )

    async def send_contact(
        self,
        chat_id: Union[int, str],
        phone_number: str,
        first_name: str,
        last_name: Optional[str] = None,
        vcard: Optional[str] = None,
        disable_notification: Optional[bool] = None,
        protect_content: Optional[bool] = None,
        reply_parameters: Optional[Dict] = None,
        reply_markup: Optional[Dict] = None,
        message_thread_id: Optional[int] = None,
        business_connection_id: Optional[str] = None,
    ):
        """Send phone contact"""
        return await self._request(
            "sendContact",
            chat_id=chat_id,
            phone_number=phone_number,
            first_name=first_name,
            last_name=last_name,
            vcard=vcard,
            disable_notification=disable_notification,
            protect_content=protect_content,
            reply_parameters=reply_parameters,
            reply_markup=reply_markup,
            message_thread_id=message_thread_id,
            business_connection_id=business_connection_id,
        )

    async def send_poll(
        self,
        chat_id: Union[int, str],
        question: str,
        options: List[str],
        is_anonymous: Optional[bool] = None,
        type: Optional[str] = None,
        allows_multiple_answers: Optional[bool] = None,
        correct_option_id: Optional[int] = None,
        explanation: Optional[str] = None,
        explanation_parse_mode: Optional[str] = None,
        explanation_entities: Optional[List[Dict]] = None,
        open_period: Optional[int] = None,
        close_date: Optional[int] = None,
        is_closed: Optional[bool] = None,
        disable_notification: Optional[bool] = None,
        protect_content: Optional[bool] = None,
        reply_parameters: Optional[Dict] = None,
        reply_markup: Optional[Dict] = None,
        message_thread_id: Optional[int] = None,
        business_connection_id: Optional[str] = None,
    ):
        """Send a native poll"""
        return await self._request(
            "sendPoll",
            chat_id=chat_id,
            question=question,
            options=options,
            is_anonymous=is_anonymous,
            type=type,
            allows_multiple_answers=allows_multiple_answers,
            correct_option_id=correct_option_id,
            explanation=explanation,
            explanation_parse_mode=explanation_parse_mode,
            explanation_entities=explanation_entities,
            open_period=open_period,
            close_date=close_date,
            is_closed=is_closed,
            disable_notification=disable_notification,
            protect_content=protect_content,
            reply_parameters=reply_parameters,
            reply_markup=reply_markup,
            message_thread_id=message_thread_id,
            business_connection_id=business_connection_id,
        )

    async def send_dice(
        self,
        chat_id: Union[int, str],
        emoji: Optional[str] = None,
        disable_notification: Optional[bool] = None,
        protect_content: Optional[bool] = None,
        reply_parameters: Optional[Dict] = None,
        reply_markup: Optional[Dict] = None,
        message_thread_id: Optional[int] = None,
        business_connection_id: Optional[str] = None,
    ):
        """Send animated emoji (dice, darts, basketball, etc.)"""
        return await self._request(
            "sendDice",
            chat_id=chat_id,
            emoji=emoji,
            disable_notification=disable_notification,
            protect_content=protect_content,
            reply_parameters=reply_parameters,
            reply_markup=reply_markup,
            message_thread_id=message_thread_id,
            business_connection_id=business_connection_id,
        )

    # ==========================================
    # Editing Messages
    # ==========================================

    async def edit_message_text(
        self,
        text: str,
        chat_id: Optional[Union[int, str]] = None,
        message_id: Optional[int] = None,
        inline_message_id: Optional[str] = None,
        parse_mode: Optional[str] = None,
        entities: Optional[List[Dict]] = None,
        link_preview_options: Optional[Dict] = None,
        reply_markup: Optional[Dict] = None,
        business_connection_id: Optional[str] = None,
    ):
        """Edit text message"""
        return await self._request(
            "editMessageText",
            chat_id=chat_id,
            message_id=message_id,
            inline_message_id=inline_message_id,
            text=text,
            parse_mode=parse_mode,
            entities=entities,
            link_preview_options=link_preview_options,
            reply_markup=reply_markup,
            business_connection_id=business_connection_id,
        )

    async def edit_message_caption(
        self,
        chat_id: Optional[Union[int, str]] = None,
        message_id: Optional[int] = None,
        inline_message_id: Optional[str] = None,
        caption: Optional[str] = None,
        parse_mode: Optional[str] = None,
        caption_entities: Optional[List[Dict]] = None,
        reply_markup: Optional[Dict] = None,
        business_connection_id: Optional[str] = None,
    ):
        """Edit caption of message"""
        return await self._request(
            "editMessageCaption",
            chat_id=chat_id,
            message_id=message_id,
            inline_message_id=inline_message_id,
            caption=caption,
            parse_mode=parse_mode,
            caption_entities=caption_entities,
            reply_markup=reply_markup,
            business_connection_id=business_connection_id,
        )

    async def edit_message_media(
        self,
        media: Dict,
        chat_id: Optional[Union[int, str]] = None,
        message_id: Optional[int] = None,
        inline_message_id: Optional[str] = None,
        reply_markup: Optional[Dict] = None,
        business_connection_id: Optional[str] = None,
    ):
        """Edit animation, audio, document, photo, or video message"""
        return await self._request(
            "editMessageMedia",
            chat_id=chat_id,
            message_id=message_id,
            inline_message_id=inline_message_id,
            media=media,
            reply_markup=reply_markup,
            business_connection_id=business_connection_id,
        )

    async def edit_message_live_location(
        self,
        latitude: float,
        longitude: float,
        chat_id: Optional[Union[int, str]] = None,
        message_id: Optional[int] = None,
        inline_message_id: Optional[str] = None,
        horizontal_accuracy: Optional[float] = None,
        heading: Optional[int] = None,
        proximity_alert_radius: Optional[int] = None,
        reply_markup: Optional[Dict] = None,
        business_connection_id: Optional[str] = None,
    ):
        """Edit live location message"""
        return await self._request(
            "editMessageLiveLocation",
            chat_id=chat_id,
            message_id=message_id,
            inline_message_id=inline_message_id,
            latitude=latitude,
            longitude=longitude,
            horizontal_accuracy=horizontal_accuracy,
            heading=heading,
            proximity_alert_radius=proximity_alert_radius,
            reply_markup=reply_markup,
            business_connection_id=business_connection_id,
        )

    async def stop_message_live_location(
        self,
        chat_id: Optional[Union[int, str]] = None,
        message_id: Optional[int] = None,
        inline_message_id: Optional[str] = None,
        reply_markup: Optional[Dict] = None,
        business_connection_id: Optional[str] = None,
    ):
        """Stop updating live location message"""
        return await self._request(
            "stopMessageLiveLocation",
            chat_id=chat_id,
            message_id=message_id,
            inline_message_id=inline_message_id,
            reply_markup=reply_markup,
            business_connection_id=business_connection_id,
        )

    async def edit_message_reply_markup(
        self,
        chat_id: Optional[Union[int, str]] = None,
        message_id: Optional[int] = None,
        inline_message_id: Optional[str] = None,
        reply_markup: Optional[Dict] = None,
        business_connection_id: Optional[str] = None,
    ):
        """Edit reply markup of message"""
        return await self._request(
            "editMessageReplyMarkup",
            chat_id=chat_id,
            message_id=message_id,
            inline_message_id=inline_message_id,
            reply_markup=reply_markup,
            business_connection_id=business_connection_id,
        )

    async def stop_poll(
        self,
        chat_id: Union[int, str],
        message_id: int,
        reply_markup: Optional[Dict] = None,
        business_connection_id: Optional[str] = None,
    ):
        """Stop a poll"""
        return await self._request(
            "stopPoll",
            chat_id=chat_id,
            message_id=message_id,
            reply_markup=reply_markup,
            business_connection_id=business_connection_id,
        )

    async def delete_message(self, chat_id: Union[int, str], message_id: int):
        """Delete a message"""
        return await self._request(
            "deleteMessage",
            chat_id=chat_id,
            message_id=message_id,
        )

    async def delete_messages(self, chat_id: Union[int, str], message_ids: List[int]):
        """Delete multiple messages"""
        return await self._request(
            "deleteMessages",
            chat_id=chat_id,
            message_ids=message_ids,
        )

    # ==========================================
    # Stickers
    # ==========================================

    async def send_sticker(
        self,
        chat_id: Union[int, str],
        sticker: Union[str, Any],
        emoji: Optional[str] = None,
        disable_notification: Optional[bool] = None,
        protect_content: Optional[bool] = None,
        reply_parameters: Optional[Dict] = None,
        reply_markup: Optional[Dict] = None,
        message_thread_id: Optional[int] = None,
        business_connection_id: Optional[str] = None,
    ):
        """Send sticker"""
        return await self._request(
            "sendSticker",
            chat_id=chat_id,
            sticker=sticker,
            emoji=emoji,
            disable_notification=disable_notification,
            protect_content=protect_content,
            reply_parameters=reply_parameters,
            reply_markup=reply_markup,
            message_thread_id=message_thread_id,
            business_connection_id=business_connection_id,
        )

    async def get_sticker_set(self, name: str):
        """Get sticker set"""
        return await self._request("getStickerSet", name=name)

    async def get_custom_emoji_stickers(self, custom_emoji_ids: List[str]):
        """Get information about custom emoji stickers"""
        return await self._request(
            "getCustomEmojiStickers",
            custom_emoji_ids=custom_emoji_ids,
        )

    async def upload_sticker_file(
        self,
        user_id: int,
        sticker: Any,
        sticker_format: str,
    ):
        """Upload sticker file"""
        return await self._request(
            "uploadStickerFile",
            user_id=user_id,
            sticker=sticker,
            sticker_format=sticker_format,
        )

    async def create_new_sticker_set(
        self,
        user_id: int,
        name: str,
        title: str,
        stickers: List[Dict],
        sticker_format: str,
        sticker_type: Optional[str] = None,
        needs_repainting: Optional[bool] = None,
    ):
        """Create new sticker set"""
        return await self._request(
            "createNewStickerSet",
            user_id=user_id,
            name=name,
            title=title,
            stickers=stickers,
            sticker_format=sticker_format,
            sticker_type=sticker_type,
            needs_repainting=needs_repainting,
        )

    async def add_sticker_to_set(
        self,
        user_id: int,
        name: str,
        sticker: Dict,
    ):
        """Add sticker to set"""
        return await self._request(
            "addStickerToSet",
            user_id=user_id,
            name=name,
            sticker=sticker,
        )

    async def set_sticker_position_in_set(self, sticker: str, position: int):
        """Move sticker in set"""
        return await self._request(
            "setStickerPositionInSet",
            sticker=sticker,
            position=position,
        )

    async def delete_sticker_from_set(self, sticker: str):
        """Delete sticker from set"""
        return await self._request("deleteStickerFromSet", sticker=sticker)

    async def set_sticker_emoji_list(self, sticker: str, emoji_list: List[str]):
        """Change emoji list of sticker"""
        return await self._request(
            "setStickerEmojiList",
            sticker=sticker,
            emoji_list=emoji_list,
        )

    async def set_sticker_keywords(self, sticker: str, keywords: Optional[List[str]] = None):
        """Change search keywords of sticker"""
        return await self._request(
            "setStickerKeywords",
            sticker=sticker,
            keywords=keywords,
        )

    async def set_sticker_mask_position(self, sticker: str, mask_position: Optional[Dict] = None):
        """Change mask position of mask sticker"""
        return await self._request(
            "setStickerMaskPosition",
            sticker=sticker,
            mask_position=mask_position,
        )

    async def set_sticker_set_title(self, name: str, title: str):
        """Set sticker set title"""
        return await self._request(
            "setStickerSetTitle",
            name=name,
            title=title,
        )

    async def set_sticker_set_thumbnail(
        self,
        name: str,
        user_id: int,
        thumbnail: Optional[Any] = None,
    ):
        """Set sticker set thumbnail"""
        return await self._request(
            "setStickerSetThumbnail",
            name=name,
            user_id=user_id,
            thumbnail=thumbnail,
        )

    async def set_custom_emoji_sticker_set_thumbnail(
        self,
        name: str,
        custom_emoji_id: Optional[str] = None,
    ):
        """Set custom emoji sticker set thumbnail"""
        return await self._request(
            "setCustomEmojiStickerSetThumbnail",
            name=name,
            custom_emoji_id=custom_emoji_id,
        )

    async def delete_sticker_set(self, name: str):
        """Delete sticker set"""
        return await self._request("deleteStickerSet", name=name)

    # ==========================================
    # Inline Mode
    # ==========================================

    async def answer_inline_query(
        self,
        inline_query_id: str,
        results: List[Dict],
        cache_time: int = 300,
        is_personal: bool = False,
        next_offset: Optional[str] = None,
        button: Optional[Dict] = None,
    ):
        """Answer inline query"""
        return await self._request(
            "answerInlineQuery",
            inline_query_id=inline_query_id,
            results=results,
            cache_time=cache_time,
            is_personal=is_personal,
            next_offset=next_offset,
            button=button,
        )

    async def answer_web_app_query(
        self,
        web_app_query_id: str,
        result: Dict,
    ):
        """Set result of interaction with Web App"""
        return await self._request(
            "answerWebAppQuery",
            web_app_query_id=web_app_query_id,
            result=result,
        )

    # ==========================================
    # Payments
    # ==========================================

    async def send_invoice(
        self,
        chat_id: Union[int, str],
        title: str,
        description: str,
        payload: str,
        provider_token: str,
        currency: str,
        prices: List[Dict],
        max_tip_amount: Optional[int] = None,
        suggested_tip_amounts: Optional[List[int]] = None,
        start_parameter: Optional[str] = None,
        provider_data: Optional[str] = None,
        photo_url: Optional[str] = None,
        photo_size: Optional[int] = None,
        photo_width: Optional[int] = None,
        photo_height: Optional[int] = None,
        need_name: Optional[bool] = None,
        need_phone_number: Optional[bool] = None,
        need_email: Optional[bool] = None,
        need_shipping_address: Optional[bool] = None,
        send_phone_number_to_provider: Optional[bool] = None,
        send_email_to_provider: Optional[bool] = None,
        is_flexible: Optional[bool] = None,
        disable_notification: Optional[bool] = None,
        protect_content: Optional[bool] = None,
        reply_parameters: Optional[Dict] = None,
        reply_markup: Optional[Dict] = None,
        message_thread_id: Optional[int] = None,
    ):
        """Send invoice"""
        return await self._request(
            "sendInvoice",
            chat_id=chat_id,
            title=title,
            description=description,
            payload=payload,
            provider_token=provider_token,
            currency=currency,
            prices=prices,
            max_tip_amount=max_tip_amount,
            suggested_tip_amounts=suggested_tip_amounts,
            start_parameter=start_parameter,
            provider_data=provider_data,
            photo_url=photo_url,
            photo_size=photo_size,
            photo_width=photo_width,
            photo_height=photo_height,
            need_name=need_name,
            need_phone_number=need_phone_number,
            need_email=need_email,
            need_shipping_address=need_shipping_address,
            send_phone_number_to_provider=send_phone_number_to_provider,
            send_email_to_provider=send_email_to_provider,
            is_flexible=is_flexible,
            disable_notification=disable_notification,
            protect_content=protect_content,
            reply_parameters=reply_parameters,
            reply_markup=reply_markup,
            message_thread_id=message_thread_id,
        )

    async def create_invoice_link(
        self,
        title: str,
        description: str,
        payload: str,
        provider_token: str,
        currency: str,
        prices: List[Dict],
        max_tip_amount: Optional[int] = None,
        suggested_tip_amounts: Optional[List[int]] = None,
        provider_data: Optional[str] = None,
        photo_url: Optional[str] = None,
        photo_size: Optional[int] = None,
        photo_width: Optional[int] = None,
        photo_height: Optional[int] = None,
        need_name: Optional[bool] = None,
        need_phone_number: Optional[bool] = None,
        need_email: Optional[bool] = None,
        need_shipping_address: Optional[bool] = None,
        send_phone_number_to_provider: Optional[bool] = None,
        send_email_to_provider: Optional[bool] = None,
        is_flexible: Optional[bool] = None,
    ):
        """Create invoice link"""
        return await self._request(
            "createInvoiceLink",
            title=title,
            description=description,
            payload=payload,
            provider_token=provider_token,
            currency=currency,
            prices=prices,
            max_tip_amount=max_tip_amount,
            suggested_tip_amounts=suggested_tip_amounts,
            provider_data=provider_data,
            photo_url=photo_url,
            photo_size=photo_size,
            photo_width=photo_width,
            photo_height=photo_height,
            need_name=need_name,
            need_phone_number=need_phone_number,
            need_email=need_email,
            need_shipping_address=need_shipping_address,
            send_phone_number_to_provider=send_phone_number_to_provider,
            send_email_to_provider=send_email_to_provider,
            is_flexible=is_flexible,
        )

    async def answer_shipping_query(
        self,
        shipping_query_id: str,
        ok: bool,
        shipping_options: Optional[List[Dict]] = None,
        error_message: Optional[str] = None,
    ):
        """Answer shipping query"""
        return await self._request(
            "answerShippingQuery",
            shipping_query_id=shipping_query_id,
            ok=ok,
            shipping_options=shipping_options,
            error_message=error_message,
        )

    async def answer_pre_checkout_query(
        self,
        pre_checkout_query_id: str,
        ok: bool,
        error_message: Optional[str] = None,
    ):
        """Answer pre-checkout query"""
        return await self._request(
            "answerPreCheckoutQuery",
            pre_checkout_query_id=pre_checkout_query_id,
            ok=ok,
            error_message=error_message,
        )

    # ==========================================
    # Games
    # ==========================================

    async def send_game(
        self,
        chat_id: int,
        game_short_name: str,
        disable_notification: Optional[bool] = None,
        protect_content: Optional[bool] = None,
        reply_parameters: Optional[Dict] = None,
        reply_markup: Optional[Dict] = None,
        message_thread_id: Optional[int] = None,
        business_connection_id: Optional[str] = None,
    ):
        """Send game"""
        return await self._request(
            "sendGame",
            chat_id=chat_id,
            game_short_name=game_short_name,
            disable_notification=disable_notification,
            protect_content=protect_content,
            reply_parameters=reply_parameters,
            reply_markup=reply_markup,
            message_thread_id=message_thread_id,
            business_connection_id=business_connection_id,
        )

    async def set_game_score(
        self,
        user_id: int,
        score: int,
        force: Optional[bool] = None,
        disable_edit_message: Optional[bool] = None,
        chat_id: Optional[int] = None,
        message_id: Optional[int] = None,
        inline_message_id: Optional[str] = None,
    ):
        """Set game score"""
        return await self._request(
            "setGameScore",
            user_id=user_id,
            score=score,
            force=force,
            disable_edit_message=disable_edit_message,
            chat_id=chat_id,
            message_id=message_id,
            inline_message_id=inline_message_id,
        )

    async def get_game_high_scores(
        self,
        user_id: int,
        chat_id: Optional[int] = None,
        message_id: Optional[int] = None,
        inline_message_id: Optional[str] = None,
    ):
        """Get game high scores"""
        return await self._request(
            "getGameHighScores",
            user_id=user_id,
            chat_id=chat_id,
            message_id=message_id,
            inline_message_id=inline_message_id,
        )

    # ==========================================
    # Callback Queries
    # ==========================================

    async def answer_callback_query(
        self,
        callback_query_id: str,
        text: Optional[str] = None,
        show_alert: bool = False,
        url: Optional[str] = None,
        cache_time: int = 0,
    ):
        """Answer callback query"""
        return await self._request(
            "answerCallbackQuery",
            callback_query_id=callback_query_id,
            text=text,
            show_alert=show_alert,
            url=url,
            cache_time=cache_time,
        )

    # ==========================================
    # Managing Bot Properties
    # ==========================================

    async def set_my_commands(
        self,
        commands: List[Dict],
        scope: Optional[Dict] = None,
        language_code: Optional[str] = None,
    ):
        """Set bot commands"""
        return await self._request(
            "setMyCommands",
            commands=commands,
            scope=scope,
            language_code=language_code,
        )

    async def delete_my_commands(
        self,
        scope: Optional[Dict] = None,
        language_code: Optional[str] = None,
    ):
        """Delete bot commands"""
        return await self._request(
            "deleteMyCommands",
            scope=scope,
            language_code=language_code,
        )

    async def get_my_commands(
        self,
        scope: Optional[Dict] = None,
        language_code: Optional[str] = None,
    ):
        """Get bot commands"""
        return await self._request(
            "getMyCommands",
            scope=scope,
            language_code=language_code,
        )

    async def set_my_name(
        self,
        name: Optional[str] = None,
        language_code: Optional[str] = None,
    ):
        """Set bot name"""
        return await self._request(
            "setMyName",
            name=name,
            language_code=language_code,
        )

    async def get_my_name(self, language_code: Optional[str] = None):
        """Get bot name"""
        return await self._request("getMyName", language_code=language_code)

    async def set_my_description(
        self,
        description: Optional[str] = None,
        language_code: Optional[str] = None,
    ):
        """Set bot description"""
        return await self._request(
            "setMyDescription",
            description=description,
            language_code=language_code,
        )

    async def get_my_description(self, language_code: Optional[str] = None):
        """Get bot description"""
        return await self._request("getMyDescription", language_code=language_code)

    async def set_my_short_description(
        self,
        short_description: Optional[str] = None,
        language_code: Optional[str] = None,
    ):
        """Set bot short description"""
        return await self._request(
            "setMyShortDescription",
            short_description=short_description,
            language_code=language_code,
        )

    async def get_my_short_description(self, language_code: Optional[str] = None):
        """Get bot short description"""
        return await self._request("getMyShortDescription", language_code=language_code)

    async def set_chat_menu_button(
        self,
        chat_id: Optional[int] = None,
        menu_button: Optional[Dict] = None,
    ):
        """Set chat menu button"""
        return await self._request(
            "setChatMenuButton",
            chat_id=chat_id,
            menu_button=menu_button,
        )

    async def get_chat_menu_button(self, chat_id: Optional[int] = None):
        """Get chat menu button"""
        return await self._request("getChatMenuButton", chat_id=chat_id)

    async def set_my_default_administrator_rights(
        self,
        rights: Optional[Dict] = None,
        for_channels: Optional[bool] = None,
    ):
        """Set default administrator rights"""
        return await self._request(
            "setMyDefaultAdministratorRights",
            rights=rights,
            for_channels=for_channels,
        )

    async def get_my_default_administrator_rights(self, for_channels: Optional[bool] = None):
        """Get default administrator rights"""
        return await self._request(
            "getMyDefaultAdministratorRights",
            for_channels=for_channels,
        )

    # ==========================================
    # Chat Management
    # ==========================================

    async def get_chat(self, chat_id: Union[int, str]):
        """Get chat information"""
        return await self._request("getChat", chat_id=chat_id)

    async def get_chat_administrators(self, chat_id: Union[int, str]):
        """Get chat administrators"""
        return await self._request("getChatAdministrators", chat_id=chat_id)

    async def get_chat_member_count(self, chat_id: Union[int, str]):
        """Get number of members in chat"""
        return await self._request("getChatMemberCount", chat_id=chat_id)

    async def get_chat_member(self, chat_id: Union[int, str], user_id: int):
        """Get chat member"""
        return await self._request(
            "getChatMember",
            chat_id=chat_id,
            user_id=user_id,
        )

    async def set_chat_sticker_set(self, chat_id: Union[int, str], sticker_set_name: str):
        """Set chat sticker set"""
        return await self._request(
            "setChatStickerSet",
            chat_id=chat_id,
            sticker_set_name=sticker_set_name,
        )

    async def delete_chat_sticker_set(self, chat_id: Union[int, str]):
        """Delete chat sticker set"""
        return await self._request("deleteChatStickerSet", chat_id=chat_id)

    async def ban_chat_member(
        self,
        chat_id: Union[int, str],
        user_id: int,
        until_date: Optional[int] = None,
        revoke_messages: Optional[bool] = None,
    ):
        """Ban chat member"""
        return await self._request(
            "banChatMember",
            chat_id=chat_id,
            user_id=user_id,
            until_date=until_date,
            revoke_messages=revoke_messages,
        )

    async def unban_chat_member(
        self,
        chat_id: Union[int, str],
        user_id: int,
        only_if_banned: Optional[bool] = None,
    ):
        """Unban chat member"""
        return await self._request(
            "unbanChatMember",
            chat_id=chat_id,
            user_id=user_id,
            only_if_banned=only_if_banned,
        )

    async def restrict_chat_member(
        self,
        chat_id: Union[int, str],
        user_id: int,
        permissions: Dict,
        use_independent_chat_permissions: Optional[bool] = None,
        until_date: Optional[int] = None,
    ):
        """Restrict chat member"""
        return await self._request(
            "restrictChatMember",
            chat_id=chat_id,
            user_id=user_id,
            permissions=permissions,
            use_independent_chat_permissions=use_independent_chat_permissions,
            until_date=until_date,
        )

    async def promote_chat_member(
        self,
        chat_id: Union[int, str],
        user_id: int,
        is_anonymous: Optional[bool] = None,
        can_manage_chat: Optional[bool] = None,
        can_delete_messages: Optional[bool] = None,
        can_manage_video_chats: Optional[bool] = None,
        can_restrict_members: Optional[bool] = None,
        can_promote_members: Optional[bool] = None,
        can_change_info: Optional[bool] = None,
        can_invite_users: Optional[bool] = None,
        can_post_messages: Optional[bool] = None,
        can_edit_messages: Optional[bool] = None,
        can_pin_messages: Optional[bool] = None,
        can_post_stories: Optional[bool] = None,
        can_edit_stories: Optional[bool] = None,
        can_delete_stories: Optional[bool] = None,
        can_manage_topics: Optional[bool] = None,
    ):
        """Promote chat member"""
        return await self._request(
            "promoteChatMember",
            chat_id=chat_id,
            user_id=user_id,
            is_anonymous=is_anonymous,
            can_manage_chat=can_manage_chat,
            can_delete_messages=can_delete_messages,
            can_manage_video_chats=can_manage_video_chats,
            can_restrict_members=can_restrict_members,
            can_promote_members=can_promote_members,
            can_change_info=can_change_info,
            can_invite_users=can_invite_users,
            can_post_messages=can_post_messages,
            can_edit_messages=can_edit_messages,
            can_pin_messages=can_pin_messages,
            can_post_stories=can_post_stories,
            can_edit_stories=can_edit_stories,
            can_delete_stories=can_delete_stories,
            can_manage_topics=can_manage_topics,
        )

    async def set_chat_administrator_custom_title(
        self,
        chat_id: Union[int, str],
        user_id: int,
        custom_title: str,
    ):
        """Set custom title for administrator"""
        return await self._request(
            "setChatAdministratorCustomTitle",
            chat_id=chat_id,
            user_id=user_id,
            custom_title=custom_title,
        )

    async def set_chat_permissions(
        self,
        chat_id: Union[int, str],
        permissions: Dict,
        use_independent_chat_permissions: Optional[bool] = None,
    ):
        """Set chat permissions"""
        return await self._request(
            "setChatPermissions",
            chat_id=chat_id,
            permissions=permissions,
            use_independent_chat_permissions=use_independent_chat_permissions,
        )

    async def export_chat_invite_link(self, chat_id: Union[int, str]):
        """Export chat invite link"""
        return await self._request("exportChatInviteLink", chat_id=chat_id)

    async def create_chat_invite_link(
        self,
        chat_id: Union[int, str],
        name: Optional[str] = None,
        expire_date: Optional[int] = None,
        member_limit: Optional[int] = None,
        creates_join_request: Optional[bool] = None,
    ):
        """Create chat invite link"""
        return await self._request(
            "createChatInviteLink",
            chat_id=chat_id,
            name=name,
            expire_date=expire_date,
            member_limit=member_limit,
            creates_join_request=creates_join_request,
        )

    async def edit_chat_invite_link(
        self,
        chat_id: Union[int, str],
        invite_link: str,
        name: Optional[str] = None,
        expire_date: Optional[int] = None,
        member_limit: Optional[int] = None,
        creates_join_request: Optional[bool] = None,
    ):
        """Edit chat invite link"""
        return await self._request(
            "editChatInviteLink",
            chat_id=chat_id,
            invite_link=invite_link,
            name=name,
            expire_date=expire_date,
            member_limit=member_limit,
            creates_join_request=creates_join_request,
        )

    async def revoke_chat_invite_link(
        self,
        chat_id: Union[int, str],
        invite_link: str,
    ):
        """Revoke chat invite link"""
        return await self._request(
            "revokeChatInviteLink",
            chat_id=chat_id,
            invite_link=invite_link,
        )

    async def approve_chat_join_request(self, chat_id: Union[int, str], user_id: int):
        """Approve chat join request"""
        return await self._request(
            "approveChatJoinRequest",
            chat_id=chat_id,
            user_id=user_id,
        )

    async def decline_chat_join_request(self, chat_id: Union[int, str], user_id: int):
        """Decline chat join request"""
        return await self._request(
            "declineChatJoinRequest",
            chat_id=chat_id,
            user_id=user_id,
        )

    async def set_chat_photo(self, chat_id: Union[int, str], photo: Any):
        """Set chat photo"""
        return await self._request("setChatPhoto", chat_id=chat_id, photo=photo)

    async def delete_chat_photo(self, chat_id: Union[int, str]):
        """Delete chat photo"""
        return await self._request("deleteChatPhoto", chat_id=chat_id)

    async def set_chat_title(self, chat_id: Union[int, str], title: str):
        """Set chat title"""
        return await self._request("setChatTitle", chat_id=chat_id, title=title)

    async def set_chat_description(
        self,
        chat_id: Union[int, str],
        description: Optional[str] = None,
    ):
        """Set chat description"""
        return await self._request(
            "setChatDescription",
            chat_id=chat_id,
            description=description,
        )

    async def pin_chat_message(
        self,
        chat_id: Union[int, str],
        message_id: int,
        disable_notification: Optional[bool] = None,
    ):
        """Pin chat message"""
        return await self._request(
            "pinChatMessage",
            chat_id=chat_id,
            message_id=message_id,
            disable_notification=disable_notification,
        )

    async def unpin_chat_message(
        self,
        chat_id: Union[int, str],
        message_id: Optional[int] = None,
    ):
        """Unpin chat message"""
        return await self._request(
            "unpinChatMessage",
            chat_id=chat_id,
            message_id=message_id,
        )

    async def unpin_all_chat_messages(self, chat_id: Union[int, str]):
        """Unpin all chat messages"""
        return await self._request("unpinAllChatMessages", chat_id=chat_id)

    async def leave_chat(self, chat_id: Union[int, str]):
        """Leave chat"""
        return await self._request("leaveChat", chat_id=chat_id)

    # ==========================================
    # Forum Topic Management
    # ==========================================

    async def create_forum_topic(
        self,
        chat_id: Union[int, str],
        name: str,
        icon_color: Optional[int] = None,
        icon_custom_emoji_id: Optional[str] = None,
    ):
        """Create forum topic"""
        return await self._request(
            "createForumTopic",
            chat_id=chat_id,
            name=name,
            icon_color=icon_color,
            icon_custom_emoji_id=icon_custom_emoji_id,
        )

    async def edit_forum_topic(
        self,
        chat_id: Union[int, str],
        message_thread_id: int,
        name: Optional[str] = None,
        icon_custom_emoji_id: Optional[str] = None,
    ):
        """Edit forum topic"""
        return await self._request(
            "editForumTopic",
            chat_id=chat_id,
            message_thread_id=message_thread_id,
            name=name,
            icon_custom_emoji_id=icon_custom_emoji_id,
        )

    async def close_forum_topic(
        self,
        chat_id: Union[int, str],
        message_thread_id: int,
    ):
        """Close forum topic"""
        return await self._request(
            "closeForumTopic",
            chat_id=chat_id,
            message_thread_id=message_thread_id,
        )

    async def reopen_forum_topic(
        self,
        chat_id: Union[int, str],
        message_thread_id: int,
    ):
        """Reopen forum topic"""
        return await self._request(
            "reopenForumTopic",
            chat_id=chat_id,
            message_thread_id=message_thread_id,
        )

    async def delete_forum_topic(
        self,
        chat_id: Union[int, str],
        message_thread_id: int,
    ):
        """Delete forum topic"""
        return await self._request(
            "deleteForumTopic",
            chat_id=chat_id,
            message_thread_id=message_thread_id,
        )

    async def unpin_all_forum_topic_messages(
        self,
        chat_id: Union[int, str],
        message_thread_id: int,
    ):
        """Unpin all forum topic messages"""
        return await self._request(
            "unpinAllForumTopicMessages",
            chat_id=chat_id,
            message_thread_id=message_thread_id,
        )

    async def edit_general_forum_topic(
        self,
        chat_id: Union[int, str],
        name: str,
    ):
        """Edit general forum topic"""
        return await self._request(
            "editGeneralForumTopic",
            chat_id=chat_id,
            name=name,
        )

    async def close_general_forum_topic(self, chat_id: Union[int, str]):
        """Close general forum topic"""
        return await self._request("closeGeneralForumTopic", chat_id=chat_id)

    async def reopen_general_forum_topic(self, chat_id: Union[int, str]):
        """Reopen general forum topic"""
        return await self._request("reopenGeneralForumTopic", chat_id=chat_id)

    async def hide_general_forum_topic(self, chat_id: Union[int, str]):
        """Hide general forum topic"""
        return await self._request("hideGeneralForumTopic", chat_id=chat_id)

    async def unhide_general_forum_topic(self, chat_id: Union[int, str]):
        """Unhide general forum topic"""
        return await self._request("unhideGeneralForumTopic", chat_id=chat_id)

    async def unpin_all_general_forum_topic_messages(self, chat_id: Union[int, str]):
        """Unpin all general forum topic messages"""
        return await self._request("unpinAllGeneralForumTopicMessages", chat_id=chat_id)

    # ==========================================
    # File Management
    # ==========================================

    async def get_file(self, file_id: str):
        """Get file information"""
        return await self._request("getFile", file_id=file_id)

    async def get_user_profile_photos(
        self,
        user_id: int,
        offset: Optional[int] = None,
        limit: int = 100,
    ):
        """Get user profile photos"""
        return await self._request(
            "getUserProfilePhotos",
            user_id=user_id,
            offset=offset,
            limit=limit,
        )
