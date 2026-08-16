# SwiftBot Benchmarks

This folder contains the reproducible offline and read-only Telegram benchmarks for SwiftBot, aiogram, python-telegram-bot, and pyTelegramBotAPI.

## Layout

```text
benchmark/
├── README.md
├── requirements.txt
├── benchmark_dispatch.py      # speed, latency, and route scaling
├── benchmark_memory.py        # RSS and memory growth
├── benchmark_pool.py          # worker pool and backpressure
├── benchmark_real_api.py      # read-only getMe/getChat/getUpdates
├── analyze.py                 # results to CSV and charts
├── results/
│   ├── public/                # sanitized committed results
│   └── raw/                   # local-only raw outputs; ignored
└── reports/
    ├── benchmark_report.md
    ├── summary.csv
    ├── summary.json
    ├── scaling.json
    └── charts/
```

The ordinary SwiftBot regression test remains at [`../tests/test_testing_harness.py`](../tests/test_testing_harness.py). The full assessment is in [`reports/benchmark_report.md`](reports/benchmark_report.md).

## Install

Use separate environments so framework dependencies do not contaminate one another:

```bash
python3 -m venv venv-swiftbot
python3 -m venv venv-aiogram
python3 -m venv venv-ptb
python3 -m venv venv-telebot

venv-swiftbot/bin/python -m pip install swiftbot==1.6.3
venv-aiogram/bin/python -m pip install aiogram==3.30.0
venv-ptb/bin/python -m pip install python-telegram-bot==22.8
venv-telebot/bin/python -m pip install pyTelegramBotAPI==4.36.1
```

## Run

From the repository root:

```bash
mkdir -p benchmark/results/raw

PYTHONPATH=. venv-swiftbot/bin/python benchmark/benchmark_dispatch.py swiftbot --routes 10 --iterations 2000 --warmup 100 --repeats 5 --output benchmark/results/raw/swiftbot.json
venv-aiogram/bin/python benchmark/benchmark_dispatch.py aiogram --routes 10 --iterations 2000 --warmup 100 --repeats 5 --output benchmark/results/raw/aiogram.json
venv-ptb/bin/python benchmark/benchmark_dispatch.py ptb --routes 10 --iterations 2000 --warmup 100 --repeats 5 --output benchmark/results/raw/ptb.json
venv-telebot/bin/python benchmark/benchmark_dispatch.py telebot --routes 10 --iterations 2000 --warmup 100 --repeats 5 --output benchmark/results/raw/telebot.json

PYTHONPATH=. venv-swiftbot/bin/python benchmark/benchmark_memory.py swiftbot --routes 10 --updates 10000 --batch-size 100 --output benchmark/results/raw/memory_swiftbot.json
PYTHONPATH=. venv-swiftbot/bin/python benchmark/benchmark_pool.py --updates 400 --delay 0.002 --queue-size 100 --repeats 3 --backpressure-updates 20 --backpressure-delay 0.05 --backpressure-timeout 0.005 --output benchmark/results/raw/pool.json
python3 benchmark/analyze.py
```

## Real Telegram test

`benchmark_real_api.py` performs read-only `getMe`, `getChat`, and `getUpdates` calls. It does not send messages or modify bot state. Keep the token outside the repository and write any raw output to `benchmark/results/raw/`; sanitize before copying a result into `benchmark/results/public/`.

```bash
export TELEGRAM_TOKEN_FILE=/secure/location/Env.txt
PYTHONPATH=. venv-swiftbot/bin/python benchmark/benchmark_real_api.py \
  --token-file "$TELEGRAM_TOKEN_FILE" \
  --chat-id "$TELEGRAM_CHAT_ID" \
  --expected-username "$TELEGRAM_EXPECTED_USERNAME" \
  --output benchmark/results/raw/real_telegram.json
```

Never commit a token or unsanitized real response. Revoke any token that has been exposed.
