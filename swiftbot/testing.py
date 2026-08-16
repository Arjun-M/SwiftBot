"""
SwiftBot - Testing harness (FakeBot / TestClient)

Unit-test handlers WITHOUT hitting Telegram's network:

    import asyncio
    from swiftbot import SwiftBot
    from swiftbot.testing import TestClient
    from swiftbot.types import Message
    from swiftbot.filters import Command

    bot = SwiftBot(token="0000000000:TEST")

    @bot.on(Message(text=Command("start")))
    async def start(ctx):
        await ctx.reply("Hello, world!")

    async def test_start_handler():
        async with TestClient(bot) as client:
            await client.send_update({
                "update_id": 1,
                "message": {
                    "message_id": 1,
                    "date": 1000,
                    "chat": {"id": 42, "type": "private"},
                    "from": {"id": 7, "is_bot": False, "first_name": "Tester"},
                    "text": "/start",
                },
            })

        # Assert what the bot tried to send:
        assert client.outgoing[0]["method"] == "sendMessage"
        assert client.outgoing[0]["params"]["text"] == "Hello, world!"
        assert client.outgoing[0]["params"]["chat_id"] == 42

The ``TestClient`` wires the bot's API layer to an in-memory fake pool that
records every request (method + params) and can be scripted to return
values or raise Telegram errors. Handlers run through the real worker pool,
router, filters, middleware and FSM storage — exactly as in production,
minus the network.

Copyright (c) 2026 Arjun-M/SwiftBot
"""

import asyncio
import json
from typing import Any, Callable, Dict, List, Optional

from .connection.pool import HTTPConnectionPool
from .exceptions.telegram import TelegramError


class _FakeResponse:
    """Minimal stand-in for ``httpx.Response`` used by ``TelegramAPI._request``."""

    __slots__ = ("status_code", "headers", "_data")

    def __init__(self, status_code: int, data: Dict[str, Any]):
        self.status_code = status_code
        self.headers = {}
        self._data = data

    def json(self) -> Dict[str, Any]:
        return self._data


class FakePool(HTTPConnectionPool):
    """
    In-memory fake of ``HTTPConnectionPool``. Every API call the bot makes is
    recorded in ``outgoing``; responses are served by ``scripts`` callbacks
    or by defaulting to ``{"ok": True, "result": ...}``.

    Usage::

        fake = FakePool()
        fake.script("sendMessage", result={"message_id": 1})
        bot = SwiftBot(token="...", connection_pool=fake)
    """

    def __init__(self, timeout: float = 1.0):
        # Skip the real httpx initialization entirely — nothing needs it.
        self.proxy = None
        self.max_connections = 0
        self.max_keepalive = 0
        self.enable_http2 = False
        self.max_retries = 3
        self.backoff_factor = 0
        self.transport = None
        self._client = None
        self._lock = asyncio.Lock()
        self.timeout = timeout

        self.outgoing: List[Dict[str, Any]] = []
        # method -> list of scripted responses (popped in order)
        self.scripts: Dict[str, List[Any]] = {}
        # Optional global handler: async def (method, params) -> result|response|raise
        self.hook: Optional[Callable] = None
        # Default return value when nothing is scripted
        self.default_result: Any = True

    def script(self, method: str, *, result: Any = True, error: Optional[Dict] = None):
        """
        Queue a scripted response for an API method.

        Args:
            method: Telegram method name, e.g. ``"sendMessage"``.
            result: Success payload returned under ``"result"``.
            error: If given, the call fails with a ``TelegramError`` built
                from this response (e.g. ``{"ok": False, "error_code": 404,
                "description": "Not Found"}``).
        """
        entry = {"result": result, "error": error}
        self.scripts.setdefault(method, []).append(entry)

    async def initialize(self):
        pass  # nothing to initialize

    async def close(self):
        pass

    async def post(self, url: str, json=None, files=None):
        """Record the request and serve a scripted/default response."""
        method = url.rsplit("/", 1)[-1]
        params = json if json is not None else {}
        params = {k: __import__("json").loads(v)
                  if isinstance(v, str) and v[:1] in "{[" else v
                  for k, v in params.items()}
        record = {"method": method, "params": params,
                  "files": list(files.keys()) if files else None}
        self.outgoing.append(record)

        if self.hook is not None:
            outcome = self.hook(method, params)
            if asyncio.iscoroutine(outcome):
                outcome = await outcome
            if isinstance(outcome, BaseException):
                raise outcome
            if isinstance(outcome, _FakeResponse):
                return outcome
            # Treat non-response outcomes as the success result
            return _FakeResponse(200, {"ok": True, "result": outcome})

        entry = (self.scripts.get(method) or [None])[0]
        if entry is not None and self.scripts[method]:
            entry = self.scripts[method].pop(0)

        if entry and entry.get("error"):
            record["error_code"] = entry["error"].get("error_code", 400)
            record["error_description"] = entry["error"].get("description", "")
            return _FakeResponse(entry["error"].get("error_code", 400),
                                 entry["error"])
        result = entry["result"] if entry else self.default_result
        return _FakeResponse(200, {"ok": True, "result": result})

    @property
    def error_count(self) -> int:
        """Number of outgoing calls that returned a scripted error."""
        return sum(
            1 for r in self.outgoing if r.get("error_code")
        )

    get = post  # both verbs handled identically in the fake


class TestClient:
    """
    Context-manager wrapper that runs a bot in test mode.

    Example::

        async with TestClient(bot) as client:
            await client.send_update({...})          # simulate an update
            await client.send_message(text="...")    # call API directly
            assert client.outgoing[-1]["method"] == "sendMessage"

    The bot's worker pool is started so handlers run as in production.
    Call ``drain()`` to wait for all queued updates to finish processing.
    """

    def __init__(self, bot: "SwiftBot", fake_pool: Optional[FakePool] = None):
        self.bot = bot
        self.pool: FakePool = fake_pool or FakePool()
        self.outgoing = self.pool.outgoing
        bot.connection_pool = self.pool
        # Make the API layer use the (fake) pool it already references via
        # ``self.api.pool`` — replace it here too.
        bot.api.pool = self.pool

    async def __aenter__(self):
        await self.bot.worker_pool.start()
        return self

    async def __aexit__(self, *exc):
        await self.bot.worker_pool.stop()

    async def send_update(self, raw_update: Dict[str, Any]):
        """Feed one raw Telegram update and wait for handler completion."""
        await self.bot.worker_pool.submit(self.bot._process_update, raw_update)
        await self.drain()

    async def send_updates(self, raw_updates: List[Dict[str, Any]]):
        """Feed a batch of raw updates and wait for all handlers to finish."""
        for raw_update in raw_updates:
            await self.bot.worker_pool.submit(self.bot._process_update, raw_update)
        await self.drain()

    async def send_message(self, **params) -> Dict[str, Any]:
        """Call the API directly (goes through the fake pool)."""
        result = await self.bot.api._request("sendMessage", **params)
        return result

    async def drain(self, pause: float = 0.02):
        """Wait until all submitted work has called ``queue.task_done()``.

        ``pause`` is retained for source compatibility but is no longer used.
        ``asyncio.Queue.join`` waits for both queued and in-flight work, unlike
        polling ``queue.empty()``, which can return too early after a worker
        takes an item but before its handler completes.
        """
        await self.bot.worker_pool.queue.join()
