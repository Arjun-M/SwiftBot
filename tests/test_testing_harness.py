import asyncio

import pytest

from swiftbot import SwiftBot
from swiftbot.testing import TestClient
from swiftbot.types import Message


def raw_message(text="slow"):
    return {
        "update_id": 1,
        "message": {
            "message_id": 1,
            "date": 1000,
            "chat": {"id": 42, "type": "private"},
            "from": {"id": 7, "is_bot": False, "first_name": "Tester"},
            "text": text,
        },
    }


@pytest.mark.asyncio
async def test_testclient_waits_for_in_flight_handler():
    bot = SwiftBot(token="0000000000:TEST", worker_pool_size=1)
    completed = []

    @bot.on(Message(text="slow"))
    async def slow_handler(ctx):
        await asyncio.sleep(0.01)
        completed.append(True)

    async with TestClient(bot) as client:
        await client.send_update(raw_message())
        assert completed == [True]


@pytest.mark.asyncio
async def test_testclient_send_updates_waits_for_entire_batch():
    bot = SwiftBot(token="0000000000:TEST", worker_pool_size=2)
    completed = []

    @bot.on(Message(text="slow"))
    async def slow_handler(ctx):
        await asyncio.sleep(0.005)
        completed.append(True)

    async with TestClient(bot) as client:
        await client.send_updates([raw_message(), raw_message()])
        assert len(completed) == 2
