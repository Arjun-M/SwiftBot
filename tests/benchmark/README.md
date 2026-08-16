# SwiftBot Benchmark Suite

This repository contains a reproducible benchmark and technical assessment of **SwiftBot** against aiogram, python-telegram-bot, and pyTelegramBotAPI. It covers offline dispatch speed, latency, route-scaling behavior, worker-pool concurrency, queue backpressure, resident memory, package footprint, startup/build cost, and a separate read-only real Telegram API smoke test.

## Project stance

The controlled offline results support SwiftBot as a promising high-performance framework for greenfield asynchronous Telegram bots. SwiftBot led the local dispatch and RSS tests in this environment, and its worker pool demonstrated useful scaling with an asynchronous handler and bounded queue behavior. The project should still be adopted with a load-test and compatibility gate for mission-critical deployments because its public ecosystem and release maturity are less established than the leading alternatives.

## Primary measured results

| Framework | Median offline throughput | Median latency | Peak RSS | Framework package |
|---|---:|---:|---:|---:|
| SwiftBot 1.6.3 | **28,954 updates/s** | **34.5 µs/update** | **32.9 MiB** | **0.93 MiB** |
| python-telegram-bot 22.8 | 8,919 updates/s | 112.1 µs/update | 39.6 MiB | 6.75 MiB |
| pyTelegramBotAPI 4.36.1 | 6,734 updates/s | 148.5 µs/update | 46.0 MiB | 4.44 MiB |
| aiogram 3.30.0 | 1,407 updates/s | 710.9 µs/update | 154.0 MiB | 5.76 MiB |

All four frameworks routed the expected handler invocations correctly. These are local dispatch measurements without Telegram network latency, outbound API calls, databases, Redis, webhooks, or application-specific business logic.

## Repository layout

```text
.
├── README.md
├── BENCHMARK_REPORT.md
├── SECURITY.md
├── .gitignore
├── requirements-benchmark.txt
├── scripts/
│   ├── benchmark_dispatch.py
│   ├── benchmark_memory.py
│   ├── benchmark_pool.py
│   ├── benchmark_swiftbot_harness.py
│   ├── collect_stats.py
│   ├── analyze_results.py
│   ├── analyze_extended.py
│   ├── real_telegram_benchmark.py
│   ├── sanitize_real_result.py
│   ├── inspect_competitors.py
│   ├── inspect_runtime_config.py
│   ├── inspect_swiftbot.py
│   └── smoke_dispatch.py
├── results/
│   ├── full_*_10routes.json
│   ├── *_1routes.json / *_10routes.json / *_50routes.json
│   ├── memory_*_normalgc.json
│   ├── pool_full.json
│   ├── stats_*.json
│   └── real_telegram_swiftbot_sanitized.json
├── analysis/
│   ├── extended_summary.csv
│   ├── primary_summary.csv
│   ├── throughput_10routes.png
│   ├── routing_scalability.png
│   ├── memory_peak_rss.png
│   └── swiftbot_pool_scaling.png
└── docs/
    ├── extended_scope.md
    └── installation_notes.md
```

## Benchmark tests and graph outputs

The suite is organized as reproducible offline tests plus an explicitly read-only real Telegram smoke test. The checked-in JSON and CSV files are the measured snapshot used by [`BENCHMARK_REPORT.md`](BENCHMARK_REPORT.md); rerunning the scripts can produce different numbers on another machine or under a different runtime load.

| Test file | What it tests | Main output |
|---|---|---|
| `scripts/benchmark_dispatch.py` | Routes synthetic updates through SwiftBot, aiogram, python-telegram-bot, or pyTelegramBotAPI and measures throughput, latency, correctness, and route scaling. | `results/full_*_10routes.json`, `results/*_1routes.json`, `results/*_10routes.json`, `results/*_50routes.json` |
| `scripts/benchmark_memory.py` | Measures fresh-process peak RSS, workload RSS delta, package size, and site-packages footprint for each framework. | `results/memory_*_normalgc.json` |
| `scripts/benchmark_pool.py` | Measures SwiftBot worker-pool throughput across worker counts and verifies bounded-queue backpressure and completion counts. | `results/pool_full.json` |
| `scripts/benchmark_swiftbot_harness.py` | Measures the built-in `TestClient` harness with no Telegram network calls. | A JSON result supplied with `--output` |
| `scripts/collect_stats.py` | Collects package and environment size statistics from an isolated virtual environment. | `results/stats_*.json` |
| `scripts/analyze_results.py` | Aggregates primary results and writes the primary summary tables and charts. | `analysis/primary_summary.*`, `analysis/throughput_10routes.png`, `analysis/routing_scalability.png`, `analysis/memory_peak_rss.png` |
| `scripts/analyze_extended.py` | Aggregates extended results and writes the worker-pool summary and scaling chart. | `analysis/extended_summary.*`, `analysis/pool_summary.json`, `analysis/swiftbot_pool_scaling.png` |
| `scripts/real_telegram_benchmark.py` | Performs read-only `getMe`, `getChat`, and `getUpdates` checks against Telegram when explicitly supplied with private credentials. | A local JSON result supplied with `--output` |
| `scripts/sanitize_real_result.py` | Removes bot and chat identifiers from a real benchmark result before publication. | A sanitized JSON result |

### Generated graphs

The benchmark analysis scripts generate the following charts from the JSON result files. They are included here so the benchmark results can be reviewed directly from the repository:

![Throughput comparison](analysis/throughput_10routes.png)

![Routing scalability](analysis/routing_scalability.png)

![Peak resident memory](analysis/memory_peak_rss.png)

![SwiftBot worker-pool scaling](analysis/swiftbot_pool_scaling.png)

Run the analysis after collecting or replacing results:

```bash
python3 scripts/analyze_results.py
python3 scripts/analyze_extended.py
```

## Reproduce the offline benchmark

Use Python 3.12 or another supported Python 3.10+ runtime. The benchmark uses isolated virtual environments so dependency graphs do not contaminate one another.

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

venv-swiftbot/bin/python scripts/benchmark_dispatch.py swiftbot --routes 10 --iterations 5000 --warmup 250 --repeats 7 --output results/full_swiftbot_10routes.json
venv-aiogram/bin/python scripts/benchmark_dispatch.py aiogram --routes 10 --iterations 5000 --warmup 250 --repeats 7 --output results/full_aiogram_10routes.json
venv-ptb/bin/python scripts/benchmark_dispatch.py ptb --routes 10 --iterations 5000 --warmup 250 --repeats 7 --output results/full_ptb_10routes.json
venv-telebot/bin/python scripts/benchmark_dispatch.py telebot --routes 10 --iterations 5000 --warmup 250 --repeats 7 --output results/full_telebot_10routes.json
```

The memory and worker-pool tests can be run as follows:

```bash
venv-swiftbot/bin/python scripts/benchmark_memory.py swiftbot --routes 10 --updates 10000 --output results/memory_swiftbot_normalgc.json
venv-aiogram/bin/python scripts/benchmark_memory.py aiogram --routes 10 --updates 10000 --output results/memory_aiogram_normalgc.json
venv-ptb/bin/python scripts/benchmark_memory.py ptb --routes 10 --updates 10000 --output results/memory_ptb_normalgc.json
venv-telebot/bin/python scripts/benchmark_memory.py telebot --routes 10 --updates 10000 --output results/memory_telebot_normalgc.json

venv-swiftbot/bin/python scripts/benchmark_pool.py --updates 400 --delay 0.002 --queue-size 100 --repeats 3 --backpressure-updates 20 --backpressure-delay 0.05 --backpressure-timeout 0.005 --output results/pool_full.json
python3 scripts/analyze_results.py
python3 scripts/analyze_extended.py
```

## Real Telegram smoke test

The real test is deliberately read-only. It calls only `getMe`, `getChat`, and `getUpdates`, and records latency, concurrency behavior, and process RSS. It does not send messages, modify bot state, set webhooks, or acknowledge updates. Do not commit a token or raw private result file.

```bash
export TELEGRAM_TOKEN_FILE=/secure/location/Env.txt
venv-swiftbot/bin/python scripts/real_telegram_benchmark.py \
  --token-file "$TELEGRAM_TOKEN_FILE" \
  --chat-id "$TELEGRAM_CHAT_ID" \
  --expected-username "$TELEGRAM_EXPECTED_USERNAME" \
  --output results/real_telegram_swiftbot_local.json
```

The checked-in `real_telegram_swiftbot_sanitized.json` removes bot IDs, chat IDs, usernames, and other identifying fields while preserving the measured latency and resource metrics. A new real run should be sanitized before publication.

## Security

Never put a Telegram token in source code, Markdown, shell history, Git history, issue comments, or benchmark output. Use a file outside the repository or an environment variable, and revoke any token that has been exposed. See [`SECURITY.md`](SECURITY.md).

## Sources

The package identities and documented capabilities were checked against the official [SwiftBot PyPI page](https://pypi.org/project/swiftbot/), [SwiftBot GitHub repository](https://github.com/Arjun-M/SwiftBot), [aiogram PyPI page](https://pypi.org/project/aiogram/), [python-telegram-bot PyPI page](https://pypi.org/project/python-telegram-bot/), and [pyTelegramBotAPI PyPI page](https://pypi.org/project/pyTelegramBotAPI/).
