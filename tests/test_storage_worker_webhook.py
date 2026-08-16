"""
Tests for FSM storage persistence, worker pool backpressure, and the
webhook server (must pass raw dicts, not wrapped objects).
"""

import asyncio
import json
import os
import sys
import tempfile

import pytest
from aiohttp import web
from aiohttp.test_utils import AioHTTPTestCase, TestClient, TestServer

from swiftbot.storage import (
    MemoryStorage, JSONFileStorage, StateManager, StorageError,
)
from swiftbot.connection.worker import WorkerPool
from swiftbot.webhook.server import WebhookServer
from swiftbot.client import SwiftBot
from swiftbot.update_types import Update
from swiftbot.exceptions import ConfigurationError


# ---------- Storage ----------

@pytest.mark.asyncio
async def test_memory_storage_basic():
    s = MemoryStorage()
    await s.set("user", "123:state", "step2")
    assert await s.get("user", "123:state") == "step2"
    await s.delete("user", "123:state")
    assert await s.get("user", "123:state") is None


@pytest.mark.asyncio
async def test_json_file_storage_persistence(tmp_path):
    path = str(tmp_path / "state.json")
    s1 = JSONFileStorage(path, flush_interval=0.05)
    await s1.set("user", "123:state", "step2")
    # Must survive a fresh instance (restart simulation)
    await asyncio.sleep(0.2)
    s2 = JSONFileStorage(path, flush_interval=0.05)
    assert await s2.get("user", "123:state") == "step2"
    await s2.close()
    # Raw file is valid JSON
    with open(path) as f:
        data = json.load(f)
    assert data["user"]["123:state"] == "step2"


@pytest.mark.asyncio
async def test_json_storage_corrupted_file_starts_fresh(tmp_path):
    path = str(tmp_path / "bad.json")
    with open(path, "w") as f:
        f.write("not json")
    s = JSONFileStorage(path)
    assert await s.get("user", "x") is None


@pytest.mark.asyncio
async def test_json_storage_empty_path_raises():
    with pytest.raises(StorageError):
        JSONFileStorage("")


@pytest.mark.asyncio
async def test_state_manager_ttl(tmp_path):
    s = JSONFileStorage(str(tmp_path / "s.json"), flush_interval=0.05)
    m = StateManager(s, ttl=0.1)
    await m.set_state(1, "waiting")
    assert await m.get_state(1) == "waiting"
    await asyncio.sleep(0.2)
    assert await m.get_state(1) is None  # expired


@pytest.mark.asyncio
async def test_state_manager_clear(tmp_path):
    s = JSONFileStorage(str(tmp_path / "s.json"), flush_interval=0.05)
    m = StateManager(s)
    await m.set_state(1, "x")
    await m.clear_state(1)
    assert await m.get_state(1) is None


# ---------- Worker pool ----------

@pytest.mark.asyncio
async def test_worker_pool_bounded_concurrency():
    pool = WorkerPool(num_workers=2, max_queue_size=2)
    await pool.start()
    results = []

    async def task(n):
        results.append(n)

    await pool.submit(task, 1)
    await pool.submit(task, 2)
    await pool.submit(task, 3)
    await asyncio.sleep(0.1)
    await pool.stop()
    assert sorted(results) == [1, 2, 3]
    assert pool.processed_count == 3


@pytest.mark.asyncio
async def test_worker_pool_backpressure_timeout():
    """A saturated pool must refuse new work instead of blocking forever.

    With ``num_workers=1`` and ``max_queue_size=1`` the pool can hold three
    items at most: one being executed plus one queued. Fill every slot, then
    verify both submission variants are refused.
    """
    pool = WorkerPool(num_workers=1, max_queue_size=1, backpressure_timeout=0.2)
    await pool.start()

    # Give the single worker a chance to start before we fill the queue.
    # Without this yield the worker may be scheduled only after a later
    # ``await``, which makes the queue-capacity arithmetic racy.
    await asyncio.sleep(0)

    released = asyncio.Event()       # gate so the blocking task stays running

    async def blocking_task():
        await released.wait()

    # Slot 1: taken by the worker immediately
    await pool.submit(blocking_task)
    # Slots 2 and 3: the physical queue (maxsize = max_queue_size + num_workers)
    await pool.submit(asyncio.sleep, 0.5)
    await pool.submit(asyncio.sleep, 0.5)

    assert pool.queue.full(), "pool must be fully saturated"

    # Any further submission must be refused with backpressure:
    with pytest.raises(asyncio.QueueFull):
        pool.submit_nowait(asyncio.sleep, 60)
    with pytest.raises(asyncio.TimeoutError):
        await pool.submit(asyncio.sleep, 60)

    # Drain everything cleanly before shutdown
    await asyncio.sleep(0.6)           # let the two queued sleeps finish
    released.set()                     # release the blocking in-flight task
    await asyncio.sleep(0.05)
    await pool.stop()


@pytest.mark.asyncio
async def test_worker_pool_dead_letter_captures_exception():
    pool = WorkerPool(num_workers=1, enable_dead_letter=True)
    await pool.start()

    async def failing():
        raise RuntimeError("boom")

    await pool.submit(failing)
    await asyncio.sleep(0.1)
    await pool.stop()
    assert pool.failed_count == 1
    assert pool.dead_letter_queue[0]["error"] == "boom"


@pytest.mark.asyncio
async def test_worker_pool_stop_drains_queue(tmp_path):
    pool = WorkerPool(num_workers=2, max_queue_size=100, enable_dead_letter=True)
    await pool.start()
    # Flood the queue with instant tasks
    for i in range(20):
        pool.submit_nowait(asyncio.sleep, 0)
    await pool.stop()
    # Nothing is silently lost: processed + failed + dead letters == submitted
    assert pool.processed_count + pool.failed_count + len(pool.dead_letter_queue) == 20


@pytest.mark.asyncio
async def test_worker_pool_invalid_config():
    with pytest.raises(ValueError):
        WorkerPool(num_workers=0)


# ---------- Webhook server ----------

class WebhookHarness:
    """Starts a WebhookServer against a bot and posts updates to it."""

    def __init__(self):
        self.bot = SwiftBot(token="123:ABC")
        self.bot.storage = None
        self.bot._state_manager = None
        self.processed = []

    async def start(self):
        # The worker pool only starts inside run_*() — but the webhook server
        # dispatches through it, so start it explicitly here.
        await self.bot.worker_pool.start()
        self.server = WebhookServer(
            client=self.bot, port=0, verify_signature=True, secret_token="secret"
        )
        # Minimal handler that records updates
        from swiftbot.types import Message as MsgEvent
        async def handler(ctx):
            self.processed.append(ctx.text)
        self.bot.router.add_handler(MsgEvent(), handler)
        self.runner = web.AppRunner(self.server.app)
        await self.runner.setup()
        self.site = web.TCPSite(self.runner, "127.0.0.1", 0)
        await self.site.start()
        port = self.site._server.sockets[0].getsockname()[1]
        self.base = f"http://127.0.0.1:{port}"

    async def post(self, payload):
        import aiohttp
        async with aiohttp.ClientSession() as s:
            async with s.post(self.base + "/webhook", json=payload,
                              headers={"X-Telegram-Bot-Api-Secret-Token": "secret"}) as r:
                return r.status

    async def stop(self):
        await self.site.stop()
        await self.runner.cleanup()
        await self.bot.worker_pool.stop()


@pytest.mark.asyncio
async def test_webhook_passes_raw_dict_not_updateobj():
    """Regression: previously every webhook update crashed with AttributeError."""
    h = WebhookHarness()
    await h.start()
    try:
        status = await h.post({
            "update_id": 1,
            "message": {
                "message_id": 5, "date": 1, "text": "hello",
                "chat": {"id": 1, "type": "private"},
                "from": {"id": 1, "is_bot": False, "first_name": "A"},
            },
        })
        assert status == 200
        # Wait for the dispatched task + worker to finish
        await asyncio.sleep(0.2)
        assert h.processed == ["hello"]
        assert h.server.requests_processed == 1
    finally:
        await h.stop()


@pytest.mark.asyncio
async def test_webhook_rejects_bad_json_and_bad_secret():
    h = WebhookHarness()
    await h.start()
    try:
        import aiohttp
        async with aiohttp.ClientSession() as s:
            # No secret header while verification is enabled -> 403 first
            r = await s.post(h.base + "/webhook", data="not json",
                             headers={"X-Telegram-Bot-Api-Secret-Token": "wrong"})
            assert r.status == 403
            r = await s.post(h.base + "/webhook", data="not json",
                             headers={"X-Telegram-Bot-Api-Secret-Token": "secret"})
            assert r.status == 400
            r = await s.post(h.base + "/webhook",
                             json={"update_id": 2},
                             headers={"X-Telegram-Bot-Api-Secret-Token": "wrong"})
            assert r.status == 403
            # Correct secret is accepted
            r = await s.post(h.base + "/webhook",
                             json={"update_id": 2},
                             headers={"X-Telegram-Bot-Api-Secret-Token": "secret"})
            assert r.status == 200
    finally:
        await h.stop()


# ---------- Client ----------

@pytest.mark.asyncio
async def test_webhook_reports_missing_aiohttp(monkeypatch):
    client = SwiftBot("test-token")
    monkeypatch.delitem(sys.modules, "swiftbot.webhook", raising=False)
    monkeypatch.delitem(sys.modules, "swiftbot.webhook.server", raising=False)
    monkeypatch.setitem(sys.modules, "aiohttp", None)

    with pytest.raises(
        ConfigurationError,
        match="Webhook mode requires the 'aiohttp' dependency",
    ):
        await client.run_webhook(webhook_url="https://example.com/webhook")


def test_client_token_validation():
    with pytest.raises(ConfigurationError):
        SwiftBot(token="")
    with pytest.raises(ConfigurationError):
        SwiftBot(token="   ")


def test_client_storage_validation():
    with pytest.raises(ConfigurationError):
        SwiftBot(token="123:ABC", storage="not a storage")


def test_client_default_memory_storage():
    bot = SwiftBot(token="123:ABC")
    assert isinstance(bot.storage, MemoryStorage)


def test_client_json_storage_wired():
    bot = SwiftBot(token="123:ABC", storage=JSONFileStorage("/tmp/sb-test.json"))
    assert isinstance(bot.storage, JSONFileStorage)
