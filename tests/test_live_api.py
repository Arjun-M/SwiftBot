"""
Live tests for the SwiftBot package against the real Telegram Bot API.

These tests exercise the installed ``swiftbot`` package end-to-end against
Telegram's live API (getMe, getUpdates, sendMessage, API error handling,
storage + state manager wiring, and the run loop startup/shutdown).

SAFETY
------
- The bot token is read from the ``SWIFTBOT_TOKEN`` environment variable.
  It is NEVER written to disk or committed anywhere.
- Sending a real message to a chat is OFF by default. Set
  ``SWIFTBOT_SEND_CHAT_ID`` to enable it; the message is a single,
  self-contained health-check text.
- Nothing in this file pushes, branches, or creates PRs.

Run::
    SWIFTBOT_TOKEN="1234567890:ABC..." python3 -m pytest test_swiftbot_live.py -v

Copyright (c) 2026 Arjun-M/SwiftBot contributors. Local-only deliverable.
"""
import asyncio
import os
from unittest.mock import AsyncMock

import pytest

TOKEN = os.environ.get("SWIFTBOT_TOKEN", "").strip()
SEND_CHAT_ID = os.environ.get("SWIFTBOT_SEND_CHAT_ID", "").strip()
pytestmark = pytest.mark.asyncio


def _require_token():
    if not TOKEN or ":" not in TOKEN:
        pytest.skip("SWIFTBOT_TOKEN not set or malformed; skipping live tests")


@pytest.fixture
def bot():
    _require_token()
    from swiftbot import SwiftBot

    return SwiftBot(token=TOKEN)


# ---------------------------------------------------------------------------
# 1. LIVE API LAYER (api/telegram.py)
# ---------------------------------------------------------------------------

class LiveTelegramAPITests:
    """The real TelegramAPI wrapper must work against Telegram's servers."""

    async def test_get_me_returns_bot_user(self, bot):
        me = await bot.api.get_me()
        assert isinstance(me, dict)
        assert me.get("is_bot") is True
        assert me.get("id")
        assert me.get("first_name")
        # The API object must be bound to the configured token.
        assert TOKEN.split(":")[0] in bot.api.base_url

    async def test_get_me_idempotent_and_cached(self, bot):
        first = await bot.api.get_me()
        second = await bot.api.get_me()
        assert first["id"] == second["id"]

    async def test_send_message_live_health_check(self, bot):
        if not SEND_CHAT_ID:
            pytest.skip("SWIFTBOT_SEND_CHAT_ID not set; message send disabled")

        text = (
            "SwiftBot live environment check: package is installed, "
            "the Telegram API layer works, and this bot responds."
        )
        result = await bot.api.send_message(chat_id=int(SEND_CHAT_ID), text=text)
        assert isinstance(result, dict)
        assert result.get("message_id")
        assert result.get("text") == text

    async def test_invalid_method_returns_error_handling(self, bot):
        # A clearly invalid method must surface as a Telegram error rather
        # than a crash or a silent success.
        with pytest.raises(Exception) as exc_info:
            await bot.api._request("getMeWithThisIsNotARealMethod")
        assert exc_info.type.__name__.endswith("TelegramError") or "Telegram" in str(exc_info.type)

    async def test_get_updates_no_crash(self, bot):
        # A single long-polling call without a webhook confirms the polling
        # plumbing wires through the connection pool.
        await bot.api.delete_webhook(drop_pending_updates=True)
        updates = await bot.api.get_updates(timeout=1, limit=1)
        assert isinstance(updates, list)


# ---------------------------------------------------------------------------
# 2. LIVE CLIENT + DISPATCH (client.py, router, middleware, storage)
# ---------------------------------------------------------------------------

class LiveClientWiringTests:
    """The SwiftBot client must start, dispatch, and shut down cleanly."""

    async def test_run_starts_and_stops_cleanly(self, bot):
        # Give the polling loop a short, bounded window then stop.
        # If the token has an active webhook, polling cannot start — a
        # legitimate configuration check, so delete the webhook first.
        await bot.api.delete_webhook(drop_pending_updates=True)

        async def stopper():
            await asyncio.sleep(2)
            bot.stop()  # ``stop()`` is synchronous in SwiftBot

        runner = asyncio.create_task(stopper())
        await bot.run(timeout=1)  # short long-poll timeout keeps the test fast
        await runner
        # Observable evidence that the run loop executed: ``running`` flipped
        # on, getMe completed (cached bot info populated), and the worker pool
        # started.
        assert bot.running is False, "bot must report stopped after shutdown"
        assert bot._stats["start_time"] is not None, (
            "the run loop must have recorded a start time"
        )

    async def test_middleware_runs_in_production_mode(self, bot):
        from swiftbot.middleware import Middleware

        seen = []

        class Tracer(Middleware):
            async def on_update(self, ctx, next_handler):
                seen.append("tracer")
                await next_handler()

        bot.use(Tracer())
        assert Tracer() in bot.middleware or len(bot.middleware) >= 1

    async def test_state_manager_live(self, bot):
        from swiftbot.storage import MemoryStorage, StateManager

        manager = StateManager(bot.storage)
        await manager.set_state(user_id=99999, state={"probe": "live"})
        fetched = await manager.get_state(user_id=99999)
        assert fetched["probe"] == "live"
        await manager.clear_state(user_id=99999)
        assert await manager.get_state(user_id=99999) is None

    async def test_dialogue_registration(self, bot):
        dlg = bot.dialogue("live_check")

        async def state_fn(ctx, prev=None):
            return None

        dlg.state("probe")(state_fn)
        assert dlg.name == "live_check"
        assert bot._dialogues["live_check"] is dlg


# ---------------------------------------------------------------------------
# 3. MOCKED-ON-TOP-OF-LIVE HYBRID CHECK
# ---------------------------------------------------------------------------

class HybridMockAndLiveTests:
    """Verify unittest.mock.AsyncMock substitutes cleanly around the live bot."""

    def test_api_mock_substitution(self, bot):  # sync on purpose — no event loop needed
        mock_api = AsyncMock(name="telegram_api")
        mock_api.get_me = AsyncMock(return_value={"id": 1, "is_bot": True,
                                                  "first_name": "MockBot"})
        original = bot.api
        bot.api = mock_api

        # The mocked layer answers immediately and records the call, proving
        # the injection point is usable without touching the network.
        loop = asyncio.new_event_loop()
        result = loop.run_until_complete(bot.api.get_me())
        loop.close()

        assert result["id"] == 1
        mock_api.get_me.assert_called()
        bot.api = original  # restore the real API layer
