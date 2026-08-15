"""
Tests for update parsing, recursion guard, command routing and typed errors.
"""

import sys
import pytest
from swiftbot.update_types import Update, Message, Chat, User
from swiftbot.router import CommandRouter, CommandTrie
from swiftbot.types import Message as MessageEvent, CallbackQuery
from swiftbot.context import Context
from swiftbot.exceptions import (
    TelegramError, BadRequest, Unauthorized, Forbidden,
    UserNotFound, ChatNotFound, TooManyRequests, MigrateToChat,
)


# ---------- Update parsing ----------

def make_message(text=None, reply_to=None, user_id=1):
    return {
        "message_id": 1,
        "date": 1,
        "chat": {"id": 1, "type": "private"},
        "from": {"id": user_id, "is_bot": False, "first_name": "A"},
        **({"text": text} if text else {}),
        **({"reply_to_message": reply_to} if reply_to else {}),
    }


def test_update_from_dict_basic():
    u = Update.from_dict({"update_id": 7, "message": make_message(text="hi")})
    assert u.update_id == 7
    assert u.message is not None
    assert u.message.text == "hi"


def test_message_recursion_guard_shallow():
    reply = make_message(reply_to=make_message())
    m = Message.from_dict(reply)
    assert m.reply_to_message is not None
    assert m.reply_to_message.reply_to_message is None


def test_message_recursion_guard_deep_payload_rejected_under_low_limit():
    """A crafted deeply nested payload must not crash the parser."""
    sys.setrecursionlimit(250)
    try:
        node = {"message_id": 0, "date": 0,
                "chat": {"id": 1, "type": "private"},
                "from": {"id": 1, "is_bot": False, "first_name": "A"}}
        for _ in range(400):
            node = make_message(reply_to=node)
        # Must not raise RecursionError; deep chains are truncated instead
        m = Message.from_dict(node)
        assert m is not None
    finally:
        sys.setrecursionlimit(1000)


def test_chat_pinned_message_parsed():
    c = Chat.from_dict({
        "id": 2, "type": "group",
        "pinned_message": make_message(text="pinned"),
    })
    assert c.pinned_message is not None
    assert c.pinned_message.text == "pinned"


def test_from_dict_none_returns_none():
    assert Update.from_dict(None) is None
    assert Message.from_dict(None) is None


# ---------- Trie routing ----------

def test_trie_lookup():
    trie = CommandTrie()
    called = []
    trie.insert("/start", lambda: called.append(1), None)
    trie.insert("/help", lambda: called.append(2), None)

    handler, _ = trie.search("/start arg")
    assert handler is not None
    handler()
    assert called == [1]
    assert trie.search("/missing") is None
    # @bot mentions stripped
    assert trie.search("/start@SomeBot") is not None
    assert trie.search("/HELP") is not None  # case-insensitive


def test_router_trie_fast_path():
    router = CommandRouter()
    hit = None

    async def handler(ctx):
        pass

    router.add_handler(MessageEvent(text="/start"), handler)
    # Build a minimal object that walks the trie fast path
    from types import SimpleNamespace
    obj = SimpleNamespace(text="/start")

    loop_handler, match, event = None, None, None

    @pytest.mark.asyncio
    def _run():
        pass  # route() is async, covered in test_router_trie_async

    import asyncio

    h, m, e = asyncio.run(router.route(obj, "message"))
    assert h is handler
    assert m is None


@pytest.mark.asyncio
async def test_router_trie_async():
    router = CommandRouter()

    async def handler(ctx):
        pass

    router.add_handler(MessageEvent(text="/start"), handler)
    from types import SimpleNamespace
    obj = SimpleNamespace(text="/start")
    h, m, e = await router.route(obj, "message")
    assert h is handler


@pytest.mark.asyncio
async def test_router_callback_data_match():
    router = CommandRouter()

    async def handler(ctx):
        pass

    router.add_handler(CallbackQuery(data="btn:1"), handler)
    from types import SimpleNamespace
    obj = SimpleNamespace(data="btn:1", message=None, from_user=None)
    h, m, e = await router.route(obj, "callback_query")
    assert h is handler


def test_router_invalid_regex_does_not_crash():
    """Registering an invalid regex must not crash add_handler or route()."""
    router = CommandRouter()

    async def handler(ctx):
        pass

    # Invalid pattern is dropped at compile time (logged), handler still
    # registered and matchable as a catch-all
    # Unmatched bracket — a regex the engine can never compile
    router.add_handler(MessageEvent(pattern="abc["), handler)
    from types import SimpleNamespace
    obj = SimpleNamespace(text="anything")

    import asyncio
    h, m, e = asyncio.run(router.route(obj, "message"))
    assert h is handler


# ---------- Filters ----------

def test_command_filter_validation():
    from swiftbot.filters import CommandFilter

    f = CommandFilter(["start", "/help", "About"])
    assert "/start" in f.commands_lower
    assert "/help" in f.commands_lower
    assert "/about" in f.commands_lower

    # Case-insensitive + @bot stripping
    from types import SimpleNamespace
    msg = SimpleNamespace(text="/START@MyBot extra")
    assert f(msg) is True
    assert f(SimpleNamespace(text="not a command")) is False
    assert f(SimpleNamespace(text=None)) is False

    # Empty list raises
    with pytest.raises(ValueError):
        CommandFilter([])


def test_filters_facade():
    from swiftbot.filters import Filters
    f = Filters.command("start")
    assert f({"text": "/start"}) or f(type("M", (), {"text": "/start"})())


# ---------- Typed errors ----------

def test_error_from_response_mapping():
    assert isinstance(
        TelegramError.from_response({"ok": False, "error_code": 400,
                                     "description": "chat not found"}),
        ChatNotFound,
    )
    assert isinstance(
        TelegramError.from_response({"ok": False, "error_code": 401,
                                     "description": "Unauthorized"}),
        Unauthorized,
    )
    assert isinstance(
        TelegramError.from_response({"ok": False, "error_code": 403,
                                     "description": "forbidden: bot was blocked"}),
        Forbidden,
    )
    assert isinstance(
        TelegramError.from_response({"ok": False, "error_code": 400,
                                     "description": "user not found"}),
        UserNotFound,
    )


def test_too_many_requests_retry_after():
    e = TelegramError.from_response({
        "ok": False, "error_code": 429,
        "description": "Too Many Requests: retry after",
        "parameters": {"retry_after": 7},
    })
    assert isinstance(e, TooManyRequests)
    assert e.retry_after == 7
    assert e.error_code == 429


def test_migrate_to_chat():
    e = TelegramError.from_response({
        "ok": False, "error_code": 400,
        "description": "The group has been migrated to a supergroup",
        "parameters": {"migrate_to_chat_id": -100123},
    })
    assert isinstance(e, MigrateToChat)
    assert e.migrate_to_chat_id == -100123


def test_context_creation_from_update():
    """Context must be constructable from a real parsed update."""
    from swiftbot.client import SwiftBot
    from swiftbot.storage import MemoryStorage

    bot = SwiftBot(token="123:ABC")
    bot.storage = MemoryStorage()
    bot._state_manager = None  # plain client without storage wiring test
    update = Update.from_dict({"update_id": 1, "message": make_message(text="/start")})
    ctx = Context(bot, update, update.message, None)
    assert ctx.text == "/start"
    assert ctx.chat.id == 1
    assert ctx.args == []
    assert ctx.user is not None
