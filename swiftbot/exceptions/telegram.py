"""
Typed Telegram Bot API error hierarchy.

Instead of raising a bare ``Exception`` for every API failure, the framework
now maps Telegram API error codes and descriptions to typed exceptions that
users can catch precisely, with no string parsing or status-code branching.

Usage:
    try:
        await bot.send_message(chat_id=99999999, text="hi")
    except TelegramError as e:
        print(e.error_code, e.description)
    except UserNotFound:
        print("That user doesn't exist")
    except RetryAfter as e:
        print(f"Back off for {e.retry_after} seconds")
    except MessageNotModified:
        pass  # Nothing to do
"""

from __future__ import annotations

from typing import Any, Optional


class TelegramError(Exception):
    """Base class for all Telegram Bot API errors.

    Attributes:
        error_code: HTTP status code returned by the Telegram API.
        description: The ``description`` field from the API response.
        parameters: Optional ``parameters`` object from the API response
            (e.g. ``{"retry_after": 12}``).
        method: Name of the API method that failed (if known).
    """

    def __init__(
        self,
        error_code: int,
        description: str,
        parameters: Optional[dict] = None,
        method: Optional[str] = None,
    ) -> None:
        self.error_code: int = error_code
        self.description: str = description
        self.parameters: dict = parameters or {}
        self.method: Optional[str] = method
        message = f"Telegram API error {error_code}: {description}"
        if method:
            message = f"[{method}] {message}"
        super().__init__(message)

    @classmethod
    def from_response(
        cls,
        response: dict,
        method: Optional[str] = None,
    ) -> "TelegramError":
        """Build and return the most specific typed exception from a raw API
        error response ``{"ok": False, "error_code": 400, "description": "...",
        "parameters": {...}}``.
        """
        error_code = int(response.get("error_code", 500))
        description = response.get("description", "Unknown error")
        parameters = response.get("parameters") or {}
        try:
            raise_telegram_error(
                error_code, description, parameters=parameters, method=method,
            )
        except TelegramError as e:
            return e
        return TelegramError(error_code, description, parameters=parameters, method=method)

    @property
    def retry_after(self) -> Optional[int]:
        """``retry_after`` value when Telegram rate-limits the request."""
        value = self.parameters.get("retry_after")
        if value is not None:
            try:
                return int(value)
            except (TypeError, ValueError):
                return None
        return None

    @property
    def migrate_to_chat_id(self) -> Optional[int]:
        """``migrate_to_chat_id`` when a supergroup migration happened."""
        value = self.parameters.get("migrate_to_chat_id")
        if value is not None:
            try:
                return int(value)
            except (TypeError, ValueError):
                return None
        return None


# ---------------------------------------------------------------------------
# 4xx client errors (the request is wrong)
# ---------------------------------------------------------------------------

class BadRequest(TelegramError):
    """400 Bad Request — the request was malformed or invalid."""


class Unauthorized(TelegramError):
    """401 Unauthorized — the bot token is invalid or was revoked."""


class Forbidden(TelegramError):
    """403 Forbidden — the bot has no access to this chat/user/action."""


# ---------------------------------------------------------------------------
# Semantic Telegram errors (mapped by error description or code)
# ---------------------------------------------------------------------------

class UserNotFound(BadRequest):
    """The target user could not be found (bad_request: USER_NOT_FOUND)."""


class ChatNotFound(BadRequest):
    """The chat does not exist or the bot is not a member."""


class MessageNotModified(BadRequest):
    """The message text is identical to the current one."""


class MessageToDeleteNotFound(BadRequest):
    """The target message to delete does not exist or is too old."""


class MessageToEditNotFound(BadRequest):
    """The target message to edit does not exist or is too old."""


class MessageIdInvalid(BadRequest):
    """The supplied message_id is invalid for the target chat."""


class ChatWriteForbidden(BadRequest):
    """The bot cannot send messages to this chat."""


class ButtonDataInvalid(BadRequest):
    """Inline button ``callback_data`` exceeds 64 bytes or is malformed."""


class MessageCaptionTooLong(BadRequest):
    """Caption exceeds the allowed length."""


class MessageTextIsEmpty(BadRequest):
    """A text/caption message was sent without content."""


class TooManyRequests(TelegramError):
    """429 Too Many Requests — Telegram is rate limiting this bot."""

    def __init__(self, retry_after: int, description: str = "Too Many Requests: retry after", method: Optional[str] = None) -> None:
        super().__init__(429, description, parameters={"retry_after": retry_after}, method=method)


class MigrateToChat(TelegramError):
    """A group chat has been migrated to a supergroup; use the new chat id.

    The new chat id is available via ``e.migrate_to_chat_id``.
    """

    def __init__(self, migrate_to_chat_id: int, method: Optional[str] = None) -> None:
        super().__init__(
            400,
            f"Need to migrate the chat to a supergroup: {migrate_to_chat_id}",
            parameters={"migrate_to_chat_id": migrate_to_chat_id},
            method=method,
        )


# ---------------------------------------------------------------------------
# Mapping from Telegram error descriptions to exception classes
# ---------------------------------------------------------------------------

_DESCRIPTION_MAP: dict = {
    "user not found": UserNotFound,
    "chat not found": ChatNotFound,
    "message is not modified": MessageNotModified,
    "message to delete not found": MessageToDeleteNotFound,
    "message to edit not found": MessageToEditNotFound,
    "message_id_invalid": MessageIdInvalid,
    "chat_write_forbidden": ChatWriteForbidden,
    "chat was not found": ChatNotFound,
    "button_data_invalid": ButtonDataInvalid,
    "message_caption_too_long": MessageCaptionTooLong,
    "message_text_is_empty": MessageTextIsEmpty,
    "too_many_requests": TooManyRequests,
    "forbidden: bot was blocked by the user": Forbidden,
    "forbidden: bot is not a member of the supergroup chat": Forbidden,
    "forbidden: bot was kicked from the group chat": Forbidden,
    "forbidden: bot was kicked from the channel chat": Forbidden,
    "forbidden: bot was kicked from the supergroup chat": Forbidden,
    "forbidden: bot can't initiate conversation with a user": Forbidden,
    "unauthorized": Unauthorized,
}

_ERROR_CODE_MAP: dict = {
    400: BadRequest,
    401: Unauthorized,
    403: Forbidden,
    404: TelegramError,
    429: TooManyRequests,
    500: TelegramError,
    502: TelegramError,
    503: TelegramError,
    504: TelegramError,
}


def raise_telegram_error(
    error_code: int,
    description: str,
    parameters: Optional[dict] = None,
    method: Optional[str] = None,
) -> None:
    """Raise the most specific typed exception for a Telegram API error.

    Selection order:
    1. ``retry_after`` parameter -> ``TooManyRequests`` (regardless of code)
    2. ``migrate_to_chat_id`` parameter -> ``MigrateToChat``
    3. Known error description -> semantic class
    4. HTTP status code -> generic code-based class
    5. Fallback -> ``TelegramError``
    """
    params = parameters or {}

    retry_after = params.get("retry_after")
    if retry_after is not None:
        try:
            raise TooManyRequests(int(retry_after), description, method=method)
        except TypeError:
            raise TooManyRequests(int(retry_after), description, method=method) from None

    if "migrate_to_chat_id" in params:
        try:
            raise MigrateToChat(int(params["migrate_to_chat_id"]), method=method)
        except (TypeError, ValueError):
            pass

    lower_desc = description.lower()
    for key, cls in _DESCRIPTION_MAP.items():
        if key in lower_desc:
            raise cls(error_code, description, parameters=params, method=method)

    cls = _ERROR_CODE_MAP.get(error_code, TelegramError)
    raise cls(error_code, description, parameters=params, method=method)
