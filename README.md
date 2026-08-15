# SwiftBot

![Banner](banner.jpg)

[![Python](https://img.shields.io/badge/Python-3.10%2B-blue.svg)](https://www.python.org/)
[![License](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)
[![Tests](https://img.shields.io/badge/tests-passing-green.svg)](https://github.com/Arjun-M/SwiftBot/actions)

SwiftBot is an async framework for building Telegram bots. It pairs a handler model most people already know from Telethon with a few things the older libraries make you wire up yourself: persistent conversation state, real rate-limit handling, typed Telegram errors, and a worker pool that behaves sensibly under load. Everything runs on httpx with HTTP/2, and the core has no external dependencies beyond the HTTP client.

## Features

**Handlers and routing.** Register handlers with `@client.on(...)` and match on event type, exact text, regex, or an arbitrary predicate. Slash commands are stored in a trie, so lookup cost is proportional to the command length rather than the number of handlers.

**Conversation state that survives restarts.** Attach a storage backend (`MemoryStorage`, `JSONFileStorage`, or your own `BaseStorage` subclass) and use `ctx.set_state` / `ctx.get_state` / `ctx.clear_state` to drive multi-step conversations. State can expire automatically with `state_ttl`.

**Rate-limit handling done properly.** When Telegram answers a request with 429, SwiftBot reads `parameters.retry_after` (or the `Retry-After` header) and waits exactly that long before retrying — no blind exponential backoff that gets accounts flagged. A circuit breaker sits in front of the connection pool for added protection.

**Typed errors.** Telegram's JSON errors are mapped to a real exception hierarchy. Catch `ChatNotFound`, `Forbidden`, `TooManyRequests`, `MigrateToChat` (which carries the new supergroup id) and others instead of parsing error strings.

**A worker pool with backpressure.** Updates are dispatched to a bounded pool of workers. When the queue fills, `submit` fails fast with a timeout error instead of blocking forever, and handlers that raise are preserved in a dead-letter queue with their exceptions intact, so nothing is lost and failures are retryable.

**Webhooks.** A webhook server built on aiohttp with secret-token verification, request size limits, and health/metrics endpoints — tested end-to-end.

**Files.** Send local files with `InputFile`, and pull files down with `get_file` / `download_file`.

**Middleware.** A simple `client.use(...)` chain ships with a logger, rate limiter, admin auth, and an analytics collector, all in-memory and dependency-free.

## Installation

```bash
pip install swiftbot

# or straight from GitHub
pip install git+https://github.com/Arjun-M/SwiftBot.git
```

Requires Python 3.10 or newer.

## Quick Start

```python
import asyncio
from swiftbot import SwiftBot
from swiftbot.types import Message
from swiftbot.middleware import Logger, RateLimiter

client = SwiftBot(
    token="YOUR_BOT_TOKEN",
    worker_pool_size=50,
    enable_http2=True,
)

client.use(Logger(level="INFO"))
client.use(RateLimiter(rate=10, per=60))

@client.on(Message(pattern=r"^/start"))
async def start(ctx):
    await ctx.reply("Hello from SwiftBot!")

asyncio.run(client.run(mode="polling"))
```

### A multi-step conversation

```python
from swiftbot import SwiftBot
from swiftbot.types import Message
from swiftbot.storage import JSONFileStorage

bot = SwiftBot(
    token="YOUR_BOT_TOKEN",
    storage=JSONFileStorage("state.json"),
    state_ttl=3600,
)

@bot.on(Message(text="/start"))
async def cmd_start(ctx):
    await ctx.set_state({"step": "name"})
    await ctx.reply("What's your name?")

@bot.on(Message())
async def on_text(ctx):
    state = await ctx.get_state()
    if state and state.get("step") == "name":
        await ctx.set_state({"step": "done", "name": ctx.text})
        await ctx.reply(f"Got it — {ctx.text}.")
    elif state and state.get("step") == "done":
        await ctx.clear_state()
```

### Handling Telegram errors by type

```python
from swiftbot.exceptions import ChatNotFound, Forbidden, TooManyRequests

try:
    await bot.send_message(chat_id, "notification")
except ChatNotFound:
    # chat was deleted — remove from your records
except Forbidden:
    # the user blocked the bot
except TooManyRequests as exc:
    # exc.retry_after tells you how long Telegram wants you to wait
```

## Client Reference

```python
client = SwiftBot(
    token="YOUR_BOT_TOKEN",
    parse_mode="HTML",               # default parse mode for sends
    worker_pool_size=50,             # concurrent handler workers
    max_connections=100,             # HTTP connection limit
    timeout=30,                      # request timeout in seconds
    enable_http2=True,               # HTTP/2 multiplexing
    enable_centralized_exceptions=True,
    storage=JSONFileStorage("state.json"),  # optional FSM backend
    state_ttl=3600,                           # optional state expiry
)
```

Run in either mode: `client.run(mode="polling")` or `client.run(mode="webhook", url="...", secret_token="...")`.

## Event Types and Filters

```python
from swiftbot.types import Message, CallbackQuery
from swiftbot.filters import Filters as F

@client.on(Message())                    # every message
@client.on(Message(text="hello"))        # exact text
@client.on(Message(pattern=r"^/start"))  # regex
@client.on(Message(chat_id=[111, 222]))  # attribute filter
@client.on(CallbackQuery(data="btn:1"))  # callback data
@client.on(CallbackQuery(pattern=r"^page_\d+$"))
@client.on(Message(), F.text(lambda t: len(t) > 50))
```

## Context Object

Every handler receives a `Context` with the parsed update and shortcuts for the most common operations:

```python
@client.on(Message())
async def handler(ctx):
    ctx.text    # message text
    ctx.user    # sender User object
    ctx.chat    # Chat object
    ctx.args    # command arguments (list)
    ctx.match   # regex Match, when a pattern matched

    await ctx.reply("Text")
    await ctx.edit("New text")
    await ctx.delete()
    await ctx.forward_to(chat_id)
```

## Middleware

```python
from swiftbot.middleware import Logger, RateLimiter, Auth, AnalyticsCollector

client.use(Logger(level="INFO", format="text"))
client.use(RateLimiter(rate=10, per=60))          # sliding window, in-memory
client.use(Auth(admin_list=[123456, 789012]))     # restrict commands to admins
client.use(AnalyticsCollector())                  # request metrics
```

Middleware runs as a chain around each update; write your own by subclassing `Middleware`.

## Under the Hood

**HTTP layer.** All Telegram requests go through an httpx connection pool with HTTP/2 multiplexing, keep-alive, and automatic recycling of failed connections. 429 responses respect Telegram's `retry_after` value.

**Worker pool.** Updates are submitted to a bounded queue with backpressure (configurable timeout, default 5s) and a dead-letter queue that keeps failed updates with their exceptions for later inspection or retry via `retry_dead_letters()`. Workers are drained gracefully on shutdown.

**Webhook server.** Built on aiohttp: 1 MB request cap, optional secret-token verification (403 on mismatch), and JSON parse errors logged and returned as 400.

**Parsing.** Update JSON is deserialized into dataclass objects. Deeply nested `reply_to_message` chains are truncated rather than recursed infinitely, and unknown update fields are ignored gracefully.

## Project Structure

```
swiftbot/
├── __init__.py           # package exports
├── client.py             # SwiftBot client
├── context.py            # Context object and FSM helpers
├── types.py              # Message / CallbackQuery / event types
├── filters.py            # filter system and CommandFilter
├── storage.py            # BaseStorage, MemoryStorage, JSONFileStorage
├── router.py             # trie-based command router
├── update_types.py       # Telegram API object parsing
├── webhook/              # aiohttp webhook server
├── exceptions/           # typed Telegram error hierarchy
└── middleware/           # Logger, RateLimiter, Auth, AnalyticsCollector

tests/        # test suite (pytest)
examples/     # working example bots
```

## Development

```bash
git clone https://github.com/Arjun-M/SwiftBot.git
cd SwiftBot
pip install -e ".[dev]"
python -m pytest
```

Pull requests are welcome — and appreciated. If you find a bug, an issue with a way to reproduce it will get a fix faster than a description alone.

## License

MIT — Copyright (c) 2025 Arjun-M/SwiftBot

## Acknowledgments

The handler syntax is inspired by [Telethon](https://github.com/LonamiWebs/Telethon); the HTTP layer is built on [httpx](https://www.python-httpx.org/).
