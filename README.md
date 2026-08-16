<img src="https://raw.githubusercontent.com/Arjun-M/SwiftBot/main/banner.jpg" alt="SwiftBot - Ultra-Fast Telegram Bot Framework" width="100%">

[![PyPI](https://img.shields.io/pypi/v/swiftbot.svg)](https://pypi.org/project/swiftbot/)
[![Python](https://img.shields.io/badge/python-3.10%2B-blue.svg)](https://www.python.org/)
[![License](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)

# SwiftBot

SwiftBot is a fast, async-first Telegram bot framework built for simplicity and correctness. One decorator registers a handler, a rich `Context` object does the talking, and the framework quietly handles everything else — HTTP/2 connection pooling, `Retry-After` compliance, persistent state storage, and a fully typed error hierarchy. Everything is typed, everything is optional, and you never need an external database to get started.

```bash
pip install swiftbot
```

The built-in webhook server is optional. Polling does not require `aiohttp`; install the webhook extra only when you need webhook mode:

```bash
pip install "swiftbot[webhook]"
```

## Why SwiftBot

SwiftBot is a strong fit for asynchronous, route-heavy bots where local dispatch speed, predictable resource use, typed APIs, and operational controls matter. The checked-in benchmark snapshot measured SwiftBot at **28,954 updates per second** and **34.5 microseconds per update** for a controlled ten-route offline workload on Python 3.12.3. Every framework routed all expected handler calls correctly; these measurements exclude Telegram network latency, databases, business logic, and application-specific middleware.

| Advantage | What it means in practice | Evidence in this repository |
|---|---|---|
| **Fast local dispatch** | More handler work can be processed per process before application logic or network I/O becomes the bottleneck. | SwiftBot measured 3.25× the throughput of python-telegram-bot, 4.30× pyTelegramBotAPI, and 20.6× aiogram in the controlled offline comparison. |
| **Low measured framework footprint** | Smaller framework distributions and lower measured peak RSS can help constrained deployments, while dependency footprints still need to be evaluated for the full application. | The snapshot measured 32.9 MiB peak RSS and a 0.93 MiB SwiftBot package distribution. |
| **Useful async concurrency** | I/O-like handlers can scale with bounded worker concurrency rather than relying on unbounded task creation. | The worker-pool benchmark reached 2,839 completed updates per second at eight workers versus 437 at one worker, with all 400 updates completed in every repeat. |
| **Operational safeguards** | HTTP/2 pooling, retry-after handling, bounded backpressure, dead-letter handling, and typed Telegram errors reduce the amount of reliability plumbing bot authors must build themselves. | These are implemented in the connection pool, worker pool, exception hierarchy, and webhook server. |
| **Network-free testing** | Handlers can be exercised without Telegram credentials or network calls, with outgoing API requests captured for assertions. | The built-in `TestClient` harness and the repository’s 210 passing tests provide the local testing path. |

The benchmark results are **controlled local measurements, not a universal claim that SwiftBot is faster for every production bot**. Framework choice should still account for ecosystem maturity, compatibility requirements, workload shape, network latency, and a project-specific load test. See the full [benchmark report](tests/benchmark/BENCHMARK_REPORT.md) and the [reproduction guide](tests/benchmark/README.md) for methods, charts, raw results, and caveats.

## Quick Start

```python
import asyncio
from swiftbot import SwiftBot, Filters as F
from swiftbot.types import Message

bot = SwiftBot(token="YOUR_BOT_TOKEN")

@bot.on(Message(text="hello"))
async def hello(ctx):
    await ctx.reply("Hi there!")

@bot.on(Message(filters=F.command("start")))
async def start(ctx):
    await ctx.reply("Welcome! Send me hello.")

asyncio.run(bot.run())
```

That is the whole bot. No router setup, no dispatch table, no middleware boilerplate.

## Core Concepts

### Handlers and Filters

Handlers are registered with `@bot.on(Message(...))` and the first matching handler wins. Filters are composable — combine commands, regex patterns, and predicates:

```python
@bot.on(Message(filters=F.command("ban") & F.chat(-100123456789)))
async def ban(ctx):
    ...

@bot.on(Message(pattern=r"^/weather (\w+)"))
async def weather(ctx):
    city = ctx.match.group(1)
    await ctx.reply(f"Weather in {city}: sunny")
```

### Context

Every handler receives a `Context` with typed access to the update, plus shortcuts that cover most use cases: `ctx.reply()`, `ctx.edit()`, `ctx.delete()`, `ctx.answer_callback()`, and `ctx.forward_to()`.

### Buttons and Callbacks

```python
from swiftbot import InlineKeyboard, Button, CallbackData

# Declare the payload shape once
page = CallbackData("page", int)

# Attach packed payloads to buttons
kb = InlineKeyboard([]).add_row(
    Button.inline("1", page.pack(1)),
    Button.inline("2", page.pack(2)),
)
await ctx.reply("Pick a page:", reply_markup=kb.to_dict())

# Filter on valid payloads and decode the typed data
@bot.on(CallbackQuery(pattern=rf"^{page.prefix}:[^:]+:[^:]+$"))
async def on_page(ctx):
    page_num = page.unpack(ctx.callback_query.data)[0]
    await ctx.answer_callback(f"Page {page_num}")
```

### State and Dialogues

State survives restarts with pluggable storage backends — in-memory, JSON file, or Redis — and the dialogue system models multi-step conversations as declared transition graphs with per-state timeouts:

```python
survey = bot.dialogue("survey")

@survey.state("ask_name", next=["ask_age"])
async def ask_name(ctx, prev=None):
    await ctx.reply("What's your name?")
    return Dialogue.next("ask_age", carry=ctx.text)

@survey.state("ask_age", timeout=120.0)
async def ask_age(ctx, prev=None):
    await ctx.reply(f"Hi {prev}, how old are you?")
    return Dialogue.end
```

### Middleware, Pipelines and Scopes

Middleware runs around every handler, and the `Composer` bundles middleware chains with error boundaries. `Pipeline` adds dependency injection so handlers stay pure and testable, while `scope()` attaches middleware to only the updates matching a predicate.

```python
from swiftbot.middleware import Logger, RateLimiter
from swiftbot.pipeline import Pipeline

bot.use(Logger())
bot.use(RateLimiter(rate=20, per=60))

pipe = Pipeline().deps(db=my_db)
async def stats(ctx, db):
    await ctx.reply(f"{await db.count()} users")
pipe.handle(F.command("stats"), stats)
bot.pipeline(pipe)

bot.scope(F.private).use(RateLimiter(rate=1, per=1.0))
```

### Safety Nets

Fallback handlers catch anything that no other handler matched, and outbound throttling keeps your bot under Telegram's limits automatically:

```python
@bot.fallback
async def catch_all(ctx):
    await ctx.reply("Try /help.")

bot.api.config.use(throttle(max_per_second=20.0, per_chat=4.0))
```

## Testing Without Telegram

The built-in harness runs your real handlers with zero network calls — every outgoing API request is captured and every response is scriptable:

```python
from swiftbot.testing import TestClient

async with TestClient(bot) as client:
    await client.send_update({
        "update_id": 1,
        "message": {
            "message_id": 1, "date": 1,
            "chat": {"id": 1, "type": "private"},
            "from": {"id": 2, "is_bot": False, "first_name": "A"},
            "text": "hello",
        },
    })

assert client.outgoing[0]["method"] == "sendMessage"
```

## More

| Topic | What you get |
| --- | --- |
| [Commands](https://github.com/Arjun-M/SwiftBot/tree/main/docs/05_Commands.md) | Declarative command specs with auto-generated `/help` |
| [Transformers](https://github.com/Arjun-M/SwiftBot/tree/main/docs/16_Transformers.md) | Outbound API layer with auto-typing and recording |
| [Deep Linking](https://github.com/Arjun-M/SwiftBot/tree/main/docs/09_DeepLinking.md) | Typed `?start=` payloads for referrals and auth |
| [Webhooks](https://github.com/Arjun-M/SwiftBot/tree/main/docs/22_Webhooks.md) | aiohttp server with secret-token verification and metrics |
| [Storage](https://github.com/Arjun-M/SwiftBot/tree/main/docs/17_StorageAndState.md) | In-memory, JSON-file, and Redis FSM backends |
| [Exceptions](https://github.com/Arjun-M/SwiftBot/tree/main/docs/18_Exceptions.md) | Typed `ChatNotFound`, `TooManyRequests`, `Forbidden`, ... |
| [Benchmarks](tests/benchmark/README.md) | Reproducible dispatch, memory, worker-pool, backpressure, and read-only Telegram smoke tests with reports and graphs |

The complete documentation lives in the [`docs/`](https://github.com/Arjun-M/SwiftBot/tree/main/docs) folder. The benchmark suite is documented in [`tests/benchmark/README.md`](tests/benchmark/README.md), with the measured results summarized in [`tests/benchmark/BENCHMARK_REPORT.md`](tests/benchmark/BENCHMARK_REPORT.md).

## Contributing

Contributions are welcome — open an issue or submit a pull request.

## License

MIT — Copyright (c) 2026 Arjun-M/SwiftBot
