"""
SwiftBot v1.6 — new framework features test suite.

Covers:
- Dialogue: state-carrying conversation FSM (transitions, data carry,
  illegal transitions, timeouts, persistence, step_forward)
- Scopes: predicate-guarded middleware chains
- Throttle: outbound rate-limiting transformer (token bucket)
- Reply: fluent reply builder
- Fallback + unknown-command handlers
"""

import asyncio
import sys
import os
import pytest
import time

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from swiftbot import SwiftBot, Dialogue, DialogueTransitionError, Scope, Reply, throttle, F
from swiftbot.commands import BotCommands, CommandsMiddleware
from swiftbot.testing import FakePool, TestClient
from swiftbot.storage import MemoryStorage
from swiftbot.types import Message
from swiftbot.update_types import Update


def _make_bot():
    return SwiftBot(token="123456:TEST-TOKEN")


def _message_update(text: str, chat_id: int = 1, user_id: int = 7,
                    chat_type: str = "private", update_id: int = 1) -> dict:
    return {
        "update_id": update_id,
        "message": {
            "message_id": 1,
            "date": 1000,
            "chat": {"id": chat_id, "type": chat_type},
            "from": {"id": user_id, "is_bot": False, "first_name": "Tester"},
            "text": text,
        },
    }


# ======================================================================
# Dialogue — state-carrying conversation FSM
# ======================================================================

class DialogueTests:

    @pytest.mark.asyncio
    async def test_state_registration(self):
        dlg = Dialogue("survey", MemoryStorage())

        @dlg.state("ask_name", next=["ask_age"])
        async def ask_name(ctx, prev=None):
            await ctx.reply("Name?")
            return Dialogue.next("ask_age")

        @dlg.state("ask_age", next=["done"])
        async def ask_age(ctx, prev=None):
            await ctx.reply("Age?")
            return Dialogue.next("done", carry="done-now")

        @dlg.finish
        async def done(ctx, prev=None):
            await ctx.reply(f"carry={prev}")
            return Dialogue.end

        assert "ask_name" in repr(dlg)
        assert "done" in dlg._states or dlg._finish_fn is not None

    @pytest.mark.asyncio
    async def test_illegal_transition_raises(self):
        bot = _make_bot()
        dlg = bot.dialogue("bad")
        ctx = _make_ctx(bot, "x")

        @dlg.state("a", next=["b"])
        async def a(ctx, prev=None):
            return Dialogue.next("c")  # not allowed

        dlg._states["c"] = {"fn": a, "next": None, "timeout": None}
        await dlg._set_state(ctx, "a", None)
        with pytest.raises(DialogueTransitionError):
            await dlg.step_forward(ctx, answer="x")

    @pytest.mark.asyncio
    async def test_unknown_target_state_raises(self):
        bot = _make_bot()
        dlg = bot.dialogue("u")
        ctx = _make_ctx(bot, "x")

        @dlg.state("a", next=None)
        async def a(ctx, prev=None):
            return Dialogue.next("ghost")

        await dlg._set_state(ctx, "a", None)
        with pytest.raises(DialogueTransitionError):
            await dlg.step_forward(ctx, answer="x")

    @pytest.mark.asyncio
    async def test_persistence(self):
        bot = _make_bot()
        store = MemoryStorage()
        dlg = bot.dialogue("survey", storage=store)
        ctx = _make_ctx(bot, "x")

        @dlg.state("ask_name", next=["ask_age"])
        async def ask_name(ctx, prev=None):
            return Dialogue.next("ask_age", carry=prev)

        @dlg.state("ask_age")
        async def ask_age(ctx, prev=None):
            return Dialogue.end

        # enter
        await dlg.enter(ctx, "ask_name")
        assert await dlg.current(ctx) == "ask_name"
        # persist + recover in a new Dialogue instance
        dlg2 = Dialogue("survey", store)
        dlg2._states = dlg._states
        assert await dlg2.current(ctx) == "ask_name"

    @pytest.mark.asyncio
    async def test_full_round_trip_with_carry(self):
        """The bot drives a dialogue through three updates and the carry
        value flows from the first state's answer into the last."""
        seen = []
        bot = _make_bot()
        dlg = bot.dialogue("survey")

        @dlg.state("ask_name", next=["ask_age"])
        async def ask_name(ctx, prev=None):
            seen.append(("ask_name", prev))
            return Dialogue.next("ask_age", carry=ctx.text)

        @dlg.state("ask_age")
        async def ask_age(ctx, prev=None):
            seen.append(("ask_age", prev))
            return Dialogue.end

        ctx1 = _make_ctx(bot, "Arjun")
        await dlg.enter(ctx1, "ask_name")
        assert seen == [("ask_name", None)]
        assert await dlg.current(ctx1) == "ask_name"

        # second update advances: state receives ctx.text as answer
        ok = await dlg.step_forward(ctx1, answer="Arjun")
        assert ok is True, "step_forward did not advance"
        assert seen[-1] == ("ask_age", "Arjun")
        assert await dlg.current(ctx1) is None, "dialogue did not end"

    @pytest.mark.asyncio
    async def test_timeout_exits(self):
        calls = []
        bot = _make_bot()
        dlg = bot.dialogue("t")
        dlg._timeout = 0
        ctx = _make_ctx(bot, "x")

        @dlg.state("wait", next=[])
        async def wait(ctx, prev=None):
            return Dialogue.next("wait")

        @dlg.on_timeout
        async def expired(ctx, state):
            calls.append(("expired", state))

        # seed state with a stale entry timestamp
        await dlg._storage.set("swiftbot:dialogue:t", "7:at", time.monotonic() - 10)
        await dlg._storage.set("swiftbot:dialogue:t", "7", ("wait", None))
        await dlg.step_forward(ctx, answer="x")
        assert calls == [("expired", "wait")]
        assert await dlg.current(ctx) is None

    @pytest.mark.asyncio
    async def test_update_routing_gives_active_dialogue_priority(self):
        """An update for a user with an active dialogue is consumed by the
        dialogue before any router handler can see it."""
        consumed = []
        bot = _make_bot()
        dlg = bot.dialogue("survey")

        @dlg.state("ask_age")
        async def ask_age(ctx, prev=None):
            consumed.append(prev)
            return Dialogue.end

        @bot.on(Message())
        async def regular(ctx):
            consumed.append("regular")

        tc = TestClient(bot)
        async with tc:
            # enter the dialogue within the running client
            ctx1 = _make_ctx(bot, "12")
            await dlg.enter(ctx1, "ask_age")
            # send a plain message — the dialogue should consume it
            await tc.send_update(_message_update("27", update_id=9))
        assert "regular" not in consumed
        # The first entry comes from ``dlg.enter`` running the ask_age step;
        # the second comes from the routed update advancing it with "27".
        assert consumed == [None, "27"]

    @pytest.mark.asyncio
    async def test_exit_clears_state(self):
        bot = _make_bot()
        dlg = bot.dialogue("e")
        ctx = _make_ctx(bot, "x")

        @dlg.state("s")
        async def s(ctx, prev=None):
            return Dialogue.next("s")

        await dlg.enter(ctx, "s")
        assert await dlg.current(ctx) == "s"
        await dlg.exit(ctx)
        assert await dlg.current(ctx) is None


def _make_ctx(bot, text):
    u = Update.from_dict(_message_update(text))
    obj = u.get_update_object()
    ctx = Context(bot, u, obj, None)
    return ctx


from swiftbot.context import Context  # noqa: E402 (after _make_ctx usage for clarity)


# ======================================================================
# Scopes — predicate-guarded middleware chains
# ======================================================================

class ScopeTests:

    @pytest.mark.asyncio
    async def test_scope_runs_when_predicate_matches(self):
        seen = []

        async def track(ctx, next_handler):
            seen.append("scoped")
            await next_handler()

        scope = Scope(lambda upd: upd.get("message", {}).get("chat", {}).get("type") == "private")
        scope.use(track)

        bot = _make_bot()
        bot._scopes.append(scope)

        ctx = _make_ctx(bot, "hi")
        await scope.on_update(ctx, bot._noop)
        assert seen == ["scoped"], f"predicate did not match raw update {ctx.update.raw}"

    @pytest.mark.asyncio
    async def test_scope_skipped_when_predicate_fails(self):
        seen = []

        async def track(ctx, next_handler):
            seen.append("scoped")
            await next_handler()

        scope = Scope(lambda upd: False)
        scope.use(track)

        bot = _make_bot()
        ctx = _make_ctx(bot, "hi")
        await scope.on_update(ctx, bot._noop)
        assert seen == []

    @pytest.mark.asyncio
    async def test_scope_broken_predicate_never_blocks(self):
        scope = Scope(lambda upd: 1 / 0)
        scope.use(lambda ctx, nh: nh())
        bot = _make_bot()
        ctx = _make_ctx(bot, "hi")
        # must not raise
        await scope.on_update(ctx, bot._noop)

    @pytest.mark.asyncio
    async def test_bots_scope_method_registers_and_runs(self):
        seen = []

        async def track(ctx, next_handler):
            seen.append("scoped")
            await next_handler()

        bot = _make_bot()
        bot.scope(lambda upd: True).use(track)

        tc = TestClient(bot)
        async with tc:
            await tc.send_update(_message_update("hello"))
        assert seen == ["scoped"]


# ======================================================================
# Throttle — outbound rate limiting
# ======================================================================

class ThrottleTests:

    @pytest.mark.asyncio
    async def test_allows_within_rate(self):
        t = throttle(max_per_second=100.0, burst=10)
        for _ in range(8):
            assert await t("sendMessage", {"chat_id": 1}) == {"chat_id": 1}

    @pytest.mark.asyncio
    async def test_delays_excess_calls(self):
        t = throttle(max_per_second=10.0, burst=2)
        # burst of 2 tokens first
        await t("sendMessage", {})
        await t("sendMessage", {})
        # third call must wait for a token
        start = time.monotonic()
        await t("sendMessage", {})
        waited = time.monotonic() - start
        assert waited >= 0.05, f"throttle did not delay: {waited}s"

    @pytest.mark.asyncio
    async def test_per_chat_limiting(self):
        t = throttle(max_per_second=1000.0, per_chat=0.2)
        start = time.monotonic()
        await t("sendMessage", {"chat_id": 1})
        await t("sendMessage", {"chat_id": 1})
        waited = time.monotonic() - start
        assert waited >= 0.15, "per-chat rate not enforced"

    @pytest.mark.asyncio
    async def test_invalid_rate_rejected(self):
        with pytest.raises(ValueError):
            throttle(max_per_second=0)

    @pytest.mark.asyncio
    async def test_composes_as_api_transformer(self):
        bot = _make_bot()
        bot.api.config.use(throttle(max_per_second=1000.0))
        tc = TestClient(bot)
        async with tc:
            # api call must still go through (slower, but fine)
            await bot.api.send_message(chat_id=1, text="hi")
        assert any(r["method"] == "sendMessage" for r in tc.outgoing)


# ======================================================================
# Reply — fluent builder
# ======================================================================

class ReplyTests:

    @pytest.mark.asyncio
    async def test_text_reply_sends(self):
        bot = _make_bot()
        fake = FakePool()
        bot.api.pool = fake
        bot.connection_pool = fake
        ctx = _make_ctx(bot, "trigger")
        await Reply(ctx).text("Hello").silent().send()
        records = [r for r in bot.api.pool.outgoing if r["method"] == "sendMessage"]
        assert records, "sendMessage was not called"
        rec = records[-1]
        assert rec["params"]["text"] == "Hello"
        assert rec["params"]["disable_notification"] is True

    @pytest.mark.asyncio
    async def test_builder_options_apply(self):
        bot = _make_bot()
        bot.api.pool = FakePool()
        bot.connection_pool = bot.api.pool
        ctx = _make_ctx(bot, "t")
        await Reply(ctx).text("x").protect().parse_mode("HTML").reply_to(42).send()
        rec = [r for r in bot.api.pool.outgoing if r["method"] == "sendMessage"][-1]["params"]
        assert rec["protect_content"] is True
        assert rec["parse_mode"] == "HTML"
        assert rec["reply_parameters"]["message_id"] == 42

    @pytest.mark.asyncio
    async def test_markup_applies_to_dict(self):
        bot = _make_bot()
        bot.api.pool = FakePool()
        bot.connection_pool = bot.api.pool
        ctx = _make_ctx(bot, "t")
        from swiftbot.button import InlineKeyboard

        from swiftbot.button import InlineButton
        kb = InlineKeyboard([]).add_row(InlineButton("Go", callback_data="nav:1"))
        await Reply(ctx).text("ok").markup(kb).send()
        rec = [r for r in bot.api.pool.outgoing if r["method"] == "sendMessage"][-1]["params"]
        assert "reply_markup" in rec

    @pytest.mark.asyncio
    async def test_photo_build(self):
        bot = _make_bot()
        bot.api.pool = FakePool()
        bot.connection_pool = bot.api.pool
        ctx = _make_ctx(bot, "t")
        await Reply(ctx).photo("pic.jpg").caption("Look").send()
        rec = [r for r in bot.api.pool.outgoing if r["method"] == "sendPhoto"][-1]["params"]
        assert rec["photo"] == "pic.jpg"
        assert rec["caption"] == "Look"


# ======================================================================
# Fallback + unknown-command handlers
# ======================================================================

class FallbackTests:

    @pytest.mark.asyncio
    async def test_fallback_runs_on_no_match(self):
        handled = []

        bot = _make_bot()

        @bot.fallback
        async def not_found(ctx):
            handled.append(ctx.text)

        tc = TestClient(bot)
        async with tc:
            await tc.send_update(_message_update("gibberish with no handlers"))
        assert handled == ["gibberish with no handlers"]

    @pytest.mark.asyncio
    async def test_unknown_command_handler(self):
        handled = []

        class Cmd(BotCommands):
            start = "/start"

        bot = _make_bot()
        bot.use(CommandsMiddleware(Cmd))

        @bot.on_unknown_command
        async def unknown(ctx):
            handled.append(ctx.text)

        tc = TestClient(bot)
        async with tc:
            # /help is not in the spec → unknown command
            await tc.send_update(_message_update("/help", update_id=10))
            # /start is in the spec → must NOT hit the unknown handler
            await tc.send_update(_message_update("/start", update_id=11))
        assert handled == ["/help"], f"handled={handled}"

    @pytest.mark.asyncio
    async def test_no_fallback_silent_drop(self):
        bot = _make_bot()
        tc = TestClient(bot)
        async with tc:
            await tc.send_update(_message_update("nothing matches"))
        # no exception, no crash
        assert True
