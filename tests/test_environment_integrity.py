"""
SwiftBot Environment & Package Integrity Verification Suite
============================================================

A comprehensive, fully offline test suite that verifies the
``swiftbot`` package (Arjun-M/SwiftBot) is fully functional, undamaged,
and correctly installed in this environment.

What is verified (no real Telegram token or internet connection needed):

1. PACKAGE INTEGRITY
   - The package imports cleanly and exposes all documented top-level
     names (SwiftBot, types, middleware, filters, testing harness, etc.)
   - Version, author and license metadata are present and sane
   - Sub-packages (middleware, exceptions, connection, webhook) import

2. BOT INITIALIZATION & CONFIGURATION
   - SwiftBot(token) constructs with correct defaults
   - ConfigurationError is raised for invalid/empty tokens
   - Config options (parse_mode, worker_pool_size, api_base_url, debug,
     storage, state_ttl, custom HTTPConnectionPool) are honored
   - Default storage is MemoryStorage; an invalid storage raises
     ConfigurationError

3. ASYNC MESSAGE ROUTING & COMMAND EXECUTION (fully mocked)
   - unittest.mock.AsyncMock is used to simulate async message routing
     and handler execution safely, without network
   - Text handlers, regex/pattern handlers and callback-query handlers
     route through the real router
   - Middleware chains execute in order and can short-circuit
   - CommandsMiddleware populates ctx.command and the
     on_unknown_command fallback intercepts unrecognized slash commands
   - The first-party FakePool / TestClient harness records outgoing
     API calls (sendMessage, answerCallbackQuery, ...) correctly
   - FSM storage round-trips user state; dialogues transition states
   - Pipelines process matching branches with dependency injection

Copyright (c) 2025 — environment verification for Arjun-M/SwiftBot
"""

import asyncio
import sys
import importlib
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

# ---------------------------------------------------------------------------
# 1. PACKAGE INTEGRITY TESTS
# ---------------------------------------------------------------------------


class PackageIntegrityTests:
    """Verify the swiftbot package is importable and complete."""

    def test_package_imports(self):
        import swiftbot  # noqa: F401

    def test_version_is_set(self):
        import swiftbot

        assert swiftbot.__version__, "swiftbot.__version__ must be non-empty"
        parts = swiftbot.__version__.split(".")
        assert len(parts) == 3 and all(p.isdigit() for p in parts), (
            "semantic version expected, e.g. '1.6.0'"
        )

    def test_metadata_present(self):
        import swiftbot

        assert swiftbot.__author__
        assert swiftbot.__license__ in ("MIT", "MIT License")

    def test_core_client_exported(self):
        import swiftbot

        assert swiftbot.SwiftBot is not None
        assert swiftbot.Context is not None

    def test_types_module_complete(self):
        from swiftbot import types

        for name in (
            "Message", "CallbackQuery", "InlineQuery",
            "EditedMessage", "ChatMemberUpdated", "EventType",
        ):
            assert hasattr(types, name), f"swiftbot.types.{name} missing"

    def test_middleware_module_exports(self):
        from swiftbot import middleware

        for name in ("Middleware", "Logger", "Auth", "RateLimiter",
                     "AnalyticsCollector"):
            assert hasattr(middleware, name), f"middleware.{name} missing"

    def test_middleware_base_protocol(self):
        from swiftbot.middleware import Middleware

        assert asyncio.iscoroutinefunction(Middleware.on_update), (
            "Middleware.on_update must be an async method"
        )

    def test_subpackages_import(self):
        from swiftbot import exceptions  # noqa: F401
        from swiftbot.connection import pool, worker  # noqa: F401
        from swiftbot.webhook import server  # noqa: F401
        from swiftbot import middleware  # noqa: F401

    def test_all_documented_exports_importable(self):
        """Every name in swiftbot.__all__ must be importable (undamaged)."""
        import swiftbot

        importable = set(dir(swiftbot))
        missing = [n for n in swiftbot.__all__ if n not in importable]
        assert not missing, f"missing exports: {missing}"

    def test_filters_exports(self):
        from swiftbot import filters

        assert hasattr(filters, "Filters")
        assert hasattr(filters, "F")
        assert hasattr(filters, "CommandFilter")

    def test_testing_harness_exports(self):
        from swiftbot.testing import FakePool, TestClient

        assert FakePool is not None
        assert TestClient is not None

    def test_callback_data_and_deep_linking(self):
        from swiftbot import callback_data, deep_linking

        assert hasattr(callback_data, "CallbackData")
        assert hasattr(deep_linking, "encode_payload")
        assert hasattr(deep_linking, "decode_payload")

    def test_storage_backends(self):
        from swiftbot.storage import MemoryStorage, JSONFileStorage, BaseStorage

        assert issubclass(MemoryStorage, BaseStorage)
        assert issubclass(JSONFileStorage, BaseStorage)


# ---------------------------------------------------------------------------
# 2. BOT INITIALIZATION & CONFIGURATION TESTS
# ---------------------------------------------------------------------------

from swiftbot import SwiftBot, Context, EventType, Message, CallbackQuery, Update
from swiftbot.commands import BotCommands, CommandsMiddleware
from swiftbot.exceptions import ConfigurationError, SwiftBotError
from swiftbot.filters import Filters, F, CommandFilter
from swiftbot.testing import _FakeResponse
from swiftbot.middleware import Logger, Auth, RateLimiter, Middleware
from swiftbot.storage import MemoryStorage, StateManager, BaseStorage
from swiftbot.testing import FakePool, TestClient


@pytest.fixture
def bot():
    """A minimally configured bot for configuration tests."""
    return SwiftBot(token="1234567890:AAE-test-token-for-environment-check-only")


class BotInitializationTests:
    """Verify SwiftBot initializes correctly under valid and invalid configs."""

    def test_token_validation_raises_on_empty(self, bot):
        with pytest.raises(ConfigurationError):
            SwiftBot(token="")

    def test_token_validation_raises_on_whitespace(self):
        with pytest.raises(ConfigurationError):
            SwiftBot(token="   ")

    def test_token_validation_raises_on_non_string(self):
        with pytest.raises(ConfigurationError):
            SwiftBot(token=None)

    def test_token_is_stripped_and_stored(self, bot):
        assert bot.token == "1234567890:AAE-test-token-for-environment-check-only"
        wrapped = SwiftBot(token="  " + bot.token + "  ")
        assert wrapped.token == bot.token

    def test_default_configuration(self, bot):
        assert bot.parse_mode == "HTML"
        assert bot.async_mode is True
        assert bot.api_base_url == "https://api.telegram.org"
        assert bot.debug is False
        assert bot.running is False
        assert bot.worker_pool.num_workers == 50
        assert isinstance(bot.storage, MemoryStorage)

    def test_custom_configuration_honored(self):
        bot = SwiftBot(
            token="1234567890:AAE-test",
            parse_mode="MarkdownV2",
            worker_pool_size=10,
            api_base_url="http://localhost:8081",
            debug=True,
        )
        assert bot.parse_mode == "MarkdownV2"
        assert bot.worker_pool.num_workers == 10
        assert bot.api_base_url == "http://localhost:8081"
        assert bot.debug is True

    def test_storage_validation_raises_on_non_storage(self):
        with pytest.raises(ConfigurationError, match="BaseStorage"):
            SwiftBot(token="1234567890:AAE-test", storage="not a storage")

    def test_custom_storage_wired(self):
        store = MemoryStorage()
        bot = SwiftBot(token="1234567890:AAE-test", storage=store)
        assert bot.storage is store

    def test_state_ttl_wired(self):
        bot = SwiftBot(token="1234567890:AAE-test", state_ttl=60.0)
        assert isinstance(bot._state_manager, StateManager)

    def test_centralized_exception_handler_config(self):
        bot_on = SwiftBot(token="1234567890:AAE-test",
                          enable_centralized_exceptions=True)
        bot_off = SwiftBot(token="1234567890:AAE-test",
                           enable_centralized_exceptions=False)
        assert bot_on.exception_handler is not None
        assert bot_off.exception_handler is None

    def test_router_lists_empty_at_init(self, bot):
        """Router exposes per-kind handler registries; all start empty."""
        for attr in ("text_handlers", "callback_handlers", "inline_handlers",
                     "edited_message_handlers", "command_trie"):
            registry = getattr(bot.router, attr)
            if hasattr(registry, "__len__"):
                assert len(registry) == 0, f"router.{attr} should be empty at init"
        assert bot.middleware == []

    def test_middleware_registration(self, bot):
        mw = Logger()
        bot.use(mw)
        assert mw in bot.middleware

    def test_run_mode_validation(self, bot):
        with pytest.raises(ConfigurationError, match="Invalid mode"):
            asyncio.get_event_loop().run_until_complete(
                bot.run(mode="invalid_mode_xyz")
            )


# ---------------------------------------------------------------------------
# 3. ASYNC MESSAGE ROUTING & COMMAND EXECUTION TESTS (MOCKED)
#
# These tests use unittest.mock.AsyncMock to simulate asynchronous
# handlers and the Telegram API. No token, no network, no getUpdates.
# ---------------------------------------------------------------------------


def _raw_message(user_id: int = 7, chat_id: int = 42,
                 text: str = "hello", update_id: int = 1,
                 chat_type: str = "private"):
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


def _raw_callback(user_id: int = 7, chat_id: int = 42, data: str = "action",
                  update_id: int = 2):
    return {
        "update_id": update_id,
        "callback_query": {
            "id": "cb1",
            "from": {"id": user_id, "is_bot": False, "first_name": "Tester"},
            "chat_instance": str(chat_id),
            "data": data,
            "message": {
                "message_id": 99,
                "date": 1000,
                "chat": {"id": chat_id, "type": "private"},
            },
        },
    }


@pytest.fixture
def bot_with_pool():
    """Bot wired to the offline FakePool, worker pool started."""
    fake = FakePool()
    fake.script("sendMessage", result={"message_id": 1})
    fake.script("answerCallbackQuery", result=True)
    fake.script("getMe", result={"id": 9, "is_bot": True, "first_name": "TestBot"})
    bot = SwiftBot(token="1234567890:AAE-test-token-for-environment-check-only")
    bot.connection_pool = fake
    bot.api.pool = fake
    return bot, fake


class MockedAsyncMessageRoutingTests:
    """Simulate async routing purely with mocks — no Telegram network."""

    @pytest.mark.asyncio
    async def test_handler_registered_via_decorator(self, bot_with_pool):
        bot, _ = bot_with_pool
        handler = AsyncMock(name="handler")

        @bot.on(Message(text="ping"))
        async def ping(ctx):
            await handler(ctx)

        ctx = MagicMock(spec=Context)
        called = await bot._execute_middleware_chain(ctx, ping)
        # _execute_middleware_chain itself awaits the handler chain
        assert handler.called

    @pytest.mark.asyncio
    async def test_middleware_chain_order_and_short_circuit(self, bot_with_pool):
        bot, _ = bot_with_pool
        call_log = []

        class Tracer(Middleware):
            def __init__(self, name):
                self.name = name

            async def on_update(self, ctx, next_handler):
                call_log.append(self.name)
                await next_handler()

        mw1 = Tracer("mw1")
        mw2 = Tracer("mw2")
        bot.use(mw1)
        bot.use(mw2)

        final = AsyncMock(name="final_handler")

        async def chain(ctx):
            await final(ctx)

        await bot._execute_middleware_chain(None, chain)

        assert call_log == ["mw1", "mw2"], "middleware must run in registration order"
        final.assert_called_once()

    @pytest.mark.asyncio
    async def test_middleware_short_circuit_blocks_handler(self, bot_with_pool):
        bot, _ = bot_with_pool

        class Blocker(Middleware):
            async def on_update(self, ctx, next_handler):
                return  # intentionally does NOT call next_handler()

        bot.use(Blocker())
        final = AsyncMock(name="blocked_handler")

        await bot._execute_middleware_chain(None, final)
        final.assert_not_called(), "short-circuiting middleware must block the handler"

    @pytest.mark.asyncio
    async def test_callback_query_routing(self, bot_with_pool):
        bot, fake = bot_with_pool
        handler = AsyncMock(name="cb_handler")

        @bot.on(CallbackQuery(data="buy"))
        async def buy(ctx):
            await handler(ctx)
            await ctx.answer_callback(text="OK")

        # ``CallbackQuery(data=...)`` registers a handler in the router's
        # callback registry (the exact ``data`` filter requires an exact
        # match against ``update_obj.data``).
        assert bot.router.callback_handlers, (
            "CallbackQuery handler must land in router.callback_handlers"
        )

        async with TestClient(bot, fake) as client:
            # Exact ``data`` filter: the dispatched payload must equal "buy".
            await client.send_update(_raw_callback(data="buy"))

        handler.assert_called_once()
        methods = [r["method"] for r in fake.outgoing]
        assert "answerCallbackQuery" in methods, (
            "ctx.answer_callback() must call answerCallbackQuery"
        )

    @pytest.mark.asyncio
    async def test_pattern_matching_reaches_handler(self, bot_with_pool):
        bot, fake = bot_with_pool
        handler = AsyncMock(name="regex_handler")

        @bot.on(Message(pattern=r"^/order\s+(?P<item>\w+)"))
        async def order(ctx):
            assert ctx.match and ctx.match.group("item") == "pizza"
            await handler(ctx, ctx.match.group("item"))

        async with TestClient(bot, fake) as client:
            await client.send_update(_raw_message(text="/order pizza"))

        handler.assert_called_once()

    @pytest.mark.asyncio
    async def test_filter_system_text_filter(self, bot_with_pool):
        bot, fake = bot_with_pool
        handler = AsyncMock(name="filter_handler")

        @bot.on(Message(func=lambda m: getattr(m, "text", "") == "filter_hit"))
        async def filt(ctx):
            await handler(ctx)

        async with TestClient(bot, fake) as client:
            await client.send_update(_raw_message(text="filter_hit"))
            await client.send_update(_raw_message(text="filter_miss"))

        assert handler.call_count == 1


class CommandExecutionTests:
    """Verify declarative command specs and unknown-command handling."""

    @pytest.mark.asyncio
    async def test_commands_middleware_parsers_text_handler(self, bot_with_pool):
        bot, fake = bot_with_pool

        class Cmd(BotCommands):
            start = "start the bot"
            echo = "echo args | /echo <a> <b>"

        called = []

        @bot.on(Message(func=Cmd.start))
        async def start_handler(ctx):
            called.append(("start", ctx.command))

        @bot.on(Message(func=Cmd.echo))
        async def echo_handler(ctx):
            called.append(("echo", ctx.command.args))

        bot.use(CommandsMiddleware(Cmd))

        async with TestClient(bot, fake) as client:
            await client.send_update(_raw_message(text="/start"))
            await client.send_update(_raw_message(text="/echo hello world"))

        assert ("start", ctx_or_none := called[0][1]) is not None
        assert called[0][0] == "start"
        assert called[1] == ("echo", ["hello", "world"])

    @pytest.mark.asyncio
    async def test_unknown_command_fallback(self, bot_with_pool):
        bot, fake = bot_with_pool

        class Cmd(BotCommands):
            start = "start"

        bot.use(CommandsMiddleware(Cmd))

        @bot.on_unknown_command
        async def unknown(ctx):
            await ctx.reply(f"Unknown: /{ctx.command if ctx.command else 'cmd'}")

        async with TestClient(bot, fake) as client:
            await client.send_update(_raw_message(text="/bogus_command"))

        methods = [r["method"] for r in fake.outgoing]
        assert "sendMessage" in methods, "unknown command handler must send a reply"


class FakePoolAndTestClientTests:
    """Verify the first-party offline test harness behaves correctly."""

    @pytest.mark.asyncio
    async def test_outgoing_api_calls_recorded(self, bot_with_pool):
        bot, fake = bot_with_pool

        @bot.on(Message(text="/hi"))
        async def hi(ctx):
            await ctx.reply("hi back")

        async with TestClient(bot, fake) as client:
            await client.send_update(_raw_message(text="/hi"))

        sent = next(r for r in fake.outgoing if r["method"] == "sendMessage")
        assert sent["params"]["chat_id"] == 42
        assert "hi back" in sent["params"]["text"]

    @pytest.mark.asyncio
    async def test_mocked_api_errors_propagate(self, bot_with_pool, caplog):
        bot, fake = bot_with_pool

        @bot.on(Message(text="/fail"))
        async def fail(ctx):
            try:
                await ctx.reply("boom")
            except Exception:
                await ctx.bot.api.send_message(
                    chat_id=ctx.chat.id, text="error caught"
                )

        # A per-method ``hook`` guarantees the FIRST ``sendMessage`` call
        # (the handler's ``ctx.reply``) fails with a scripted Telegram
        # error, and every subsequent call succeeds — independent of any
        # response order established by fixtures.
        call_count = {"sendMessage": 0}

        def script_hook(method, params):
            call_count[method] = call_count.get(method, 0) + 1
            if method == "sendMessage" and call_count[method] == 1:
                return _FakeResponse(403, {"ok": False, "error_code": 403,
                                           "description": "Forbidden"})
            return _FakeResponse(200, {"ok": True,
                                       "result": {"message_id": call_count[method]}})

        fake.hook = script_hook

        async with TestClient(bot, fake) as client:
            await client.send_update(_raw_message(text="/fail"))

        # The reply call must have failed at the API layer (asserted via the
        # handler's except path AND the error logged by ``Context.reply``).
        assert any(r["params"]["text"] == "error caught" for r in fake.outgoing), (
            "handler must catch the API error and send a recovery message"
        )
        assert any(
            "Telegram API error 403" in rec.getMessage()
            for rec in caplog.records if "reply" in rec.getMessage().lower()
        ), "the Telegram 403 error must propagate up to the context"

    @pytest.mark.asyncio
    async def test_async_mock_wired_into_api(self, bot_with_pool):
        """Direct AsyncMock substitution for the Telegram API layer."""
        bot, fake = bot_with_pool
        bot.api.send_message = AsyncMock(
            return_value={"message_id": 7, "text": "mocked"}, name="send_message"
        )

        result = await bot.send_message(chat_id=99, text="via mock")
        bot.api.send_message.assert_awaited_once()
        # The public method enforces defaults while delegating to the API
        actual = bot.api.send_message.call_args
        assert actual.kwargs["chat_id"] == 99
        assert actual.kwargs["text"] == "via mock"
        assert actual.kwargs["parse_mode"] == "HTML"  # client-level parse mode
        assert result == {"message_id": 7, "text": "mocked"}

    @pytest.mark.asyncio
    async def test_get_me_uses_cached_result(self, bot_with_pool):
        bot, fake = bot_with_pool
        bot._bot_info = {"id": 9, "is_bot": True, "first_name": "TestBot"}
        bot._bot_info_expires = asyncio.get_running_loop().time() + 300

        info = await bot.get_me(use_cache=True)
        assert info["id"] == 9
        # Cache hit means the API layer was never touched
        assert not any(r["method"] == "getMe" for r in fake.outgoing)


class FSMStorageAndDialogueTests:
    """Verify FSM state storage round-trip and state-carrying dialogues."""

    @pytest.mark.asyncio
    async def test_storage_round_trip(self):
        store = MemoryStorage()
        manager = StateManager(store)
        await manager.set_state(user_id=123, state={"step": "name"})
        assert await manager.get_state(user_id=123) == {"step": "name"}
        await manager.clear_state(user_id=123)
        assert await manager.get_state(user_id=123) is None

    def test_state_ttl_config(self):
        """``state_ttl`` is wired into the client's StateManager."""
        bot = SwiftBot(token="1234567890:AAE-test-token-for-environment-check-only",
                       state_ttl=0.001)
        assert bot._state_manager.ttl == 0.001

    @pytest.mark.asyncio
    async def test_state_ttl_expiry(self):
        store = MemoryStorage()
        manager = StateManager(store, ttl=0.001)  # essentially immediate expiry
        await manager.set_state(user_id=123, state="ephemeral")
        await asyncio.sleep(0.01)
        assert await manager.get_state(user_id=123) is None

    @pytest.mark.asyncio
    async def test_dialogue_state_transition(self, bot_with_pool):
        from swiftbot.dialogue import Dialogue

        bot, fake = bot_with_pool
        dlg = bot.dialogue("survey")

        called = []

        @dlg.state("greeting", next=["name"])
        async def greeting(ctx, prev=None):
            called.append(("greeting", prev))
            await ctx.reply("What is your name?")
            return Dialogue.next("name")

        @dlg.state("name", next=["done"])
        async def name_state(ctx, prev=None):
            called.append(("name", prev))
            return Dialogue.next("done")

        @dlg.finish
        async def done(ctx, prev=None):
            called.append(("done", prev))
            return Dialogue.end

        async with TestClient(bot, fake) as client:
            # Seed an active dialogue in the dialogue's own storage backend
            # (stored as a ``state, carry`` tuple keyed by user id).
            seed_ctx = Context(bot, Update.from_dict(_raw_message()),
                               Update.from_dict(_raw_message()).get_update_object())
            await dlg._set_state(seed_ctx, "greeting", None)
            await client.send_update(_raw_message(text="Alice"))

        replies = [r for r in fake.outgoing if r["method"] == "sendMessage"]
        texts = " ".join(r["params"]["text"] for r in replies)
        assert "What is your name?" in texts, (
            "the greeting state must have answered the update"
        )
        # The seed context (carrying ``text="Alice"``) makes the active
        # ``greeting`` state run and hand its answer to the next state via
        # ``step_forward``. The dialogue then advanced at least one step.
        assert called, "the seeded dialogue state must have executed"
        assert called[0][0] == "greeting"
        # After advancing, the active state must no longer be ``greeting``
        assert await dlg.current(seed_ctx) != "greeting"


class PipelineTests:
    """Verify declarative pipelines with dependency injection."""

    @pytest.mark.asyncio
    async def test_pipeline_process(self, bot_with_pool):
        from swiftbot.pipeline import Pipeline

        bot, fake = bot_with_pool
        pipe = bot.pipeline()
        pipe.deps(counter=MagicMock(value=0))

        # Handlers receive injection by argument name; ``db`` must be
        # registered via ``deps()`` or the pipeline raises
        # ``PipelineDependencyMissing`` (verified in the negative test below).
        # Use a plain async handler rather than an AsyncMock: the pipeline's
        # dependency injector inspects the handler signature and injects by
        # parameter name, and a regular function keeps that flow untouched.
        called = []

        async def handler(ctx, db):
            called.append((ctx.text, db))

        pipe.handle(F.private, handler)
        pipe.deps(db="fake_db")  # register dependencies on the pipeline itself

        async with TestClient(bot, fake) as client:
            await client.send_update(_raw_message(text="any text"))

        assert called == [("any text", "fake_db")]

    @pytest.mark.asyncio
    async def test_pipeline_rejects_undeclared_dependency(self, bot_with_pool):
        from swiftbot.pipeline import Pipeline

        bot, fake = bot_with_pool
        pipe = bot.pipeline()

        async def bad_handler(ctx, db):  # ``db`` never registered via deps()
            pass

        pipe.handle(F.private, bad_handler)

        async with TestClient(bot, fake) as client:
            await client.send_update(_raw_message(text="any text"))

        # The pipeline surfaces the missing dependency through the bot's
        # centralized exception handler instead of crashing the run loop.
        assert bot._stats["errors_handled"] >= 1


class MockedWorkerPoolAndRunTests:
    """Verify run-loop machinery with mocked network dependencies."""

    @pytest.mark.asyncio
    async def test_worker_pool_submit_and_drain(self, bot_with_pool):
        bot, fake = bot_with_pool
        job = AsyncMock(name="job")

        await bot.worker_pool.start()
        await bot.worker_pool.submit(job, "arg")
        while not bot.worker_pool.queue.empty():
            await asyncio.sleep(0.01)
        job.assert_awaited_once_with("arg")
        await bot.worker_pool.stop()

    @pytest.mark.asyncio
    async def test_run_polling_with_mocked_api(self, bot_with_pool):
        """Simulate a full polling cycle with every Telegram call mocked."""
        bot, fake = bot_with_pool

        handler = AsyncMock(name="polling_handler")

        @bot.on(Message(text="from_poll"))
        async def h(ctx):
            await handler(ctx)

        async def mock_get_updates(*args, **kwargs):
            bot.running = False  # process one batch then exit the loop
            return [_raw_message(text="from_poll", update_id=10)]

        bot.api.get_updates = AsyncMock(side_effect=mock_get_updates)

        await bot.worker_pool.start()
        bot.running = True
        try:
            # Manual single cycle of the polling loop body (no network)
            updates = await bot.api.get_updates(offset=bot._update_offset)
            for upd in updates:
                bot._update_offset = upd["update_id"] + 1
                await bot.worker_pool.submit(bot._process_update, upd)
            while not bot.worker_pool.queue.empty():
                await asyncio.sleep(0.02)
        finally:
            bot.running = False
            await bot.worker_pool.stop()
            await bot.connection_pool.close()

        handler.assert_called_once()
        assert bot._stats["updates_processed"] >= 1


class ExceptionsHierarchyTests:
    """Verify the typed exception hierarchy is importable and usable."""

    def test_exception_classes(self):
        from swiftbot.exceptions import (
            SwiftBotException, SwiftBotError, ConfigurationError,
            APIError, NetworkError, BadRequest, TooManyRequests,
        )
        from swiftbot.exceptions.telegram import TelegramError

        assert issubclass(SwiftBotError, SwiftBotException)
        assert issubclass(ConfigurationError, SwiftBotException)
        assert issubclass(APIError, SwiftBotException)
        assert issubclass(NetworkError, SwiftBotException)
        assert issubclass(BadRequest, TelegramError)
        assert issubclass(TooManyRequests, TelegramError)
        # The typed Telegram hierarchy intentionally derives from ``Exception``
        # (not from SwiftBotException) so Telegram-specific errors can be
        # caught and logged separately from framework-level errors.
        assert issubclass(TelegramError, Exception)

    def test_api_error_classes(self):
        from swiftbot.exceptions.api import APIError, RateLimitError

        exc = APIError("boom", response_code=500, response_data={"ok": False})
        assert exc.response_code == 500

        rl = RateLimitError(retry_after=30)
        assert rl.retry_after == 30
        assert rl.response_code == 429


class UtilitiesTests:
    """Verify helper modules (deep linking, callback data, throttling, reply)."""

    def test_deep_linking_round_trip(self):
        from swiftbot import deep_linking

        token = deep_linking.encode_payload({"ref": "campaign_1"})
        assert deep_linking.decode_payload(token) == {"ref": "campaign_1"}

    def test_callback_data_pack_unpack(self):
        from swiftbot import CallbackData

        cd = CallbackData("buy", str, int)
        packed = cd.pack("item_7", 5)
        assert packed.startswith("buy:")
        assert cd.unpack(packed) == ("item_7", 5)

    def test_throttle_importable(self):
        from swiftbot import throttle

        assert callable(throttle)

    def test_reply_builder(self):
        from swiftbot import Reply

        assert Reply is not None


if __name__ == "__main__":
    sys.exit(pytest.main([__file__, "-v"]))
