"""
Tests for the v1.2 - v1.4 gap-fills:
- CallbackData pack/unpack (typed callback payloads)
- deep_linking utilities
- testing harness (FakePool + TestClient)
- typed models
- Bot API 2026 methods + 2026 update kinds
- proxy support
"""

import asyncio
import base64
import json

import pytest

from swiftbot import CallbackData, CallbackDataInvalid, SwiftBot
from swiftbot import deep_linking
from swiftbot import models
from swiftbot.connection.pool import HTTPConnectionPool
from swiftbot.exceptions.telegram import TelegramError
from swiftbot.filters import CommandFilter
from swiftbot.storage import MemoryStorage, RedisStorage
from swiftbot.testing import FakePool, TestClient
from swiftbot.types import Message as MessageEvent
from swiftbot.update_types import Update


# ================= CallbackData =================

class CallbackDataTests:
    def test_pack_unpack_str(self):
        nav = CallbackData("nav", str)
        packed = nav.pack("home")
        assert nav.unpack(packed) == ("home",)

    def test_pack_unpack_multiple_types(self):
        cb = CallbackData("confirm", str, int, bool, float)
        packed = cb.pack("approve", 42, True, 3.14)
        assert cb.unpack(packed) == ("approve", 42, True, 3.14)

    def test_bool_false_roundtrip(self):
        cb = CallbackData("t", bool)
        assert cb.unpack(cb.pack(False)) == (False,)

    def test_bytes_roundtrip(self):
        cb = CallbackData("b", bytes)
        payload = b"hello"
        assert cb.unpack(cb.pack(payload)) == (payload,)

    def test_wrong_value_count(self):
        cb = CallbackData("x", str, int)
        with pytest.raises(ValueError):
            cb.pack("only-one")

    def test_wrong_value_type(self):
        cb = CallbackData("x", int)
        with pytest.raises(TypeError):
            cb.pack("not-an-int")

    def test_exceeds_64_byte_limit(self):
        cb = CallbackData("x", str)
        with pytest.raises(ValueError, match="limit"):
            cb.pack("a" * 70)

    def test_invalid_prefix(self):
        with pytest.raises(ValueError):
            CallbackData("bad prefix!", str)
        with pytest.raises(ValueError):
            CallbackData("", str)
        with pytest.raises(ValueError):
            CallbackData("a" * 17, str)

    def test_empty_types_rejected(self):
        with pytest.raises(ValueError):
            CallbackData("x")

    def test_unsupported_type_rejected(self):
        with pytest.raises(ValueError):
            CallbackData("x", list)

    def test_prefix_isolation(self):
        a = CallbackData("a", str)
        b = CallbackData("b", str)
        packed = a.pack("shared")
        with pytest.raises(CallbackDataInvalid):
            b.unpack(packed)

    def test_corrupt_payload(self):
        cb = CallbackData("cb", str, int)
        with pytest.raises(CallbackDataInvalid):
            cb.unpack("cb:s:broken")

    def test_foreign_prefix_rejected(self):
        a = CallbackData("a", str)
        with pytest.raises(CallbackDataInvalid):
            a.unpack("other:s:value")

    def test_filter_matches_and_unpacks(self):
        cb = CallbackData("nav", str)
        f = cb.filter()
        assert f.matches("nav:s:home")
        assert not f.matches("other:s:home")
        assert f.unpack("nav:s:home") == ("home",)


# ================= Deep linking =================

class DeepLinkingTests:
    def test_create_start_link_username_string(self):
        link = deep_linking.create_start_link("MyBot", "ref_123")
        assert link == "https://t.me/MyBot?start=ref_123"

    def test_create_start_link_at_prefix_stripped(self):
        link = deep_linking.create_start_link("@MyBot", "ref_123")
        assert link == "https://t.me/MyBot?start=ref_123"

    def test_create_start_link_get_me_dict(self):
        link = deep_linking.create_start_link(
            {"username": "MyBot", "id": 1, "is_bot": True, "first_name": "b"},
            "abc",
        )
        assert "t.me/MyBot?start=abc" in link

    def test_private_startgroup_link(self):
        link = deep_linking.create_start_link("MyBot", "secret", private=True)
        assert link == "https://t.me/MyBot?startgroup=secret"

    def test_invalid_payload_chars(self):
        with pytest.raises(ValueError):
            deep_linking.create_start_link("MyBot", "has space")

    def test_payload_too_long(self):
        with pytest.raises(ValueError):
            deep_linking.create_start_link("MyBot", "x" * 65)

    def test_encode_decode_string_roundtrip(self):
        token = deep_linking.encode_payload("hello world/+")
        assert deep_linking.decode_payload(token) == "hello world/+"

    def test_encode_decode_dict_roundtrip(self):
        payload = {"user": 42, "ref": "campaign", "ts": 1}
        token = deep_linking.encode_payload(payload)
        assert len(token) <= 64
        assert deep_linking.decode_payload(token) == payload

    def test_dict_payload_sorted_keys(self):
        token = deep_linking.encode_payload({"z": 1, "a": 2})
        raw = token + "=" * (-len(token) % 4)
        decoded_json = json.loads(base64.urlsafe_b64decode(raw))
        assert list(decoded_json.keys()) == ["a", "z"]

    def test_encoded_payload_too_long(self):
        with pytest.raises(ValueError, match="64"):
            deep_linking.encode_payload("x" * 50)

    def test_decode_invalid_token(self):
        with pytest.raises(ValueError):
            deep_linking.decode_payload("a" * 65)
        with pytest.raises(ValueError):
            deep_linking.decode_payload("!invalid~")

    def test_parse_start_param(self):
        assert deep_linking.parse_start_param("ref_123") == "ref_123"
        assert deep_linking.parse_start_param("ref_123 extra-ignored") == "ref_123"
        assert deep_linking.parse_start_param("") is None
        assert deep_linking.parse_start_param(None) is None

    def test_custom_parameter(self):
        link = deep_linking.create_start_link_custom("MyBot", "abc", "game")
        assert link == "https://t.me/MyBot?game=abc"


# ================= Testing harness =================

class FakePoolTests:
    @pytest.mark.asyncio
    async def test_record_outgoing_calls(self):
        pool = FakePool()
        result = await pool.post("https://api.telegram.org/botfake/sendMessage",
                                 json={"chat_id": 5, "text": "hi"})
        assert result.json()["result"] is True
        assert len(pool.outgoing) == 1
        assert pool.outgoing[0]["method"] == "sendMessage"
        assert pool.outgoing[0]["params"]["text"] == "hi"

    @pytest.mark.asyncio
    async def test_script_response(self):
        pool = FakePool()
        pool.script("getMe", result={"id": 11, "is_bot": True, "first_name": "T"})
        result = await pool.post("https://x/getMe", json={})
        assert result.json()["result"]["first_name"] == "T"

    @pytest.mark.asyncio
    async def test_scripted_error_raised(self):
        from swiftbot.api.telegram import TelegramAPI
        pool = FakePool()
        pool.script("send", error={"ok": False, "error_code": 400,
                                   "description": "Bad Request: chat not found"})
        api = TelegramAPI("fake:TOKEN", pool)
        with pytest.raises(TelegramError) as exc_info:
            await api._request("send")
        assert exc_info.value.error_code == 400
        # The fake still records every call, scripted errors included
        assert pool.error_count == 1

    @pytest.mark.asyncio
    async def test_hook_called_with_params(self):
        seen = {}

        async def hook(method, params):
            seen["call"] = (method, params)
            return {"message_id": 99}

        pool = FakePool()
        pool.hook = hook
        await pool.post("https://x/setWebhook", json={"url": "https://y"})
        assert seen["call"] == ("setWebhook", {"url": "https://y"})


class TestClientTests:
    @pytest.mark.asyncio
    async def test_send_message_records_and_returns(self):
        bot = SwiftBot("fake:TOKEN")
        async with TestClient(bot) as tc:
            # Script a realistic sendMessage payload so the call returns the
            # full message object the real Telegram API would return.
            tc.pool.script("sendMessage", result={"message_id": 1, "text": "hi",
                                                   "date": 1,
                                                   "chat": {"id": 1, "type": "private"}})
            msg = await tc.send_message(chat_id=1, text="hi")
            assert msg["text"] == "hi"
            assert tc.outgoing[-1]["params"]["chat_id"] == 1

    @pytest.mark.asyncio
    async def test_send_update_routes_through_handler(self):
        called = {}
        bot = SwiftBot("fake:TOKEN")

        @bot.on(MessageEvent(filters=CommandFilter("start")))
        async def start(ctx):
            called["handler"] = True
            await ctx.reply("welcome")

        async with TestClient(bot) as tc:
            await tc.send_update({
                "update_id": 1,
                "message": {
                    "message_id": 10, "date": 1,
                    "chat": {"id": 5, "type": "private"},
                    "from": {"id": 7, "is_bot": False, "first_name": "U"},
                    "text": "/start",
                },
            })

        assert called.get("handler") is True
        # The handler replied "welcome" — find the sendMessage call in the
        # fake pool's recorded outgoing traffic.
        assert any(o["method"] == "sendMessage" and o["params"].get("text") == "welcome"
                   for o in tc.outgoing)

    @pytest.mark.asyncio
    async def test_send_update_no_handler_no_crash(self):
        bot = SwiftBot("fake:TOKEN")

        async with TestClient(bot) as tc:
            await tc.send_update({
                "update_id": 9,
                "message": {
                    "message_id": 1, "date": 1,
                    "chat": {"id": 5, "type": "private"},
                    "from": {"id": 7, "is_bot": False, "first_name": "U"},
                    "text": "/unknown",
                },
            })
        # Nothing crashed; no outgoing calls were made
        assert len(tc.outgoing) == 0


# ================= Typed models =================

class ModelTests:
    def test_user_from_dict(self):
        u = models.User.from_dict(
            {"id": 5, "is_bot": False, "first_name": "Ada", "username": "ada"}
        )
        assert u.id == 5 and u.username == "ada"

    def test_user_none_guard(self):
        assert models.User.from_dict(None) is None

    def test_chat_from_dict(self):
        c = models.Chat.from_dict({"id": 9, "type": "supergroup", "title": "G"})
        assert c.title == "G" and c.is_supergroup is True

    def test_message_from_dict(self):
        m = models.Message.from_dict(
            {
                "message_id": 1, "date": 2,
                "chat": {"id": 5, "type": "private"},
                "from": {"id": 7, "is_bot": False, "first_name": "U"},
                "text": "hi",
            }
        )
        assert m.text == "hi"
        assert m.chat.id == 5
        assert m.from_user.first_name == "U"
        assert m.chat.user is None  # private chat has no chat-level user

    def test_message_preserves_unknown_fields_in_raw(self):
        m = models.Message.from_dict(
            {
                "message_id": 1, "date": 2,
                "chat": {"id": 5, "type": "private"},
                "custom_future_field": 42,
            }
        )
        assert m.raw["custom_future_field"] == 42

    def test_message_reply_to_recursion_guarded(self):
        data = {
            "message_id": 1, "date": 2,
            "chat": {"id": 5, "type": "private"},
            "from": {"id": 7, "is_bot": False, "first_name": "U"},
            "reply_to_message": {"message_id": 0, "date": 1,
                                 "chat": {"id": 5, "type": "private"}},
        }
        m = models.Message.from_dict(data)
        assert m.reply_to_message is not None
        assert m.reply_to_message.message_id == 0

    def test_callback_query(self):
        cq = models.CallbackQuery.from_dict(
            {"id": "q", "from": {"id": 1, "is_bot": False, "first_name": "U"},
             "chat_instance": "c", "data": "nav:s:home"}
        )
        assert cq.data == "nav:s:home"

    def test_inline_keyboard_to_dict(self):
        mk = models.InlineKeyboardMarkup(
            inline_keyboard=[[{"text": "OK", "callback_data": "x"}]]
        )
        d = mk.to_dict()
        assert d["inline_keyboard"][0][0]["callback_data"] == "x"

    def test_document(self):
        d = models.Document.from_dict(
            {"file_id": "f", "file_name": "a.txt", "file_size": 7})
        assert d.file_name == "a.txt"


# ================= Bot API 2026 methods =================

class BotAPI2026Tests:
    @pytest.mark.asyncio
    async def test_2026_methods_callable_with_params(self):
        pool = FakePool()
        from swiftbot.api.telegram import TelegramAPI
        api = TelegramAPI("fake:TOKEN", pool)
        await api.get_managed_bot_token(managed_bot_token_request_id="r1")
        assert pool.outgoing[-1]["method"] == "getManagedBotToken"
        await api.replace_managed_bot_token(managed_bot_token_request_id="r2")
        assert pool.outgoing[-1]["method"] == "replaceManagedBotToken"
        await api.answer_guest_query(guest_query_id="g1", message={"text": "hi"})
        call = pool.outgoing[-1]
        assert call["method"] == "answerGuestQuery"
        assert call["params"]["message"]["text"] == "hi"
        await api.delete_all_message_reactions(chat_id=1, message_id=5)
        assert pool.outgoing[-1]["method"] == "deleteAllMessageReactions"
        await api.send_rich_message(chat_id=1, rich_message={"blocks": []})
        assert pool.outgoing[-1]["method"] == "sendRichMessage"
        await api.send_rich_message_draft(chat_id=1, rich_message={"blocks": []})
        assert pool.outgoing[-1]["method"] == "sendRichMessageDraft"
        await api.edit_message_text_rich(
            rich_message={"blocks": []}, chat_id=1, message_id=2
        )
        assert pool.outgoing[-1]["method"] == "editMessageText"
        await api.delete_ephemeral_message(chat_id=1, message_id=3)
        assert pool.outgoing[-1]["method"] == "deleteEphemeralMessage"
        await api.answer_chat_join_request_query(chat_id=1, user_id=2)
        assert pool.outgoing[-1]["method"] == "answerChatJoinRequestQuery"
        await api.send_chat_join_request_web_app(chat_id=1, user_id=2)
        assert pool.outgoing[-1]["method"] == "sendChatJoinRequestWebApp"

    def test_update_parses_2026_kinds(self):
        u = Update.from_dict({
            "update_id": 1,
            "managed_bot_created": {"managed_bot": {}},
        })
        assert u.get_update_type() == "managed_bot_created"
        assert u.managed_bot_created is not None

        u2 = Update.from_dict({
            "update_id": 2,
            "guest_message": {
                "message_id": 1, "date": 1,
                "chat": {"id": 5, "type": "private"},
                "from": {"id": 7, "is_bot": False, "first_name": "U"},
                "text": "hello",
            },
        })
        assert u2.get_update_type() == "guest_message"
        assert u2.guest_message.text == "hello"

        u3 = Update.from_dict({
            "update_id": 3, "purchase": {"transaction_id": "t1"},
        })
        assert u3.get_update_type() == "purchase"


# ================= Proxy support =================

class ProxyTests:
    def test_proxy_propagated_to_pool(self):
        pool = HTTPConnectionPool(proxy="http://proxy:3128")
        assert pool.proxy == "http://proxy:3128"

    def test_pool_without_proxy(self):
        assert HTTPConnectionPool().proxy is None

    @pytest.mark.asyncio
    async def test_bot_accepts_proxy(self):
        bot = SwiftBot("fake:TOKEN", proxy="http://proxy:8080")
        assert bot.api.pool.proxy == "http://proxy:8080"
        await bot.api.pool.close()


# ================= Storage =================

class StorageV14Tests:
    @pytest.mark.asyncio
    async def test_redis_storage_unavailable_without_redis(self):
        store = RedisStorage()
        with pytest.raises(Exception):
            await store.get("user", "key")

    @pytest.mark.asyncio
    async def test_memory_storage_unchanged(self):
        store = MemoryStorage()
        await store.set("user", "key", {"a": 1})
        assert await store.get("user", "key") == {"a": 1}
