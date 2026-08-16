import argparse
import asyncio
import gc
import json
import re
import statistics
import sys
import time
from pathlib import Path


def raw_update(update_id: int, text: str) -> dict:
    return {
        'update_id': update_id,
        'message': {
            'message_id': update_id,
            'date': 1000,
            'chat': {'id': 42, 'type': 'private'},
            'from': {'id': 7, 'is_bot': False, 'first_name': 'Tester'},
            'text': text,
        },
    }


def stream(n: int, routes: int, start: int = 1):
    return [raw_update(start + i, f'cmd{i % routes}') for i in range(n)]


async def build_swiftbot(routes: int):
    from swiftbot import SwiftBot
    from swiftbot.types import Message
    hits = [0]
    bot = SwiftBot(token='0000000000:TEST', worker_pool_size=1)

    for route in range(routes):
        expected = f'cmd{route}'

        async def handler(ctx, expected=expected):
            hits[0] += 1

        bot.on(Message(text=expected))(handler)

    async def dispatch(raw):
        await bot._process_update(raw)

    return bot, dispatch, hits, None


async def build_aiogram(routes: int):
    from aiogram import Bot, Dispatcher, Router, F
    hits = [0]
    bot = Bot(token='0000000000:TEST')
    dispatcher = Dispatcher()
    router = Router()

    for route in range(routes):
        expected = f'cmd{route}'

        async def handler(message, expected=expected):
            hits[0] += 1

        router.message.register(handler, F.text == expected)

    dispatcher.include_router(router)

    async def dispatch(raw):
        await dispatcher.feed_raw_update(bot, raw)

    async def cleanup():
        await bot.session.close()

    return bot, dispatch, hits, cleanup


async def build_ptb(routes: int):
    from telegram import Update
    from telegram.ext import Application, MessageHandler, filters
    hits = [0]
    app = Application.builder().token('0000000000:TEST').updater(None).build()

    for route in range(routes):
        expected = f'cmd{route}'
        pattern = re.compile(r'^' + re.escape(expected) + r'$')

        async def handler(update, context, expected=expected):
            hits[0] += 1

        app.add_handler(MessageHandler(filters.Regex(pattern), handler))

    # Avoid Application.initialize(), which intentionally performs Bot.get_me().
    app._initialized = True

    async def dispatch(raw):
        await app.process_update(Update.de_json(raw, app.bot))

    return app, dispatch, hits, None


async def build_telebot(routes: int):
    from telebot.async_telebot import AsyncTeleBot
    from telebot import types
    hits = [0]
    bot = AsyncTeleBot('0000000000:TEST', validate_token=False)

    for route in range(routes):
        expected = f'cmd{route}'

        def predicate(message, expected=expected):
            return message.text == expected

        async def handler(message, expected=expected):
            hits[0] += 1

        bot.message_handler(func=predicate)(handler)

    async def dispatch(raw):
        update = types.Update.de_json(json.dumps(raw))
        await bot.process_new_updates([update])

    return bot, dispatch, hits, None


async def build(framework: str, routes: int):
    return await {
        'swiftbot': build_swiftbot,
        'aiogram': build_aiogram,
        'ptb': build_ptb,
        'telebot': build_telebot,
    }[framework](routes)


async def measure(framework: str, routes: int, n: int, warmup: int, repeats: int):
    setup_start = time.perf_counter_ns()
    owner, dispatch, hits, cleanup = await build(framework, routes)
    setup_ms = (time.perf_counter_ns() - setup_start) / 1e6

    warm_stream = stream(warmup, routes, start=10_000)
    for raw in warm_stream:
        await dispatch(raw)

    seconds = []
    gc_was_enabled = gc.isenabled()
    gc.disable()
    try:
        for repetition in range(repeats):
            updates = stream(n, routes, start=1_000_000 * (repetition + 1))
            start_ns = time.perf_counter_ns()
            for raw in updates:
                await dispatch(raw)
            elapsed = (time.perf_counter_ns() - start_ns) / 1e9
            seconds.append(elapsed)
    finally:
        if gc_was_enabled:
            gc.enable()

    if cleanup is not None:
        await cleanup()

    expected_hits = warmup + (n * repeats)
    result = {
        'framework': framework,
        'routes': routes,
        'iterations_per_repeat': n,
        'warmup_iterations': warmup,
        'repeats': repeats,
        'python': sys.version.split()[0],
        'setup_ms': setup_ms,
        'repeat_seconds': seconds,
        'median_seconds': statistics.median(seconds),
        'p95_seconds': statistics.quantiles(seconds, n=20)[18] if len(seconds) >= 2 else seconds[0],
        'median_throughput_updates_per_second': n / statistics.median(seconds),
        'median_latency_microseconds_per_update': statistics.median(seconds) * 1e6 / n,
        'handler_hits': hits[0],
        'expected_handler_hits': expected_hits,
        'correct': hits[0] == expected_hits,
    }
    return result


async def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('framework', choices=['swiftbot', 'aiogram', 'ptb', 'telebot'])
    parser.add_argument('--routes', type=int, default=10)
    parser.add_argument('--iterations', type=int, default=5000)
    parser.add_argument('--warmup', type=int, default=250)
    parser.add_argument('--repeats', type=int, default=7)
    parser.add_argument('--output', type=Path)
    args = parser.parse_args()
    result = await measure(args.framework, args.routes, args.iterations, args.warmup, args.repeats)
    encoded = json.dumps(result, indent=2)
    print(encoded)
    if args.output:
        args.output.write_text(encoded + '\n', encoding='utf-8')


asyncio.run(main())
