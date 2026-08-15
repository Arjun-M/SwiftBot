"""
SwiftBot - Deep Linking Utilities
Telegram lets bots receive arbitrary ``start`` parameters through links like
``t.me/<bot>?start=<payload>``. This module builds and parses those links.

Usage:
    from swiftbot.deep_linking import create_start_link, parse_start_param

    # Build a referral link
    link = create_start_link(bot_info, "ref_123")
    # => "https://t.me/<bot_username>?start=ref_123"

    # In the /start handler
    @bot.message(Command("start"))
    async def start(ctx):
        payload = parse_start_param(ctx.args)   # "ref_123"
        if payload.startswith("ref_"):
            ...

    # Private (hidden) links — payload not shown in group chats
    link = create_start_link(bot_info, "secret", private=True)
    # => "https://t.me/<bot_username>?startgroup=secret"

Payloads are limited to 64 base64url characters. ``encode_payload`` and
``decode_payload`` convert arbitrary strings (e.g. user ids, tokens) into
payload-safe base64.

Copyright (c) 2026 Arjun-M/SwiftBot
"""

import base64
from typing import Dict, Optional, Union


DeepLinkError = ValueError


def _get_username(bot_info: Union[Dict, str]) -> str:
    if isinstance(bot_info, str):
        username = bot_info
    elif isinstance(bot_info, dict):
        username = bot_info.get("username") or ""
    else:
        username = getattr(bot_info, "username", None) or ""
    username = username.strip().lstrip("@")
    if not username:
        raise DeepLinkError("could not resolve a bot username for the link")
    return username


def create_start_link(
    bot_info: Union[Dict, str],
    payload: str,
    private: bool = False,
) -> str:
    """
    Build a ``t.me`` deep link with a start payload.

    Args:
        bot_info: Bot username string (with or without ``@``), or the
            ``get_me`` result dict (or any object with a ``username`` attr).
        payload: Start parameter, 1-64 characters from ``[A-Za-z0-9_-]``.
            Use ``encode_payload`` for arbitrary strings.
        private: If True, the link uses ``?startgroup=`` so the payload is
            hidden in group chat previews.

    Returns:
        A ``https://t.me/...`` link.
    """
    if not (1 <= len(payload) <= 64):
        raise DeepLinkError(
            f"start payload must be 1-64 characters, got {len(payload)}"
        )
    if not all(ch.isalnum() or ch in "-_" for ch in payload):
        raise DeepLinkError(
            "start payload must match [A-Za-z0-9_-]; use encode_payload() "
            "for arbitrary strings"
        )
    key = "startgroup" if private else "start"
    return f"https://t.me/{_get_username(bot_info)}?{key}={payload}"


def create_start_link_custom(
    bot_info: Union[Dict, str],
    payload: str,
    param: str = "start",
) -> str:
    """Build a deep link with an arbitrary query parameter name."""
    if not payload:
        raise DeepLinkError("payload must not be empty")
    if not all(ch.isalnum() or ch in "-_" for ch in param):
        raise DeepLinkError(f"invalid parameter name {param!r}")
    return f"https://t.me/{_get_username(bot_info)}?{param}={payload}"


def _to_bytes(data: Union[str, bytes, Dict]) -> bytes:
    """Normalize a payload into bytes: strings encode directly, dicts JSON-encode."""
    if isinstance(data, str):
        return data.encode("utf-8")
    if isinstance(data, bytes):
        return data
    if isinstance(data, dict):
        import json
        return json.dumps(data, sort_keys=True, separators=(",", ":")).encode("utf-8")
    raise DeepLinkError(f"unsupported payload type {type(data).__name__}")


def _from_bytes(raw: bytes) -> Union[str, str]:
    """Decode raw payload bytes: JSON objects become dicts, else plain string."""
    if raw[:1] == b"{" or raw[:1] == b"[":
        import json
        try:
            return json.loads(raw)
        except (ValueError, UnicodeDecodeError):
            pass
    try:
        return raw.decode("utf-8")
    except UnicodeDecodeError as exc:
        raise DeepLinkError("could not decode payload bytes") from exc


def encode_payload(data: Union[str, bytes, Dict]) -> str:
    """
    Convert an arbitrary string or dict into a payload-safe base64url token
    (padded ``=`` are dropped; ``decode_payload`` restores them).
    Raises ``DeepLinkError`` if the token exceeds 64 characters.

    Dicts are JSON-serialized (keys sorted) so structured payloads such as
    referral metadata survive the 64-char ``/start`` limit when small enough.
    """
    token = base64.urlsafe_b64encode(_to_bytes(data)).decode("ascii")
    if len(token) > 64:
        raise DeepLinkError(
            f"encoded payload is {len(token)} chars, exceeds the 64 limit"
        )
    return token.rstrip("=")


def decode_payload(token: str) -> Union[str, Dict]:
    """Inverse of ``encode_payload``. Returns a ``dict`` when the payload was."""
    if not (1 <= len(token) <= 64):
        raise DeepLinkError(f"invalid payload token length {len(token)}")
    try:
        padded = token + "=" * (-len(token) % 4)
        return _from_bytes(base64.urlsafe_b64decode(padded))
    except (ValueError, UnicodeDecodeError) as exc:
        raise DeepLinkError(f"could not decode payload {token!r}") from exc


def parse_start_param(args_text: Optional[str]) -> Optional[str]:
    """
    Extract the start payload from the text following ``/start``.

    ``/start ref_123`` -> ``"ref_123"``
    ``/start``         -> ``None``
    """
    if not args_text:
        return None
    payload = args_text.strip().split(None, 1)[0]
    return payload or None
