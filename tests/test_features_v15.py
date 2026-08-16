"""
SwiftBot v1.5 — standout features test suite.

Covers the features inspired by non-Python Telegram SDKs:
- Pipeline + dependency injection (teloxide dptree)
- Declarative BotCommands (teloxide BotCommands)
- Outbound transformers (grammy api.config.use)
- Composer bundles with error boundaries (grammy)
- Update-kind dispatch routing (grammy bot.route)
- Typed wizards (teloxide Dialogues)
- Graceful shutdown (teloxide enable_ctrlc_handler)
- First-party plugins (spam_deflector, session_limiter, idempotency, whitelist)
- F preset factory + combinators
"""

import asyncio
import sys
import os
import pytest
import time

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from swiftbot import SwiftBot, Pipeline, BotCommands, Composer, Wizard, F, plugins, transformer
from swiftbot.commands import CommandsMiddleware, ParsedCommand
from swiftbot.transformer import Recorder, payload_patch, call_logger, auto_typing, idempotency_guard
from swiftbot.composer import Composer
from swiftbot.plugins import SpamDeflector, SessionLimiter, Idempotency, Whitelist
from swiftbot.storage import MemoryStorage, BaseStorage
from swiftbot.context import Context
from swiftbot.types import Message
from swiftbot.update_types import Update


def _make_bot():
    return SwiftBot(token="123456:TEST-TOKEN")


def _message_update(text: str, chat_id: int = 1, user_id: int = 7) -> dict:
    return {
        "update_id": 1,
        "message": {
            "message_id": 1,
            "date": 1000,
            "chat": {"id": chat_id, "type": "private"},
            "from": {"id": user_id, "is_bot": False, "first_name": "Tester"},
            "text": text,
        },
    }


def _callback_update(data: str) -> dict:
    return {
        "update_id": 2,
        "callback_query": {
            "id": "cb1",
            "from": {"id": 7, "is_bot": False, "first_name": "Tester"},
            "message": {"message_id": 1, "date": 1000,
                        "chat": {"id": 1, "type": "private"}},
            "data": data,
        },
    }


async def _drain(bot, seconds=0.2):
    await asyncio.sleep(seconds)


# ======================================================================
# F preset factory + combinator algebra
# ======================================================================

class FPresetTests:
    def test_f_text_matches(self):
        u = Update.from_dict(_message_update("hello"))
        msg = u.get_update_object()
        assert F.text(msg) is True

    def test_f_combinator_and(self):
        u = Update.from_dict(_message_update("hello"))
        msg = u.get_update_object()
        assert (F.text & F.private)(msg) is True

    def test_f_combinator_not(self):
        u = Update.from_dict(_message_update("hello"))
        msg = u.get_update_object()
        assert (~F.forwarded)(msg) is True

    def test_f_command_shortcut(self):
        f = F.command("start", "help")
        u = Update.from_dict(_message_update("/start"))
        msg = u.get_update_object()
        assert f(msg) is True
        u2 = Update.from_dict(_message_update("/other"))
        assert f(u2.get_update_object()) is False

    def test_f_missing_preset_raises(self):
        with pytest.raises(AttributeError):
            F.nonexistent

    def test_f_user_and_chat_presets(self):
        fu = F.user(7)
        u = Update.from_dict(_message_update("x", user_id=7))
        assert fu(u.get_update_object()) is True
        fc = F.chat(99)
        assert fc(u.get_update_object()) is False

    def test_f_supergroup_preset(self):
        d = _message_update("x", chat_id=2)
        d["message"]["chat"]["type"] = "supergroup"
        u = Update.from_dict(d)
        msg = u.get_update_object()
        assert F.supergroup(msg) is True
        assert F.private(msg) is False


# ======================================================================
# Pipeline + dependency injection
# ======================================================================

class PipelineTests:
    @pytest.mark.asyncio
    async def test_pipeline_di_by_name(self):
        pipe = Pipeline()
        results = {}

        async def handler(ctx, db, ctx2_marker="sentinel"):
            results["db"] = db
            results["text"] = ctx.text

        pipe.deps(db={"x": 1})
        pipe.handle(F.text, handler)

        bot = _make_bot()
        update = Update.from_dict(_message_update("ping"))
        ctx = bot._fake_context_for_test(update) if hasattr(bot, "_fake_context_for_test") else None
        # Build a context directly.
        from swiftbot.context import Context
        ctx = Context(bot, update, update.get_update_object())
        handled = await pipe.process(ctx, bot)
        assert handled is True
        assert results["db"] == {"x": 1}
        assert results["text"] == "ping"

    @pytest.mark.asyncio
    async def test_pipeline_missing_dep_raises(self):
        pipe = Pipeline()

        async def handler(ctx, missing_service):
            pass

        pipe.handle(F.text, handler)
        bot = _make_bot()
        update = Update.from_dict(_message_update("ping"))
        from swiftbot.context import Context
        ctx = Context(bot, update, update.get_update_object())
        with pytest.raises(Exception):
            await pipe.process(ctx, bot)

    @pytest.mark.asyncio
    async def test_pipeline_first_match_wins(self):
        pipe = Pipeline(first=True)
        order = []

        async def h1(ctx):
            order.append(1)

        async def h2(ctx):
            order.append(2)

        pipe.handle(F.text, h1)
        pipe.handle(F.text, h2)
        bot = _make_bot()
        update = Update.from_dict(_message_update("x"))
        from swiftbot.context import Context
        ctx = Context(bot, update, update.get_update_object())
        await pipe.process(ctx, bot)
        assert order == [1]

    @pytest.mark.asyncio
    async def test_pipeline_bot_mounted_and_processed(self):
        """A pipeline mounted via bot.pipeline() handles updates end to end."""
        bot = _make_bot()
        pipe = bot.pipeline()
        pipe.deps(greeting="yo")
        seen = {}

        async def greet(ctx, greeting):
            seen["greeting"] = greeting
            seen["text"] = ctx.text

        pipe.handle(F.text, greet)
        await bot._process_update(_message_update("hello"))
        assert seen == {"greeting": "yo", "text": "hello"}

    @pytest.mark.asyncio
    async def test_pipeline_not_handled_falls_through(self):
        bot = _make_bot()
        pipe = bot.pipeline()
        # pipeline only matches /cmd; normal text falls through to router
        pipe.handle(F.command("cmd"), lambda ctx: None)
        handled = []

        @bot.on(Message(text="anything"))
        async def main_handler(ctx):
            handled.append(ctx.text)

        await bot._process_update(_message_update("anything"))
        assert handled == ["anything"]

    @pytest.mark.asyncio
    async def test_pipeline_optional_param_defaults(self):
        pipe = Pipeline()
        got = {}

        async def handler(ctx, extra="default"):
            got["extra"] = extra

        pipe.handle(F.text, handler)
        bot = _make_bot()
        update = Update.from_dict(_message_update("x"))
        from swiftbot.context import Context
        ctx = Context(bot, update, update.get_update_object())
        await pipe.process(ctx, bot)
        assert got["extra"] == "default"

    def test_pipeline_deps_chaining(self):
        pipe = Pipeline()
        result = pipe.deps(a=1).deps(b=2)
        assert result is pipe
        assert pipe.get_dep("a") == 1
        assert pipe.get_dep("b") == 2


# ======================================================================
# BotCommands — declarative typed commands
# ======================================================================

class Cmd(BotCommands):
    start = "start the session"
    name = "greet someone | /name <first> <last>"
    score = "record | /score <player> <points:int>"


class BotCommandsTests:
    def test_parse_simple(self):
        p = Cmd.parse("/start")
        assert p is not None
        assert p.name == "start"
        assert p.args == []

    def test_parse_typed_args(self):
        p = Cmd.parse("/score neo 99")
        assert p is not None
        assert p.name == "score"
        assert p.args == ["neo", 99]

    def test_parse_wrong_arg_count(self):
        assert Cmd.parse("/score only_one") is None
        assert Cmd.parse("/name") is None

    def test_parse_non_command(self):
        assert Cmd.parse("hello world") is None

    def test_help_text(self):
        help_page = Cmd.help_text()
        assert "/start" in help_page
        assert "/score" in help_page
        assert "record" in help_page  # description of score

    def test_contains_and_iter(self):
        assert "start" in Cmd
        assert set(Cmd) == {"start", "name", "score"}

    def test_filter_callable(self):
        u = Update.from_dict(_message_update("/name Arjun M"))
        assert Cmd.name(u.get_update_object()) is True
        u2 = Update.from_dict(_message_update("/other"))
        assert Cmd.name(u2.get_update_object()) is False

    @pytest.mark.asyncio
    async def test_middleware_populates_ctx_command(self):
        bot = _make_bot()
        bot.use(CommandsMiddleware(Cmd))
        got = {}

        @bot.on(Message(filters=Cmd.name))
        async def name_handler(ctx):
            got["cmd"] = ctx.command.name
            got["args"] = list(ctx.command.args)

        await bot._process_update(_message_update("/name Arjun M"))
        assert got == {"cmd": "name", "args": ["Arjun", "M"]}

    def test_parsed_command_description(self):
        p = Cmd.parse("/name x y")
        assert p.description == "greet someone"
        assert p.usage_line == "/name <first> <last>"

    def test_empty_text_parse(self):
        assert Cmd.parse("") is None
        assert Cmd.parse("   ") is None


# ======================================================================
# Transformers — outbound API interception
# ======================================================================

class TransformerTests:
    @pytest.mark.asyncio
    async def test_config_applies_transformers(self):
        bot = _make_bot()
        log = []
        bot.api.config.use(call_logger(lambda m, p: log.append((m, p))))
        bot.api.config.script("getMe", result={"id": 1, "is_bot": True, "first_name": "B"})
        result = await bot.api._request("getMe")
        assert result["first_name"] == "B"
        assert log and log[0][0] == "getMe"

    @pytest.mark.asyncio
    async def test_payload_patch_defaults(self):
        bot = _make_bot()
        bot.api.config.use(payload_patch(parse_mode="MarkdownV2"))
        rec = Recorder()
        rec.script("sendMessage", result=True)
        bot.api.config.use(rec)
        await bot.api._request("sendMessage", chat_id=1, text="hi")
        call = rec.calls[0]
        assert call["params"]["parse_mode"] == "MarkdownV2"

    @pytest.mark.asyncio
    async def test_recorder_and_script(self):
        bot = _make_bot()
        rec = Recorder()
        rec.script("sendMessage", result={"message_id": 42})
        bot.api.config.use(rec)
        result = await bot.api.send_message(1, text="hi")
        assert result == {"message_id": 42}
        assert rec.calls[0]["method"] == "sendMessage"

    @pytest.mark.asyncio
    async def test_scripted_error_raised(self):
        from swiftbot.exceptions import TelegramError
        bot = _make_bot()
        rec = Recorder()
        rec.script("sendMessage", error={
            "ok": False, "error_code": 400, "description": "chat not found"})
        bot.api.config.use(rec)
        with pytest.raises(TelegramError):
            await bot.api._request("sendMessage", chat_id=999)

    @pytest.mark.asyncio
    async def test_config_script_shortcut(self):
        bot = _make_bot()
        bot.api.config.script("getMe", result={"id": 2})
        result = await bot.api._request("getMe")
        assert result["id"] == 2

    def test_auto_typing_creation(self):
        t = auto_typing(interval=5.0)
        assert asyncio.iscoroutinefunction(t)

    @pytest.mark.asyncio
    async def test_idempotency_guard_transformer(self):
        t = idempotency_guard()
        p = {"chat_id": 1, "text": "x"}
        first = await t("sendMessage", p)
        assert first == p  # first call passes through

    @pytest.mark.asyncio
    async def test_async_transformer_wrapping(self):
        bot = _make_bot()

        def sync_t(method, payload):
            return payload

        bot.api.config.use(sync_t)  # sync callable auto-wrapped
        bot.api.config.script("getMe", result={"id": 3})
        r = await bot.api._request("getMe")
        assert r["id"] == 3

    @pytest.mark.asyncio
    async def test_broken_transformer_does_not_block(self):
        bot = _make_bot()

        async def broken(method, payload):
            raise RuntimeError("boom")

        bot.api.config.use(broken)
        bot.api.config.script("getMe", result={"id": 4})
        r = await bot.api._request("getMe")
        assert r["id"] == 4


# ======================================================================
# Composer — middleware bundles + error boundaries
# ======================================================================

class ComposerTests:
    @pytest.mark.asyncio
    async def test_bundle_runs_middleware(self):
        log = []

        class M:
            async def on_update(self, ctx, next_handler):
                log.append("pre")
                await next_handler()
                log.append("post")

        bundle = Composer(M())
        handled = []

        @handler_fn(handled)
        async def _unused():
            pass

        # Use bundle on a bot; middleware chain executes inside it.
        bot = _make_bot()
        bot.use(bundle)

        @bot.on(Message(text="x"))
        async def h(ctx):
            handled.append(1)

        await bot._process_update(_message_update("x"))
        assert log == ["pre", "post"]
        assert handled == [1]

    @pytest.mark.asyncio
    async def test_catch_boundary_handles_error(self):
        bot = _make_bot()
        bundle = Composer()
        caught = {}

        async def failing(ctx, next_handler):
            raise ValueError("boom")

        async def boundary(ctx, e):
            caught["err"] = str(e)

        bundle.use(failing)
        bundle.catch(boundary)
        bot.use(bundle)

        @bot.on(Message(text="x"))
        async def _dummy(ctx):
            pass  # handler must be registered so the middleware chain runs

        await bot._process_update(_message_update("x"))
        assert "boom" in caught["err"]

    @pytest.mark.asyncio
    async def test_no_boundary_propagates(self):
        bot = _make_bot()
        bundle = Composer()

        async def failing(ctx, next_handler):
            raise ValueError("boom")

        bundle.use(failing)
        bot.use(bundle)

        @bot.on(Message(text="x"))
        async def _dummy(ctx):
            pass  # handler must be registered so the middleware chain runs

        # Without a boundary the error must not be swallowed inside the
        # bundle. ``_process_update`` catches and centralises exceptions,
        # so exercise the bundle directly to prove the exception escapes.
        raw = _message_update("x")
        ctx = Context(bot, raw, Message(**raw["message"]))
        with pytest.raises(ValueError, match="boom"):
            await bundle.on_update(ctx, lambda: None)

    def test_use_chaining(self):
        bundle = Composer().use(1, 2).use(3)
        assert len(bundle) == 3


def handler_fn(collector):
    return lambda fn: fn


# ======================================================================
# Dispatch routing — bot.route()
# ======================================================================

class RouteTests:
    @pytest.mark.asyncio
    async def test_update_kind_dispatch(self):
        bot = _make_bot()
        log = []

        class RouteMW:
            async def on_update(self, ctx, next_handler):
                log.append(ctx.text or getattr(ctx, "data", None))
                await next_handler()

        bot.route({"callback_query": RouteMW()})
        await bot._process_update(_callback_update("nav_home"))
        assert log == ["nav_home"]

    @pytest.mark.asyncio
    async def test_unknown_kind_warned(self):
        bot = _make_bot()
        bot.route({"nonexistent_kind": None})
        assert "nonexistent_kind" not in bot._routes

    @pytest.mark.asyncio
    async def test_callable_route(self):
        bot = _make_bot()
        log = []

        async def route_fn(ctx):
            log.append("called")

        bot.route({"inline_query": route_fn})
        update = {"update_id": 3, "inline_query": {
            "id": "iq1", "from": {"id": 7, "is_bot": False, "first_name": "T"},
            "query": "search", "offset": ""}}
        await bot._process_update(update)
        assert log == ["called"]


# ======================================================================
# Wizard — typed multi-step dialogs
# ======================================================================

class WizardTests:
    @pytest.mark.asyncio
    async def test_full_wizard_flow(self):
        storage = MemoryStorage()
        wiz = Wizard("survey", storage)
        steps = []

        @wiz.step("q1")
        async def s1(ctx):
            steps.append("q1")

        @wiz.step("q2")
        async def s2(ctx):
            steps.append("q2")

        @wiz.finish
        async def done(ctx, data):
            steps.append(("done", dict(data)))

        bot = _make_bot()
        bot.storage = storage
        bot._wizards["survey"] = wiz
        update = Update.from_dict(_message_update("x"))
        from swiftbot.context import Context
        ctx = Context(bot, update, update.get_update_object())

        assert await wiz.enter(ctx) is True
        assert steps == ["q1"]
        assert await wiz.current_step(ctx) == "q1"
        assert await wiz.step_forward(ctx, "alice") is True
        assert steps == ["q1", "q2"]
        assert await wiz.step_forward(ctx, "30") is True
        assert steps[-1][0] == "done"
        assert steps[-1][1] == {"q1": "alice", "q2": "30"}

    @pytest.mark.asyncio
    async def test_inactive_wizard_passes(self):
        storage = MemoryStorage()
        wiz = Wizard("other", storage)
        bot = _make_bot()
        update = Update.from_dict(_message_update("x"))
        from swiftbot.context import Context
        ctx = Context(bot, update, update.get_update_object())
        assert await wiz.step_forward(ctx, "anything") is False

    @pytest.mark.asyncio
    async def test_exit_clears_state(self):
        storage = MemoryStorage()
        wiz = Wizard("x", storage)

        @wiz.step("s1")
        async def s1(ctx):
            pass

        bot = _make_bot()
        update = Update.from_dict(_message_update("x"))
        from swiftbot.context import Context
        ctx = Context(bot, update, update.get_update_object())
        await wiz.enter(ctx)
        assert await wiz.exit(ctx) is True
        assert await wiz.current_step(ctx) is None

    @pytest.mark.asyncio
    async def test_bot_wizard_factory(self):
        bot = _make_bot()
        wiz = bot.wizard("onboard")
        assert wiz.name == "onboard"
        assert bot._wizards["onboard"] is wiz


# ======================================================================
# Graceful shutdown
# ======================================================================

class ShutdownTests:
    @pytest.mark.asyncio
    async def test_run_shutdown_installs_handlers(self):
        import signal
        bot = _make_bot()
        await bot.run_shutdown(timeout=5.0)
        # handlers installed — simulate SIGINT delivery
        loop = asyncio.get_event_loop()
        try:
            loop.call_soon(os.kill, os.getpid(), signal.SIGINT)
        except PermissionError:
            pytest.skip("cannot send signal to self")
        # give the handler task a moment
        for _ in range(20):
            await asyncio.sleep(0.05)
            if bot._shutdown_requested.is_set():
                break
        assert bot._shutdown_requested.is_set()


# ======================================================================
# Plugins
# ======================================================================

class PluginTests:
    @pytest.mark.asyncio
    async def test_spam_deflector_blocks_flooder(self):
        bot = _make_bot()
        sd = plugins.spam_deflector(threshold=3, window=60.0)
        bot.use(sd)
        handled = []

        @bot.on(Message(text="x"))
        async def h(ctx):
            handled.append(1)

        for _ in range(5):
            await bot._process_update(_message_update("x"))
        # threshold=3 → first 3 pass, rest dropped
        assert len(handled) == 3

    @pytest.mark.asyncio
    async def test_session_limiter_throttles(self):
        bot = _make_bot()
        bot.use(plugins.session_limiter(min_interval=10.0))
        handled = []

        @bot.on(Message(text="x"))
        async def h(ctx):
            handled.append(1)

        await bot._process_update(_message_update("x"))
        await bot._process_update(_message_update("x"))
        assert handled == [1]

    @pytest.mark.asyncio
    async def test_idempotency_dedupes(self):
        bot = _make_bot()
        bot.use(plugins.idempotency(window=5.0))
        handled = []

        @bot.on(Message(text="x"))
        async def h(ctx):
            handled.append(1)

        await bot._process_update(_message_update("x"))
        await bot._process_update(_message_update("x"))
        assert handled == [1]

    @pytest.mark.asyncio
    async def test_whitelist_blocks_unknown(self):
        bot = _make_bot()
        bot.use(plugins.whitelist(user_ids={999}))
        handled = []

        @bot.on(Message(text="x"))
        async def h(ctx):
            handled.append(1)

        await bot._process_update(_message_update("x"))
        assert handled == []

    @pytest.mark.asyncio
    async def test_deflect_hook_called(self):
        deflected = []
        sd = SpamDeflector(threshold=1, window=60.0, on_deflect=lambda ctx: deflected.append(1))
        bot = _make_bot()
        bot.use(sd)

        @bot.on(Message(text="x"))
        async def h(ctx):
            pass

        await bot._process_update(_message_update("x"))  # passes
        await bot._process_update(_message_update("x"))  # deflected
        assert deflected == [1]
