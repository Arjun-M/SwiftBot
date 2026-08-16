# SwiftBot Benchmark Suite

This directory contains a reproducible comparison of SwiftBot, aiogram, python-telegram-bot, and pyTelegramBotAPI. It measures public offline raw-update processing, exact-text route scaling, worker-pool behavior, bounded backpressure, fresh-process memory, package footprint, and a separate read-only real Telegram API smoke test.

## Current stance

SwiftBot is promising for low-overhead asynchronous Telegram bots, but the benchmark should be read as a **public-path measurement**, not proof of universal framework superiority. The adapters use each framework’s public offline update-processing surface, but those surfaces still perform different amounts of parsing, validation, object construction, middleware, and scheduling work.

The earlier internal-path result has been replaced. The current result no longer uses SwiftBot’s private `_process_update()` method, disables no garbage collection, or compares regex matching against exact matching. SwiftBot now runs through the public `TestClient.send_updates()` path, and the test harness uses `asyncio.Queue.join()` so it waits for in-flight handlers without a 20 ms polling delay.

## Corrected public raw-update result

Configuration: ten exact-text routes, 2,000 measured updates per repeat, 100 warm-up updates, five repeats, one logical worker, enabled garbage collection, identical synthetic Telegram-shaped update structure, no network calls, and correctness assertion enabled.

| Framework | Public path | Median throughput | Median latency/update | Peak RSS | Correct |
|---|---|---:|---:|---:|---|
| **SwiftBot 1.6.3** | `TestClient.send_updates` | **19,803 updates/s** | **50.5 µs** | **33.2 MiB** | Yes |
| pyTelegramBotAPI 4.36.1 | `AsyncTeleBot.process_new_updates` | 10,358 updates/s | 96.5 µs | 46.8 MiB | Yes |
| python-telegram-bot 22.8 | `Application.process_update` | 9,432 updates/s | 106.0 µs | 39.9 MiB | Yes |
| aiogram 3.30.0 | `Dispatcher.feed_raw_update` | 1,219 updates/s | 820.4 µs | 154.4 MiB | Yes |

SwiftBot measured approximately 1.91× the pyTelegramBotAPI throughput, 2.10× python-telegram-bot, and 16.24× aiogram in this particular public raw-update workload. These ratios are observations for these versions and adapters, not universal production claims. See [`docs/fair_methodology.md`](docs/fair_methodology.md) for the fairness rules and remaining limitations.

## Layout

```text
.
├── README.md
├── BENCHMARK_REPORT.md
├── REAL_TELEGRAM_REPORT.md
├── SECURITY.md
├── requirements-benchmark.txt
├── scripts/
│   ├── benchmark_dispatch.py
│   ├── benchmark_memory.py
│   ├── benchmark_pool.py
│   ├── benchmark_swiftbot_harness.py
│   ├── analyze_results.py
│   ├── real_telegram_benchmark.py
│   └── sanitize_real_result.py
├── results/
│   └── fair_public/
├── analysis/
└── docs/
    └── fair_methodology.md
```

## Reproduce the corrected offline benchmark

Use Python 3.10+ and isolated virtual environments. The exact package versions used for the checked-in snapshot are SwiftBot 1.6.3, aiogram 3.30.0, python-telegram-bot 22.8, and pyTelegramBotAPI 4.36.1.

```bash
python3 -m venv venv-swiftbot
python3 -m venv venv-aiogram
python3 -m venv venv-ptb
python3 -m venv venv-telebot

venv-swiftbot/bin/python -m pip install swiftbot==1.6.3
venv-aiogram/bin/python -m pip install aiogram==3.30.0
venv-ptb/bin/python -m pip install python-telegram-bot==22.8
venv-telebot/bin/python -m pip install pyTelegramBotAPI==4.36.1

python3 -m py_compile scripts/*.py

PYTHONPATH=../.. venv-swiftbot/bin/python scripts/benchmark_dispatch.py swiftbot --routes 10 --iterations 2000 --warmup 100 --repeats 5 --output results/fair_public/swiftbot_10routes.json
venv-aiogram/bin/python scripts/benchmark_dispatch.py aiogram --routes 10 --iterations 2000 --warmup 100 --repeats 5 --output results/fair_public/aiogram_10routes.json
venv-ptb/bin/python scripts/benchmark_dispatch.py ptb --routes 10 --iterations 2000 --warmup 100 --repeats 5 --output results/fair_public/ptb_10routes.json
venv-telebot/bin/python scripts/benchmark_dispatch.py telebot --routes 10 --iterations 2000 --warmup 100 --repeats 5 --output results/fair_public/telebot_10routes.json
```

For local development from this repository, `PYTHONPATH=../..` ensures the benchmark imports the checked-out SwiftBot source rather than a different installed release.

## Resource and worker-pool tests

```bash
PYTHONPATH=../.. venv-swiftbot/bin/python scripts/benchmark_memory.py swiftbot --routes 10 --updates 10000 --batch-size 100 --output results/fair_public/memory_swiftbot.json
venv-aiogram/bin/python scripts/benchmark_memory.py aiogram --routes 10 --updates 10000 --batch-size 100 --output results/fair_public/memory_aiogram.json
venv-ptb/bin/python scripts/benchmark_memory.py ptb --routes 10 --updates 10000 --batch-size 100 --output results/fair_public/memory_ptb.json
venv-telebot/bin/python scripts/benchmark_memory.py telebot --routes 10 --updates 10000 --batch-size 100 --output results/fair_public/memory_telebot.json

PYTHONPATH=../.. venv-swiftbot/bin/python scripts/benchmark_pool.py --updates 400 --delay 0.002 --queue-size 100 --repeats 3 --backpressure-updates 20 --backpressure-delay 0.05 --backpressure-timeout 0.005 --output results/fair_public/pool_full.json
python3 scripts/analyze_results.py
```

## Real Telegram smoke test

The real test is intentionally read-only. It calls only `getMe`, `getChat`, and `getUpdates`; it does not send a message, alter webhooks, acknowledge updates, or change bot state. Store the token outside the repository and never put it in a command-line argument or Git history.

```bash
export TELEGRAM_TOKEN_FILE=/secure/location/Env.txt
venv-swiftbot/bin/python scripts/real_telegram_benchmark.py \
  --token-file "$TELEGRAM_TOKEN_FILE" \
  --chat-id "$TELEGRAM_CHAT_ID" \
  --expected-username "$TELEGRAM_EXPECTED_USERNAME" \
  --output results/real_telegram_swiftbot_local.json
python3 scripts/sanitize_real_result.py \
  results/real_telegram_swiftbot_local.json \
  results/real_telegram_swiftbot_sanitized.json
```

## Security

Never commit Telegram credentials or raw private real-test results. If a token is exposed, revoke it immediately through @BotFather. See [`SECURITY.md`](SECURITY.md).

## Sources

Package identities and documented capabilities were checked against the official [SwiftBot PyPI page](https://pypi.org/project/swiftbot/), [SwiftBot GitHub repository](https://github.com/Arjun-M/SwiftBot), [aiogram PyPI page](https://pypi.org/project/aiogram/), [python-telegram-bot PyPI page](https://pypi.org/project/python-telegram-bot/), and [pyTelegramBotAPI PyPI page](https://pypi.org/project/pyTelegramBotAPI/).
