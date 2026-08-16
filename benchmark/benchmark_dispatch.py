"""Public raw-update benchmark for SwiftBot and comparable Telegram frameworks.

This benchmark intentionally measures the public offline update-processing surface
of each framework, including its normal raw-update parsing and routing costs.
It is not a claim of end-to-end Telegram performance.
"""

import argparse
import asyncio
import gc
import json
import statistics
import sys
import time
from pathlib import Path


def raw_update(update_id: int, text: str) -> dict:
    return {
        "update_id": update_id,
        "message": {
            "message_id": update_id,
            "date": 1000,
            "chat": {"id": 42, "type": "private"},
            "from": {"id": 7, "is_bot": False, "first_name": "Tester"},
            "text": text,
        },
    }


def stream(n: int, routes: int, start: int = 1) -> list[dict]:
    return [raw_update(start + i, f"cmd{i % routes}") for i in range(n)]


async def build_swiftbot(routes: int, worker_count: int):
    from swiftbot import SwiftBot
    from swiftbot.testing import TestClient
    from swiftbot.types import Message

    hits = [0]
    bot = SwiftBot(
        token="0000000000:TEST",
        worker_pool_size=worker_count,
    )
    for route in range(routes):
        expected = f"cmd{route}"

        async def handler(ctx, expected=expected):
            hits[0] += 1

        bot.on(Message(text=expected))(handler)

    client = TestClient(bot)
    await client.__aenter__()

    async def dispatch_batch(updates):
        await client.send_updates(updates)

    async def cleanup():
        await client.__aexit__(None, None, None)

    return dispatch_batch, hits, cleanup, {
        "api_surface": "public TestClient.send_updates",
        "worker_count": worker_count,
        "matching": "exact text",
    }


async def build_aiogram(routes: int, worker_count: int):
    from aiogram import Bot, Dispatcher, F, Router

    hits = [0]
    bot = Bot(token="0000000000:TEST")
    dispatcher = Dispatcher()
    router = Router()
    for route in range(routes):
        expected = f"cmd{route}"

        async def handler(message, expected=expected):
            hits[0] += 1

        router.message.register(handler, F.text == expected)
    dispatcher.include_router(router)

    async def dispatch_batch(updates):
        for raw in updates:
            await dispatcher.feed_raw_update(bot, raw)

    async def cleanup():
        await bot.session.close()

    return dispatch_batch, hits, cleanup, {
        "api_surface": "public Dispatcher.feed_raw_update",
        "worker_count": 1,
        "matching": "exact text",
    }


async def build_ptb(routes: int, worker_count: int):
    from telegram import Update
    from telegram.ext import Application, MessageHandler, filters

    hits = [0]

    class ExactTextFilter(filters.MessageFilter):
        def __init__(self, expected):
            super().__init__(name=f"ExactText({expected})")
            self.expected = expected

        def filter(self, message):
            return message.text == self.expected

    app = Application.builder().token("0000000000:TEST").updater(None).build()
    for route in range(routes):
        expected = f"cmd{route}"

        async def handler(update, context, expected=expected):
            hits[0] += 1

        app.add_handler(MessageHandler(ExactTextFilter(expected), handler))
    # Avoid Application.initialize(), which intentionally calls Bot.get_me().
    app._initialized = True

    async def dispatch_batch(updates):
        for raw in updates:
            await app.process_update(Update.de_json(raw, app.bot))

    async def cleanup():
        return None

    return dispatch_batch, hits, cleanup, {
        "api_surface": "public Application.process_update",
        "worker_count": 1,
        "matching": "exact text custom MessageFilter",
    }


async def build_telebot(routes: int, worker_count: int):
    import json as json_module

    from telebot import types
    from telebot.async_telebot import AsyncTeleBot

    hits = [0]
    bot = AsyncTeleBot("0000000000:TEST", validate_token=False)
    for route in range(routes):
        expected = f"cmd{route}"

        def predicate(message, expected=expected):
            return message.text == expected

        async def handler(message, expected=expected):
            hits[0] += 1

        bot.message_handler(func=predicate)(handler)

    async def dispatch_batch(updates):
        parsed = [types.Update.de_json(json_module.dumps(raw)) for raw in updates]
        await bot.process_new_updates(parsed)

    async def cleanup():
        return None

    return dispatch_batch, hits, cleanup, {
        "api_surface": "public AsyncTeleBot.process_new_updates",
        "worker_count": 1,
        "matching": "exact text predicate",
    }


BUILDERS = {
    "swiftbot": build_swiftbot,
    "aiogram": build_aiogram,
    "ptb": build_ptb,
    "telebot": build_telebot,
}


async def measure(framework: str, routes: int, n: int, warmup: int, repeats: int, worker_count: int):
    setup_start = time.perf_counter_ns()
    dispatch_batch, hits, cleanup, adapter = await BUILDERS[framework](routes, worker_count)
    setup_ms = (time.perf_counter_ns() - setup_start) / 1e6

    await dispatch_batch(stream(warmup, routes, start=10_000))
    seconds = []
    for repetition in range(repeats):
        updates = stream(n, routes, start=1_000_000 * (repetition + 1))
        start_ns = time.perf_counter_ns()
        await dispatch_batch(updates)
        seconds.append((time.perf_counter_ns() - start_ns) / 1e9)
    await cleanup()

    expected_hits = warmup + n * repeats
    median = statistics.median(seconds)
    return {
        "benchmark": "public_raw_update_dispatch",
        "framework": framework,
        "routes": routes,
        "iterations_per_repeat": n,
        "warmup_iterations": warmup,
        "repeats": repeats,
        "python": sys.version.split()[0],
        "gc_mode": "enabled",
        "setup_ms": setup_ms,
        "repeat_seconds": seconds,
        "median_seconds": median,
        "p95_seconds": statistics.quantiles(seconds, n=20)[18] if len(seconds) >= 2 else seconds[0],
        "median_throughput_updates_per_second": n / median,
        "median_latency_microseconds_per_update": median * 1e6 / n,
        "handler_hits": hits[0],
        "expected_handler_hits": expected_hits,
        "correct": hits[0] == expected_hits,
        "adapter": adapter,
    }


async def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("framework", choices=sorted(BUILDERS))
    parser.add_argument("--routes", type=int, default=10)
    parser.add_argument("--iterations", type=int, default=2000)
    parser.add_argument("--warmup", type=int, default=100)
    parser.add_argument("--repeats", type=int, default=5)
    parser.add_argument("--worker-count", type=int, default=1)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    if args.framework != "swiftbot" and args.worker_count != 1:
        parser.error("--worker-count other than 1 is only valid for SwiftBot")
    result = await measure(
        args.framework,
        args.routes,
        args.iterations,
        args.warmup,
        args.repeats,
        args.worker_count,
    )
    encoded = json.dumps(result, indent=2)
    print(encoded)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(encoded + "\n", encoding="utf-8")


asyncio.run(main())
