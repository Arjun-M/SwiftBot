import pytest

from swiftbot import SwiftBot
from swiftbot.api.telegram import InputFile
from swiftbot.models import RichBlock, RichMessage, RichText
from swiftbot.testing import FakePool
from swiftbot.update_types import Update


def make_bot():
    bot = SwiftBot("0000000000:TEST")
    pool = FakePool()
    bot.api.pool = pool
    return bot, pool


@pytest.mark.asyncio
async def test_send_message_current_and_legacy_parameters():
    bot, pool = make_bot()

    await bot.api.send_message(
        chat_id=42,
        text="hello",
        receiver_user_id=7,
        callback_query_id="cb-1",
        message_effect_id="effect",
        direct_messages_topic_id=3,
        allow_paid_broadcast=True,
    )
    record = pool.outgoing[-1]
    assert record["method"] == "sendMessage"
    assert record["params"]["receiver_user_id"] == 7
    assert record["params"]["callback_query_id"] == "cb-1"
    assert record["params"]["allow_paid_broadcast"] is True

    await bot.send_message(
        chat_id=42,
        text="legacy",
        reply_to_message_id=9,
        allow_sending_without_reply=True,
        disable_web_page_preview=True,
    )
    record = pool.outgoing[-1]
    assert record["params"]["reply_parameters"] == {
        "message_id": 9,
        "allow_sending_without_reply": True,
    }
    assert record["params"]["link_preview_options"] == {"is_disabled": True}


@pytest.mark.asyncio
async def test_send_poll_uses_current_multi_answer_parameter():
    bot, pool = make_bot()
    await bot.api.send_poll(
        chat_id=42,
        question="Choose",
        options=["a", "b"],
        correct_option_id=1,
        allows_revoting=True,
        shuffle_options=True,
        description="desc",
        country_codes=["US"],
        members_only=True,
    )
    params = pool.outgoing[-1]["params"]
    assert params["correct_option_ids"] == [1]
    assert "correct_option_id" not in params
    assert params["allows_revoting"] is True
    assert params["description"] == "desc"


@pytest.mark.asyncio
async def test_rich_message_and_multipart_serialization():
    bot, pool = make_bot()
    rich = RichMessage(
        text=RichText(type="bold", text="hello"),
        blocks=[RichBlock(type="paragraph", fields={"text": "body"})],
    )
    await bot.api.send_rich_message(chat_id=42, rich_message=rich)
    params = pool.outgoing[-1]["params"]
    assert params["rich_message"]["text"]["type"] == "bold"
    assert params["rich_message"]["blocks"][0]["type"] == "paragraph"

    await bot.api.send_document(
        chat_id=42,
        document=InputFile(b"data", filename="test.txt"),
        caption="file",
    )
    record = pool.outgoing[-1]
    assert record["method"] == "sendDocument"
    assert record["params"]["caption"] == "file"
    assert record["files"] == ["document"]


@pytest.mark.asyncio
async def test_current_endpoint_wrappers_emit_official_method_names():
    bot, pool = make_bot()
    calls = [
        (bot.api.send_chat_action(42, "typing"), "sendChatAction"),
        (bot.api.send_message_draft(42, 1, "draft"), "sendMessageDraft"),
        (bot.api.send_paid_media(42, 10, [{"type": "photo", "media": "x"}]), "sendPaidMedia"),
        (bot.api.send_checklist(42, {"title": {}, "tasks": []}), "sendChecklist"),
        (bot.api.set_message_reaction(42, 1, []), "setMessageReaction"),
        (bot.api.delete_message_reaction(42, 1, user_id=7), "deleteMessageReaction"),
        (bot.api.ban_chat_sender_chat(42, 7), "banChatSenderChat"),
        (bot.api.unban_chat_sender_chat(42, 7), "unbanChatSenderChat"),
        (bot.api.get_business_connection("bc"), "getBusinessConnection"),
        (bot.api.get_user_chat_boosts(42, 7), "getUserChatBoosts"),
        (bot.api.get_user_personal_chat_messages(7), "getUserPersonalChatMessages"),
        (bot.api.get_user_profile_audios(7), "getUserProfileAudios"),
    ]
    for awaitable, method in calls:
        await awaitable
        assert pool.outgoing[-1]["method"] == method


@pytest.mark.parametrize(
    "field",
    [
        "business_connection",
        "message_reaction",
        "message_reaction_count",
        "purchased_paid_media",
        "chat_boost",
        "removed_chat_boost",
        "managed_bot",
        "subscription",
    ],
)
def test_current_update_fields_are_typed_and_routable(field):
    update = Update.from_dict({"update_id": 1, field: {"id": "x"}})
    assert update.get_update_type() == field
    assert update.get_update_object() == {"id": "x"}
    assert update.raw[field] == {"id": "x"}
