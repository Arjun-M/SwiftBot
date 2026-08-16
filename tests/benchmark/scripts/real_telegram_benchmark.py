import argparse
import asyncio
import gc
import json
import resource
import statistics
import sys
import time
from pathlib import Path


def read_token(path: Path) -> str:
    raw = path.read_text(encoding='utf-8').strip()
    if '=' in raw and raw.split('=', 1)[0].strip().upper() in {'BOT_TOKEN', 'SWIFTBOT_TOKEN', 'TOKEN'}:
        raw = raw.split('=', 1)[1].strip()
    if not raw or ':' not in raw:
        raise ValueError('The token file does not contain a plausible Telegram bot token.')
    return raw


def rss_kib() -> int:
    with open('/proc/self/status', encoding='utf-8') as handle:
        for line in handle:
            if line.startswith('VmRSS:'):
                return int(line.split()[1])
    return -1


async def measure_call(label, call, repeats):
    samples = []
    errors = []
    for _ in range(2):
        try:
            await call()
        except Exception:
            pass
    for _ in range(repeats):
        start = time.perf_counter_ns()
        try:
            value = await call()
            samples.append((time.perf_counter_ns() - start) / 1e6)
        except Exception as exc:
            errors.append({'type': type(exc).__name__, 'message': str(exc)[:240]})
    result = {
        'label': label,
        'successful_calls': len(samples),
        'failed_calls': len(errors),
        'median_ms': statistics.median(samples) if samples else None,
        'p95_ms': statistics.quantiles(samples, n=20)[18] if len(samples) >= 2 else (samples[0] if samples else None),
        'min_ms': min(samples) if samples else None,
        'max_ms': max(samples) if samples else None,
        'samples_ms': samples,
        'errors': errors,
    }
    return result


async def concurrency_probe(api_call, level):
    start = time.perf_counter_ns()
    results = await asyncio.gather(*(api_call() for _ in range(level)), return_exceptions=True)
    elapsed_ms = (time.perf_counter_ns() - start) / 1e6
    failures = [
        {'type': type(value).__name__, 'message': str(value)[:240]}
        for value in results if isinstance(value, BaseException)
    ]
    return {
        'concurrency': level,
        'wall_time_ms': elapsed_ms,
        'completed': level - len(failures),
        'failed': len(failures),
        'failures': failures,
    }


async def main():
    parser = argparse.ArgumentParser(description='Read-only real Telegram API benchmark for SwiftBot.')
    parser.add_argument('--token-file', type=Path, required=True)
    parser.add_argument('--chat-id', type=int, required=True)
    parser.add_argument('--expected-username', default='')
    parser.add_argument('--getme-repeats', type=int, default=20)
    parser.add_argument('--getchat-repeats', type=int, default=5)
    parser.add_argument('--getupdates-repeats', type=int, default=5)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()

    # Import after argument parsing; no credential is printed.
    from swiftbot import SwiftBot

    gc.collect()
    start_rss = rss_kib()
    token = read_token(args.token_file)
    bot = SwiftBot(token=token, worker_pool_size=8, max_connections=16, enable_http2=True)
    build_rss = rss_kib()
    build_ms_start = time.perf_counter_ns()
    await bot.connection_pool.initialize()
    build_ms = (time.perf_counter_ns() - build_ms_start) / 1e6

    async def get_me():
        return await bot.api.get_me()

    async def get_chat():
        return await bot.api.get_chat(args.chat_id)

    async def get_updates():
        return await bot.api.get_updates(limit=1, timeout=0)

    identity = {'status': 'not_run'}
    chat_check = {'status': 'not_run'}
    update_samples = []
    concurrency = []
    try:
        try:
            me = await get_me()
            identity = {
                'status': 'ok',
                'id': me.get('id') if isinstance(me, dict) else None,
                'is_bot': me.get('is_bot') if isinstance(me, dict) else None,
                'username': me.get('username') if isinstance(me, dict) else None,
                'first_name': me.get('first_name') if isinstance(me, dict) else None,
            }
        except Exception as exc:
            identity = {'status': 'error', 'error_type': type(exc).__name__, 'error': str(exc)[:240]}

        try:
            chat = await get_chat()
            actual_username = chat.get('username') if isinstance(chat, dict) else None
            chat_check = {
                'status': 'ok',
                'id': chat.get('id') if isinstance(chat, dict) else None,
                'type': chat.get('type') if isinstance(chat, dict) else None,
                'username': actual_username,
                'title': chat.get('title') if isinstance(chat, dict) else None,
                'expected_chat_id_matches': isinstance(chat, dict) and chat.get('id') == args.chat_id,
                'expected_username_matches': (not args.expected_username) or (isinstance(actual_username, str) and actual_username.casefold() == args.expected_username.casefold()),
            }
        except Exception as exc:
            chat_check = {'status': 'error', 'error_type': type(exc).__name__, 'error': str(exc)[:240]}

        getme_latency = await measure_call('SwiftBot API getMe', get_me, args.getme_repeats)
        getchat_latency = await measure_call('SwiftBot API getChat', get_chat, args.getchat_repeats)
        for _ in range(args.getupdates_repeats):
            start = time.perf_counter_ns()
            try:
                updates = await get_updates()
                update_samples.append({
                    'ok': True,
                    'elapsed_ms': (time.perf_counter_ns() - start) / 1e6,
                    'count': len(updates) if isinstance(updates, list) else None,
                })
            except Exception as exc:
                update_samples.append({
                    'ok': False,
                    'elapsed_ms': (time.perf_counter_ns() - start) / 1e6,
                    'error_type': type(exc).__name__,
                    'error': str(exc)[:240],
                })

        for level in [1, 2, 4, 8]:
            concurrency.append(await concurrency_probe(get_me, level))
    finally:
        await bot.connection_pool.close()

    result = {
        'benchmark': 'real_telegram_read_only',
        'framework': 'swiftbot',
        'swiftbot_version': '1.6.3',
        'python': sys.version.split()[0],
        'host_rss_before_build_kib': start_rss,
        'host_rss_after_build_kib': build_rss,
        'build_rss_delta_kib': build_rss - start_rss,
        'connection_pool_initialize_ms': build_ms,
        'configuration': {
            'worker_pool_size': 8,
            'max_connections': 16,
            'http2_enabled': True,
        },
        'identity': identity,
        'chat_check': chat_check,
        'getme_latency': getme_latency,
        'getchat_latency': getchat_latency,
        'getupdates_samples': update_samples,
        'concurrent_getme': concurrency,
        'safety': {
            'write_methods_called': [],
            'read_methods_called': ['getMe', 'getChat', 'getUpdates'],
            'token_printed': False,
            'chat_id_used': args.chat_id,
        },
    }
    args.output.write_text(json.dumps(result, indent=2) + '\n', encoding='utf-8')
    print(json.dumps(result, indent=2))


asyncio.run(main())
