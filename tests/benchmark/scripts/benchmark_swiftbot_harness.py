import argparse
import asyncio
import json
import statistics
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


async def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--routes', type=int, default=10)
    parser.add_argument('--iterations', type=int, default=1000)
    parser.add_argument('--warmup', type=int, default=100)
    parser.add_argument('--repeats', type=int, default=5)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()

    from swiftbot import SwiftBot
    from swiftbot.testing import TestClient
    from swiftbot.types import Message

    bot = SwiftBot(token='0000000000:TEST', worker_pool_size=1)
    hits = [0]
    for route in range(args.routes):
        expected = f'cmd{route}'

        async def handler(ctx, expected=expected):
            hits[0] += 1

        bot.on(Message(text=expected))(handler)

    async with TestClient(bot) as client:
        for i in range(args.warmup):
            await client.send_update(raw_update(10000 + i, f'cmd{i % args.routes}'))
        seconds = []
        for repeat in range(args.repeats):
            start = time.perf_counter_ns()
            for i in range(args.iterations):
                await client.send_update(raw_update(1000000 * (repeat + 1) + i, f'cmd{i % args.routes}'))
            seconds.append((time.perf_counter_ns() - start) / 1e9)

    result = {
        'framework': 'swiftbot',
        'mode': 'documented_TestClient_harness',
        'routes': args.routes,
        'iterations_per_repeat': args.iterations,
        'warmup_iterations': args.warmup,
        'repeats': args.repeats,
        'repeat_seconds': seconds,
        'median_seconds': statistics.median(seconds),
        'median_throughput_updates_per_second': args.iterations / statistics.median(seconds),
        'median_latency_microseconds_per_update': statistics.median(seconds) * 1e6 / args.iterations,
        'handler_hits': hits[0],
        'expected_handler_hits': args.warmup + args.iterations * args.repeats,
        'correct': hits[0] == args.warmup + args.iterations * args.repeats,
    }
    args.output.write_text(json.dumps(result, indent=2) + '\n', encoding='utf-8')
    print(json.dumps(result, indent=2))


asyncio.run(main())
