
[![Python](https://img.shields.io/badge/Python-3.10%2B-blue.svg)](https://www.python.org/)
[![License](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)
[![Tests](https://img.shields.io/badge/tests-passing-green.svg)](https://github.com/Arjun-M/SwiftBot/actions)

SwiftBot is an async Telegram bot framework built for simplicity and correctness. It offers typed decorators, composable filters, a middleware chain, persistent state (FSM) storage, HTTP/2 connection pooling with Telegram `Retry-After` compliance, and a full typed error hierarchy — plus a built-in testing harness, typed Bot API models, deep-linking utilities, Redis storage, proxy support, and up-to-date Bot API 2026 coverage.

## 🚀 Key Features

### Developer Experience
- **Telethon-Style Decorators**: Clean, intuitive `@client.on(Message(...))` syntax
- **Command Router with Trie**: O(m) command lookup for registered slash commands
- **Regex Pattern Matching**: Powerful message filtering
- **Composable Filters**: Exact-text, regex, and custom function filters
- **Type Hints**: Full IDE support
- **Rich Context Object**: Easy access to all update data, plus `ctx.reply()`, `ctx.answer()` shortcuts

### Robustness
- **Persistent FSM Storage**: State survives restarts — in-memory, JSON-file, or Redis backends (pluggable via `BaseStorage`, with per-key TTL via `StateManager`)
- **Testing Harness**: `FakePool` + `TestClient` let you run handlers against the real router, worker pool, filters and middleware with zero network calls — every outgoing API request is recorded and responses are scriptable
- **Typed Models**: `User`, `Chat`, `Message`, `CallbackQuery`, `InlineKeyboardMarkup`, `Document` with tolerant `from_dict`/`to_dict`
- **CallbackData**: Type-safe typed callback payloads with `pack`/`unpack` and a 64-byte guard
- **Deep Linking**: `create_start_link`, `encode_payload`, `decode_payload`, `parse_start_param`
- **Bot API 2026**: New methods (managed bots, guest mode, rich messages, live photos, ephemeral messages) and new update kinds (business messages, purchases)
- **Rate-Limit Compliance**: Honors Telegram `Retry-After` on 429 responses, with circuit breaker
- **Typed Error Hierarchy**: Catch `ChatNotFound`, `TooManyRequests`, `Forbidden`, `InvalidToken`, etc.
- **Worker Pool with Backpressure**: Bounded concurrency and a dead-letter queue for failed updates
- **Webhook Server**: Secret-token verification, size limits, and health/metrics endpoints
- **File Support**: `InputFile` for local uploads, plus `get_file`/`download_file` helpers
- **HTTP/2 Connection Pooling**: Built on httpx with keep-alive connections
- **Proxy Support**: `SwiftBot(proxy="http/https/socks5://...")` routes all API traffic through a proxy
- **Centralized Exception Handling** and built-in metrics

## 📦 Installation

```bash
pip install swiftbot

# Or from GitHub
pip install git+https://github.com/Arjun-M/SwiftBot.git
```

## 🎯 Quick Start

```python
import asyncio
from swiftbot import SwiftBot
from swiftbot.types import Message
from swiftbot.middleware import Logger, RateLimiter

# Initialize bot
client = SwiftBot(
    token="YOUR_BOT_TOKEN",
    worker_pool_size=50,
    enable_http2=True
)

# Add cache-based middleware
client.use(Logger(level="INFO"))
client.use(RateLimiter(rate=10, per=60))

# Simple command handler
@client.on(Message(pattern=r"^/start"))
async def start(ctx):
    await ctx.reply("Hello! I'm SwiftBot 🚀")

# Run bot
asyncio.run(client.run())
```

## 📖 Documentation

### Client Initialization

```python
from swiftbot import SwiftBot

client = SwiftBot(
    token="YOUR_BOT_TOKEN",
    parse_mode="HTML",
    worker_pool_size=50,
    max_connections=100,
    timeout=30,
    enable_http2=True,
    enable_centralized_exceptions=True
)
```

### Event Handlers

```python
from swiftbot.types import Message, CallbackQuery

# Message handlers
@client.on(Message())  # All messages
@client.on(Message(text="hello"))  # Exact text match
@client.on(Message(pattern=r"^/start"))  # Regex pattern

# Callback query handlers
@client.on(CallbackQuery(data="button_1"))
@client.on(CallbackQuery(pattern=r"page_(\d+)"))
```

### Context Object

```python
@client.on(Message())
async def handler(ctx):
    # Message data
    ctx.text          # Message text
    ctx.user          # Sender user object
    ctx.chat          # Chat object
    ctx.args          # Command arguments
    ctx.match         # Regex match object

    # Reply methods
    await ctx.reply("Text")
    await ctx.edit("New text")
    await ctx.delete()
    await ctx.forward_to(chat_id)
```

### In-built Middleware

```python
from swiftbot.middleware import Logger, RateLimiter, Auth, AnalyticsCollector

# Logging (no external dependencies)
client.use(Logger(level="INFO", format="colored"))

# Rate limiting (in-memory cache)
client.use(RateLimiter(rate=10, per=60))

# Authentication (cache-based user management)
client.use(Auth(admin_list=[123, 456]))

# Analytics (cache-based metrics)
client.use(AnalyticsCollector(enable_real_time=True))
```

## 🏗️ Architecture

### Cache-Based Design
- **No External Dependencies** for core functionality
- **In-Memory Caching** for middleware data
- **Automatic Cleanup** of old cache entries
- **High Performance** without database overhead

### Connection Pool
- HTTP/2 multiplexing for 100+ concurrent streams
- Persistent keep-alive connections
- Automatic connection recycling
- Circuit breaker for fault tolerance

### Worker Pool
- Configurable worker count
- Bounded queue with backpressure
- Dead-letter queue for failed updates (exceptions preserved, retryable via `retry_dead_letters()`)
- Graceful drain on shutdown


## 🔧 Development

### Project Structure

```
swiftbot/
├── __init__.py           # Package initialization
├── client.py             # Main SwiftBot class
├── context.py            # Context object
├── types.py              # Event types
├── filters.py            # Filter system
├── storage.py            # FSM storage backends (memory + JSON file)
├── router.py             # Command router
├── webhook/              # aiohttp webhook server
├── exceptions/           # Exception handling
│   ├── base.py
│   ├── handlers.py
│   ├── api.py
│   └── telegram.py     # Typed Telegram error hierarchy
├── middleware/           # Logger, RateLimiter, Auth, AnalyticsCollector
│   ├── base.py
│   ├── logger.py
│   ├── rate_limiter.py
│   ├── auth.py
│   └── analytics.py
└── examples/             # Example bots
    └── basic_bot.py

Tests live in `tests/` and run via CI on every push.
```

## 🎯 Use Cases

- ✅ **Lightweight bots** without external dependencies
- ✅ **High-performance applications** needing speed
- ✅ **Serverless deployments** with minimal footprint
- ✅ **Development environments** with quick setup
- ✅ **Educational projects** learning bot development

## 🧪 Testing Your Bot

The built-in harness runs your handlers end to end without a single network call:

```python
import pytest
from swiftbot import SwiftBot
from swiftbot.testing import TestClient
from swiftbot.types import Message
from swiftbot.filters import Command

bot = SwiftBot(token="0000000000:TEST")

@bot.on(Message(text=Command("start")))
async def start(ctx):
    await ctx.reply("Hello!")

async def test_start_handler():
    async with TestClient(bot) as client:
        await client.send_update({
            "update_id": 1,
            "message": {
                "message_id": 1, "date": 1000,
                "chat": {"id": 42, "type": "private"},
                "from": {"id": 7, "is_bot": False, "first_name": "Tester"},
                "text": "/start",
            },
        })

    assert client.outgoing[0]["method"] == "sendMessage"
    assert client.outgoing[0]["params"]["text"] == "Hello!"
    assert client.outgoing[0]["params"]["chat_id"] == 42
```

`FakePool.script("methodName", result=...)` and `FakePool.script("methodName", error={"error_code": 400, "description": "..."})` let you drive any API response, and the pool records every outgoing call with method and params.

## 🌟 v1.5.0 — The Standout Release

v1.5 adds a full set of advanced framework capabilities: dependency-injected
handler pipelines, declarative command specs, an outbound API transformer
layer, middleware bundles with error boundaries, dispatch routing, typed
wizards, graceful shutdown, a plugin registry, and composable filter algebra.
The full documentation site lives in `docs/index.html`.

| Feature | Module |
| --- | --- |
| Declarative handler pipelines with **dependency injection** | `swiftbot.pipeline` |
| Declarative typed command specs with auto `/help` | `swiftbot.commands` |
| **Outbound transformer layer** (auto typing, idempotency, Recorder) | `swiftbot.transformer` |
| Middleware bundles with **error boundaries** | `swiftbot.composer` |
| Pre-handler dispatch table | `bot.route()` |
| Typed wizards with data carry | `swiftbot.wizard` |
| Graceful shutdown (signal + drain) | `bot.run_shutdown()` |
| First-party plugin registry | `swiftbot.plugins` |
| `F` filter algebra | `swiftbot.filters` (`F = ...`) |

```python
# Dependency-injected pipeline handler — no globals needed
from swiftbot.pipeline import Pipeline
from swiftbot.filters import F

async def stats(ctx, db, redis):
    await ctx.reply(f"{await db.count_users()} users · ping={await redis.ping()}")

pipe = Pipeline().deps(db=my_db, redis=my_redis)
pipe.handle(F.command("stats"), stats)
bot.pipeline(pipe)
```

## 🌟 v1.6.0 — Dialogues, Scopes & Safety Nets

v1.6 adds the state-machine and safety-net layer: **state-carrying dialogues**
(declared transition graphs, typed carry data between states, per-state
timeouts with an expiry hook), **scoped middleware chains** guarded by
predicates over the raw update, **outbound rate-limit throttling** as a
transformer, a **fluent `Reply` builder**, and **fallback / unknown-command
handlers**. Documentation site: `docs/index.html`.

| Feature | Module |
| --- | --- |
| State-carrying dialogue FSM with transition graph + timeout | `swiftbot.dialogue` |
| Predicate-guarded scoped middleware | `swiftbot.scopes` + `bot.scope()` |
| Outbound token-bucket rate limiting | `swiftbot.throttle` |
| Fluent reply builder | `swiftbot.reply` (`Reply(ctx)`) |
| Fallback + unknown-command handlers | `bot.fallback()`, `bot.on_unknown_command()` |

```python
# A dialogue: states carry their own data, transitions are declared
survey = bot.dialogue("survey")

@survey.state("ask_name", next=["ask_age"])
async def ask_name(ctx, prev=None):
    await ctx.reply("What's your name?")
    return Dialogue.next("ask_age", carry=ctx.text)

@survey.state("ask_age", timeout=120.0)
async def ask_age(ctx, prev=None):
    await ctx.reply(f"Hi {prev}, how old are you?")
    return Dialogue.end

# Scoped middleware — runs only where the predicate matches
bot.scope(lambda u: u.get("message", {}).get("chat", {}).get("type") == "private") \
   .use(plugins.session_limiter(min_interval=1.0))

# Outbound rate limiting
bot.api.config.use(throttle(max_per_second=20.0, per_chat=4.0))

# Safety nets
@bot.fallback
async def catch_all(ctx):
    await ctx.reply("I didn't catch that — try /help.")
```

## 🆕 What's New in 1.4.0

| Module | What it gives you |
| --- | --- |
| `swiftbot.testing` | `FakePool` + `TestClient` — network-free handler tests |
| `swiftbot.callback_data` | Typed callback payloads (`pack`/`unpack`/`filter`) |
| `swiftbot.deep_linking` | Deep-link creation and payload encode/decode |
| `swiftbot.models` | Typed `User`/`Chat`/`Message`/`CallbackQuery`/`Document` models |
| `swiftbot.storage` | `RedisStorage` alongside `MemoryStorage`/`JSONFileStorage` |
| `swiftbot.connection.pool` | Proxy support (`SwiftBot(proxy=...)`) |
| `swiftbot.api.telegram` | 11 Bot API 2026 methods (managed bots, guest mode, rich messages, live photos, ephemeral messages) |
| `swiftbot.update_types` | 9 new update kinds (business messages, guest messages, purchases) |

## 🤝 Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

## 📄 License

MIT License - Copyright (c) 2025 Arjun-M/SwiftBot

## 🙏 Acknowledgments

- Designed with clean decorator ergonomics in mind
- Built on [httpx](https://www.python-httpx.org/) for HTTP/2

---
