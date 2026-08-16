"""
SwiftBot - Typed Callback Data Factory
A safe, pickle-free way to build structured inline-button payloads.

Usage:
    class Confirm:
        __slots__ = ()

    confirm = CallbackData("confirm", str, int)   # prefix + field types
    button = Button.inline("Yes", confirm.pack("approve", 42))

    # Later, in a callback handler:
    action, item_id = confirm.unpack(callback_query.data)
    # => ("approve", 42)

Data is encoded as ``prefix:<type-tag>:<value>:<type-tag>:<value>`` so
different CallbackData instances never collide, and values survive
URL-safe transport through Telegram without JSON parsing on the bot side.

Copyright (c) 2026 Arjun-M/SwiftBot
"""

import base64
from typing import Any, List, Sequence, Tuple, Type, Union


_ENCODED_TYPES = (str, int, float, bool, bytes)
_SEP = ":"

_TYPE_TAG = {str: "s", int: "i", float: "f", bool: "b", bytes: "y"}
_TYPE_FROM_TAG = {v: k for k, v in _TYPE_TAG.items()}


class CallbackDataInvalid(ValueError):
    """Raised when callback data cannot be decoded (wrong prefix, corrupt data)."""


class CallbackData:
    """
    Typed callback-data builder.

    Define once per payload shape::

        nav = CallbackData("nav", str)
        confirm = CallbackData("confirm", str, int)

    Then::

        kb = InlineKeyboard().add_row(Button.inline("Home", nav.pack("home")))
        button = Button.inline("Approve", confirm.pack("approve", 42))

    And decode in the handler::

        action, item_id = confirm.unpack(update.callback_query.data)
    """

    __slots__ = ("_prefix", "_types", "_max_len")

    def __init__(self, prefix: str, *types: Type[Any], max_length: int = 64):
        """
        Args:
            prefix: Unique namespace for this payload shape (used to
                distinguish payloads from other CallbackData instances).
                Must be 1-16 bytes of ``[A-Za-z0-9_-]``.
            *types: The ordered types of the packed values. Each must be one
                of ``str, int, float, bool, bytes``.
            max_length: Telegram hard limit on callback_data (64 bytes).
                Packing longer payloads raises ``ValueError``.
        """
        if not (1 <= len(prefix) <= 16) or not all(
            ch.isalnum() or ch in "-_" for ch in prefix
        ):
            raise ValueError(
                "prefix must be 1-16 characters from [A-Za-z0-9_-], "
                f"got {prefix!r}"
            )
        for t in types:
            if t not in _TYPE_TAG:
                raise ValueError(
                    f"unsupported value type {t!r}; allowed: "
                    f"{', '.join(t.__name__ for t in _TYPE_TAG)}"
                )
        if not types:
            raise ValueError("at least one value type is required")
        self._prefix = prefix
        self._types = list(types)
        self._max_len = max_length

    @property
    def prefix(self) -> str:
        return self._prefix

    def pack(self, *values: Any) -> str:
        """
        Pack values into a Telegram-safe callback_data string.
        Raises ``ValueError`` if the encoded payload exceeds 64 bytes or the
        number of values does not match the declared shape.
        """
        if len(values) != len(self._types):
            raise ValueError(
                f"{self._prefix!r} expects {len(self._types)} values, "
                f"got {len(values)}"
            )
        parts: List[str] = [self._prefix]
        for (t, v) in zip(self._types, values):
            if not isinstance(v, t):
                # bool is a subclass of int; keep strictness
                raise TypeError(
                    f"expected {t.__name__}, got {type(v).__name__} "
                    f"for {self._prefix!r}"
                )
            parts.append(_TYPE_TAG[t])
            if t is bytes:
                parts.append(base64.urlsafe_b64encode(v).decode("ascii"))
            elif t is bool:
                parts.append("1" if v else "0")
            elif t is float:
                parts.append(f"{v!r}")
            else:
                parts.append(str(v))
        payload = _SEP.join(parts)
        if len(payload.encode("utf-8")) > self._max_len:
            raise ValueError(
                f"packed payload {len(payload.encode('utf-8'))} bytes exceeds "
                f"Telegram's {self._max_len}-byte limit"
            )
        return payload

    def unpack(self, data: str) -> Tuple[Any, ...]:
        """
        Decode a callback_query.data string into declared types.
        Raises ``CallbackDataInvalid`` if the prefix or shape does not match.
        """
        parts = data.split(_SEP)
        expected = 1 + len(self._types) * 2
        if len(parts) != expected or parts[0] != self._prefix:
            raise CallbackDataInvalid(
                f"{data!r} is not a valid {self._prefix!r} payload "
                f"(expected {expected} parts)"
            )
        out = []
        for i in range(len(self._types)):
            tag, raw = parts[1 + i * 2], parts[2 + i * 2]
            t = _TYPE_FROM_TAG.get(tag)
            if t is None:
                raise CallbackDataInvalid(f"unknown type tag {tag!r}")
            if t is str:
                out.append(raw)
            elif t is int:
                try:
                    out.append(int(raw))
                except ValueError:
                    raise CallbackDataInvalid(f"invalid int {raw!r}")
            elif t is float:
                try:
                    out.append(float(raw))
                except ValueError:
                    raise CallbackDataInvalid(f"invalid float {raw!r}")
            elif t is bool:
                out.append(raw == "1")
            else:  # bytes
                try:
                    out.append(base64.urlsafe_b64decode(raw + "=" * (-len(raw) % 4)))
                except ValueError:
                    raise CallbackDataInvalid(f"invalid bytes {raw!r}")
        return tuple(out)

    def filter(self) -> "_CallbackDataFilter":
        """Return a filter-like matcher for use with the router."""
        return _CallbackDataFilter(self)


class _CallbackDataFilter:
    """Matches callback_query.data belonging to this CallbackData instance."""

    __slots__ = ("_data",)

    def __init__(self, data: CallbackData):
        self._data = data

    def matches(self, data: str) -> bool:
        return data.startswith(self._data.prefix + _SEP)

    def unpack(self, data: str):
        return self._data.unpack(data)
