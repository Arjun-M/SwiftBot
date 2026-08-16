# 3. Handlers and the Context

This page explains how SwiftBot decides which of your handlers runs for an incoming update, and everything the `Context` object gives you inside a handler.

## Registering handlers

SwiftBot uses decorator syntax inspired by Telethon. The argument to `@bot.on()` is an **event type** object that describes which updates the handler wants:

```python
from swiftbot.types import Message, CallbackQuery

@bot.on(Message(text="/start"))
async def start(ctx):
    ...

@bot.on(CallbackQuery(data="buy"))
async def on_buy(ctx):
    ...
```

| Event type | Matches |
|---|---|
| `Message(text="/start")` | a message whose text is exactly `/start` |
| `Message(pattern=r"hello (.+)")` | a message whose text matches the regex; groups are available in the match object |
| `Message(filters=F.private)` | any private message passing the `F` filter (see [Filters](04_Filters.md)) |
| `CallbackQuery(data="buy")` | an inline button press whose callback data is `"buy"` |
| `CallbackQuery(pattern=r"^buy:(\d+)$")` | callback data matching a regex |
| `InlineQuery()` | inline-mode queries |
| `EditedMessage()`, `ChatMemberUpdated()`, `PollAnswer()` | the corresponding update types |

Handlers for a given event type are matched in registration order and the first match wins. If two of your handlers could both match the same message, only the first registered one ever runs — see the "nothing happens" entry in [Troubleshooting and Pitfalls](23_Troubleshooting.md).

## How routing decides <a id="how-routing-decides"></a>

When an update arrives, SwiftBot works down a priority list and stops at the first thing that claims it:

| Priority | Stage | Notes |
|---|---|---|
| 1 | Command router | Trie-based handlers from `BotCommands` middleware (see [Commands](05_Commands.md#botcommands-declarative-commands)) handle `/`-commands first |
| 2 | Active dialogues | A user mid-conversation (see [Dialogues and Wizards](10_Dialogues.md)) has their current step run |
| 3 | Scoped middleware | `bot.scope(...)` traffic slices (see [Scopes](13_Scopes.md)) |
| 4 | Pipelines | `bot.pipeline()` handler trees (see [Pipelines](15_Pipelines.md)) |
| 5 | Decorator handlers | Your `@bot.on(...)` handlers |
| 6 | Fallback | `@bot.fallback` catches anything unclaimed |
| 7 | Unknown command | `@bot.on_unknown_command` catches `/command` that matched nothing |

## Fallback and unknown-command handlers

These two are your safety nets:

```python
@bot.fallback
async def catch_all(ctx):
    await ctx.reply("Sorry, I don't understand that.")

@bot.on_unknown_command
async def unknown(ctx):
    await ctx.reply(f"Unknown command: {ctx.command.name}")
```

`fallback` runs for updates no handler claimed; `on_unknown_command` runs specifically when a message begins with `/` but matches no route.

## The `Context` object

`ctx` is handed to every handler and bundles everything you need in one place:

| Member | What it gives you |
|---|---|
| `ctx.bot` | the `SwiftBot` instance |
| `ctx.update` | the raw parsed `Update` object |
| `ctx.message`, `ctx.callback_query`, ... | the specific update object for the event type |
| `ctx.text` | message text (or callback data), normalized |
| `ctx.user`, `ctx.chat` | `User` and `Chat` model objects (see [Models and Types](19_Models.md)) |
| `ctx.command` | a `ParsedCommand` when the command router matched |
| `ctx.reply(text)` | reply in the same chat, using the bot's default parse mode |
| `ctx.answer(text)`, `ctx.answer_callback(text, show_alert=False)` | answer a callback query (see [Reply Helpers](06_ReplyHelpers.md#the-basics-on-context)) |
| `ctx.edit(text)` | edit the triggering message |
| `ctx.send_message(...)`, `ctx.send_photo(...)` | convenience wrappers around the API |
| `ctx.set_state(...)`, `ctx.get_state()`, `ctx.clear_state()` | per-user state shortcuts (see [Storage and State](17_StorageAndState.md#the-statemanager)) |
| `ctx.chat_action("typing")` | send typing and upload indicators |
| `ctx.forward(...)`, `ctx.delete_message(...)` | forwarding and deleting helpers |

## Errors never kill the bot

Handlers run inside the worker pool (see [Bot Core](02_BotCore.md)). If a handler raises an exception, SwiftBot routes it through the centralized exception handler (see [Exceptions](18_Exceptions.md#the-centralized-handler)) and moves on — one crashed handler never brings down the polling loop.
