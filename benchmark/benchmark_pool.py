import argparse
import asyncio
import json
import statistics
import time
from pathlib import Path

from swiftbot import SwiftBot
from swiftbot.connection.worker import WorkerPool
from swiftbot.types import Message


def raw_update(update_id: int) -> dict:
    return {
        'update_id': update_id,
        'message': {
            'message_id': update_id,
            'date': 1000,
            'chat': {'id': 42, 'type': 'private'},
            'from': {'id': 7, 'is_bot': False, 'first_name': 'Tester'},
            'text': 'work',
        },
    }


async def run_throughput(workers: int, updates: int, delay: float, queue_size: int, repeats: int):
    measurements = []
    completed = []
    submit_errors_per_repeat = []
    for repeat in range(repeats):
        bot = SwiftBot(token='0000000000:TEST', worker_pool_size=workers)
        bot.worker_pool = WorkerPool(
            num_workers=workers,
            max_queue_size=queue_size,
            enable_dead_letter=True,
            backpressure_timeout=5.0,
        )
        done = [0]

        @bot.on(Message(text='work'))
        async def work_handler(ctx):
            await asyncio.sleep(delay)
            done[0] += 1

        await bot.worker_pool.start()
        start = time.perf_counter_ns()
        submit_errors = 0
        for index in range(updates):
            try:
                await bot.worker_pool.submit(bot._process_update, raw_update(repeat * updates + index + 1))
            except Exception:
                submit_errors += 1
        await bot.worker_pool.queue.join()
        elapsed = (time.perf_counter_ns() - start) / 1e9
        await bot.worker_pool.stop(timeout=10)
        measurements.append(elapsed)
        completed.append(done[0])
        submit_errors_per_repeat.append(submit_errors)

    median = statistics.median(measurements)
    return {
        'workers': workers,
        'updates': updates,
        'handler_delay_seconds': delay,
        'queue_size': queue_size,
        'repeats': repeats,
        'repeat_seconds': measurements,
        'median_seconds': median,
        'median_throughput_updates_per_second': updates / median,
        'completed_per_repeat': completed,
        'submit_errors_per_repeat': submit_errors_per_repeat,
        'correct': all(value == updates for value in completed),
    }


async def run_backpressure(updates: int, delay: float, workers: int, queue_size: int, timeout: float):
    bot = SwiftBot(token='0000000000:TEST', worker_pool_size=workers)
    bot.worker_pool = WorkerPool(
        num_workers=workers,
        max_queue_size=queue_size,
        enable_dead_letter=True,
        backpressure_timeout=timeout,
    )

    done = [0]

    @bot.on(Message(text='work'))
    async def work_handler(ctx):
        await asyncio.sleep(delay)
        done[0] += 1

    await bot.worker_pool.start()
    start = time.perf_counter_ns()

    async def submit_one(index):
        try:
            await bot.worker_pool.submit(bot._process_update, raw_update(index + 1))
            return 'accepted'
        except asyncio.TimeoutError:
            return 'timed_out'
        except Exception as exc:
            return f'error:{type(exc).__name__}'

    outcomes = await asyncio.gather(*(submit_one(index) for index in range(updates)))
    submit_elapsed = (time.perf_counter_ns() - start) / 1e9
    await bot.worker_pool.queue.join()
    await bot.worker_pool.stop(timeout=10)

    accepted = outcomes.count('accepted')
    timed_out = outcomes.count('timed_out')
    return {
        'workers': workers,
        'updates_offered': updates,
        'handler_delay_seconds': delay,
        'queue_size': queue_size,
        'backpressure_timeout_seconds': timeout,
        'submit_elapsed_seconds': submit_elapsed,
        'accepted': accepted,
        'timed_out': timed_out,
        'other_outcomes': [item for item in outcomes if item not in {'accepted', 'timed_out'}],
        'completed': done[0],
        'dead_letters_after_stop': len(bot.worker_pool.get_dead_letters()),
        'bounded_behavior_observed': timed_out > 0,
        'no_silent_loss': done[0] == accepted,
    }


async def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--updates', type=int, default=400)
    parser.add_argument('--delay', type=float, default=0.002)
    parser.add_argument('--queue-size', type=int, default=100)
    parser.add_argument('--repeats', type=int, default=3)
    parser.add_argument('--backpressure-updates', type=int, default=20)
    parser.add_argument('--backpressure-delay', type=float, default=0.05)
    parser.add_argument('--backpressure-timeout', type=float, default=0.005)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()

    scaling = []
    for workers in [1, 2, 4, 8]:
        scaling.append(await run_throughput(workers, args.updates, args.delay, args.queue_size, args.repeats))
    backpressure = await run_backpressure(
        args.backpressure_updates,
        args.backpressure_delay,
        workers=1,
        queue_size=2,
        timeout=args.backpressure_timeout,
    )
    result = {
        'benchmark': 'swiftbot_worker_pool',
        'python': __import__('sys').version.split()[0],
        'concurrency_scaling': scaling,
        'backpressure': backpressure,
    }
    args.output.write_text(json.dumps(result, indent=2) + '\n', encoding='utf-8')
    print(json.dumps(result, indent=2))


asyncio.run(main())
