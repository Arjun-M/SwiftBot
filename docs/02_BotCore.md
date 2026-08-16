# 2. Bot Core

This page covers the `SwiftBot` object itself: its constructor options, the two ways it can receive updates, and how to start and stop it. You met the constructor in [Getting Started](01_GettingStarted.md); here is everything it can do.

## The constructor <a id="the-constructor"></a>

Every option has a sensible default, so in practice you usually only pass `token`.

```python
bot = SwiftBot(
    token="YOUR_TOKEN",                # required — from @BotFather
    parse_mode="HTML",                 # default formatting for ctx.reply / send_message
    async_mode=True,                   # async update processing
    worker_pool_size=50,               # concurrent update handlers
    max_connections=100,               # httpx connection pool size
    timeout=30.0,                      # per-request timeout in seconds
    api_base_url="https://api.telegram.org",
    proxy=None,                        # e.g. "http://user:pass@host:port"
    connection_pool=None,              # advanced pool config dict
    retry_config=None,                 # retry behaviour dict
    rate_limiter=None,                 # bot-side rate limiting dict
    debug=False,                       # verbose logging
    enable_centralized_exceptions=True,
    storage=None,                      # FSM/storage backend
    state_ttl=None,                    # seconds before state expires (None = never)
)
```

The three options beginners actually need to understand are the following. **`worker_pool_size`** controls how many updates SwiftBot can handle at the same time — if 50 users message you simultaneously, all 50 can be processed concurrently. Higher values mean more parallelism and more memory. **`parse_mode`** is how Telegram interprets formatting by default: `"HTML"` lets you write `<b>bold</b>`, while `"MarkdownV2"` uses `*bold*`. You can override it per message. **`state_ttl`** is a global expiry for conversation state — a user who abandons a dialogue has their state cleared automatically after this many seconds (see [Storage and State](17_StorageAndState.md#the-statemanager)).

## Polling vs webhook <a id="polling-vs-webhook"></a>

Telegram offers two ways for your bot to receive updates, and `SwiftBot` supports both.

**Polling** means your bot repeatedly asks Telegram "any new messages?" and processes whatever comes back. It is the easiest mode for development and small bots:

```python
await bot.run_polling()
await bot.run_polling(timeout=30, limit=100,
                      allowed_updates=["message", "callback_query"])
```

`allowed_updates` tells Telegram which update types to send you. This matters for webhooks, because Telegram only forwards the types you asked for.

**Webhook** means Telegram pushes updates to a URL you host. It is better for production at scale, because Telegram delivers updates instantly instead of your bot polling for them. Webhooks are covered in full in [Webhooks](22_Webhooks.md), but the shorthand is:

```python
await bot.run_webhook(host="0.0.0.0", port=8443, path="/webhook")
```

## `run()`, `stop()`, and stats <a id="run-stop-and-stats"></a>

`bot.run()` picks the mode from its keyword arguments or defaults to polling. Both loops respect `bot.stop()`, which is how scripts and tests end the run cleanly:

```python
# Stop after 10 seconds
import asyncio
asyncio.create_task(asyncio.sleep(10)).add_done_callback(lambda _: bot.stop())
await bot.run()
```

Two helpers round out the core. `await bot.get_me()` verifies your token and returns your bot's identity — it is cached, so it doubles as a cheap startup health check. `bot.get_stats()` returns counters such as updates processed, handlers executed, and errors handled, useful for monitoring.
