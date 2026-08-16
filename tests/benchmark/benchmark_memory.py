"""Fresh-process RSS benchmark using the public raw-update surfaces."""

import argparse
import asyncio
import gc
import json
import resource
import sys
import time
from pathlib import Path


def rss_kib() -> int:
    with open("/proc/self/status", encoding="utf-8") as handle:
        for line in handle:
            if line.startswith("VmRSS:"):
                return int(line.split()[1])
    return -1


def maxrss_kib() -> int:
    return int(resource.getrusage(resource.RUSAGE_SELF).ru_maxrss)


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


async def build_swiftbot(routes: int):
    from swiftbot import SwiftBot
    from swiftbot.testing import TestClient
    from swiftbot.types import Message

    hits = [0]
    bot = SwiftBot(token="0000000000:TEST", worker_pool_size=1)
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

    return dispatch_batch, hits, cleanup, "public TestClient.send_updates"


async def build_aiogram(routes: int):
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

    return dispatch_batch, hits, cleanup, "public Dispatcher.feed_raw_update"


async def build_ptb(routes: int):
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
    app._initialized = True

    async def dispatch_batch(updates):
        for raw in updates:
            await app.process_update(Update.de_json(raw, app.bot))

    async def cleanup():
        return None

    return dispatch_batch, hits, cleanup, "public Application.process_update"


async def build_telebot(routes: int):
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

    return dispatch_batch, hits, cleanup, "public AsyncTeleBot.process_new_updates"


BUILDERS = {
    "swiftbot": build_swiftbot,
    "aiogram": build_aiogram,
    "ptb": build_ptb,
    "telebot": build_telebot,
}


async def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("framework", choices=sorted(BUILDERS))
    parser.add_argument("--routes", type=int, default=10)
    parser.add_argument("--updates", type=int, default=10000)
    parser.add_argument("--batch-size", type=int, default=100)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()

    gc.collect()
    process_start_rss = rss_kib()
    build_start_ns = time.perf_counter_ns()
    dispatch_batch, hits, cleanup, api_surface = await BUILDERS[args.framework](args.routes)
    build_elapsed_ms = (time.perf_counter_ns() - build_start_ns) / 1e6
    after_build_rss = rss_kib()
    peak_samples = [after_build_rss]

    for start in range(0, args.updates, args.batch_size):
        count = min(args.batch_size, args.updates - start)
        updates = [raw_update(start + i + 1, f"cmd{(start + i) % args.routes}") for i in range(count)]
        await dispatch_batch(updates)
        peak_samples.append(rss_kib())
    after_workload_rss = rss_kib()
    peak_rss = max(peak_samples)
    await cleanup()
    gc.collect()

    result = {
        "benchmark": "public_raw_update_memory",
        "framework": args.framework,
        "routes": args.routes,
        "updates": args.updates,
        "batch_size": args.batch_size,
        "python": sys.version.split()[0],
        "gc_mode": "enabled",
        "api_surface": api_surface,
        "process_start_rss_kib": process_start_rss,
        "after_build_rss_kib": after_build_rss,
        "after_workload_rss_kib": after_workload_rss,
        "peak_sampled_rss_kib": peak_rss,
        "build_rss_delta_kib": after_build_rss - process_start_rss,
        "workload_rss_delta_kib": after_workload_rss - after_build_rss,
        "peak_rss_delta_from_build_start_kib": peak_rss - process_start_rss,
        "ru_maxrss_kib": maxrss_kib(),
        "build_elapsed_ms": build_elapsed_ms,
        "handler_hits": hits[0],
        "expected_handler_hits": args.updates,
        "correct": hits[0] == args.updates,
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(result, indent=2))


asyncio.run(main())
