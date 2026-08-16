# SwiftBot Documentation

SwiftBot is an ultra-fast Telegram bot framework for Python. This folder holds its documentation: one Markdown file per topic, arranged so you can read them top to bottom as a course, or jump straight to the feature you need.

If you have never written a bot before, start with [Getting Started](01_GettingStarted.md). It explains what a Telegram bot actually is and how to get your token from @BotFather. Everything else builds on it.

## How to read this documentation

| Order | File | What you will learn |
|---|---|---|
| 1 | [Getting Started](01_GettingStarted.md) | What a bot is, getting your token from @BotFather, installing SwiftBot, your first bot in 15 lines |
| 2 | [Bot Core](02_BotCore.md) | The `SwiftBot` constructor options, polling vs webhook, starting and stopping the bot |
| 3 | [Handlers and the Context](03_HandlersAndContext.md) | `@bot.on()`, how routing picks a handler, the `Context` object, fallbacks |
| 4 | [Filters](04_Filters.md) | The `F` filter algebra (`&`, `|`, `~`), presets, user/chat/command filters |
| 5 | [Commands](05_Commands.md) | Pattern matching, `CommandFilter`, `BotCommands` declarative commands with typed arguments |
| 6 | [Reply Helpers](06_ReplyHelpers.md) | `ctx.reply()`, answering callbacks, editing, the fluent `Reply` builder |
| 7 | [Buttons and Keyboards](07_Buttons.md) | Inline keyboards, reply keyboards, buttons, link buttons, removing keyboards |
| 8 | [Typed Callback Data](08_CallbackData.md) | Typed, collision-safe inline button payloads with `CallbackData` |
| 9 | [Deep Linking](09_DeepLinking.md) | Referral links, `start`/`startgroup` parameters, payload encoding |
| 10 | [Dialogues and Wizards](10_Dialogues.md) | State machines for multi-step conversations: `Dialogue` and `Wizard` |
| 11 | [Middleware](11_Middleware.md) | The middleware chain, `Logger`, `Auth`, `RateLimiter`, `AnalyticsCollector` |
| 12 | [Plugins](12_Plugins.md) | Ready-made middleware: spam deflector, session limiter, idempotency, whitelist |
| 13 | [Scopes](13_Scopes.md) | Running middleware on a slice of traffic only (e.g. groups only) |
| 14 | [Composer](14_Composer.md) | Bundling middleware with per-module error boundaries |
| 15 | [Pipelines](15_Pipelines.md) | Dependency-injected handler trees |
| 16 | [Transformers](16_Transformers.md) | Intercepting every outbound API call, outbound rate limiting |
| 17 | [Storage and State](17_StorageAndState.md#the-statemanager) | Memory / JSON / Redis backends, `StateManager`, TTL expiry |
| 18 | [Exceptions](18_Exceptions.md#the-hierarchy) | The typed Telegram error hierarchy, the "send safely" pattern |
| 19 | [Models and Types](19_Models.md) | `User`, `Chat`, `Message`, `CallbackQuery`, `Update` and friends |
| 20 | [API Reference](20_API.md#messages) | The full Telegram Bot API surface grouped by topic |
| 21 | [Testing Without a Network](21_Testing.md) | Testing your bot fully offline with `FakePool`, `TestClient`, `record()` |
| 22 | [Webhooks](22_Webhooks.md) | The built-in webhook server, secret tokens, health and metrics |
| 23 | [Troubleshooting and Pitfalls](23_Troubleshooting.md) | Common mistakes, Telegram limits, and fixes |

## A five-minute summary of how SwiftBot works

Every SwiftBot bot follows the same shape. You create a bot object with your token, register `async` handlers with `@bot.on(...)` that describe which updates they care about, and start the run loop. When Telegram delivers an update, SwiftBot matches it against your handlers in priority order, hands it to the first match wrapped in a `Context`, and your handler replies through `ctx.reply()`.

```python
import asyncio
from swiftbot import SwiftBot
from swiftbot.types import Message

bot = SwiftBot(token="YOUR_TOKEN")      # see Getting Started — never hardcode a real token

@bot.on(Message(text="/start"))
async def start(ctx):
    await ctx.reply("Welcome!")

asyncio.run(bot.run())
```

Middleware, state machines, plugins, transformers and everything else in the files above slot into this same loop — you add them as you need them, and a beginner never has to understand all of them to ship a bot.

## Keep your token safe

Your bot token is the password to your bot. Keep it out of git (put it in an environment variable and read it with `os.environ["BOT_TOKEN"]`), out of docs, and out of any file you share. The examples in this folder use `YOUR_TOKEN` as a placeholder on purpose. See [Getting Started](01_GettingStarted.md#getting-your-token-from-botfather) and [Troubleshooting and Pitfalls](23_Troubleshooting.md) for details.
