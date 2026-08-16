# 1. Getting Started

This page is the beginning of the SwiftBot journey. It explains what a Telegram bot actually is, where your token comes from, how to install the library, and how to write your first bot. No prior bot experience is needed — you only need basic Python.

## What is a Telegram bot?

A Telegram bot is an ordinary program that talks to Telegram's servers instead of talking to users directly. The flow works like this: a user sends a message to your bot in Telegram, Telegram forwards that message to your program, your program decides what to say, and Telegram delivers the reply back to the user. Your program's only conversation partner is Telegram's API.

Two things are required for this to work. The first is **a bot token**, a secret string that identifies your bot. The second is **your program**, which authenticates with that token and uses SwiftBot to call Telegram's [Bot API](https://core.telegram.org/bots/api).

## Getting your token from @BotFather <a id="getting-your-token-from-botfather"></a>

Telegram's official bot [@BotFather](https://t.me/BotFather) hands out tokens. Message him on Telegram and send `/newbot`. He asks for a name (what users see) and a username (must end in `bot`). In return you receive a token that looks like this:

```
123456789:ABCdefGHIjklMNOpqrsTUVwxyz11
```

That string is your bot's password. Anyone who holds it can read your bot's messages and send messages as it. Keep it private, keep it out of git, and never paste it into documentation or chats. The conventional safe practice is to store it in an environment variable and read it at runtime:

```python
import os
token = os.environ["BOT_TOKEN"]
```

## Installation

```bash
pip install git+https://github.com/Arjun-M/SwiftBot.git
```

SwiftBot requires Python 3.10 or newer and pulls in `httpx` for HTTP/2 requests. Two optional extras come up later in this documentation: install `redis[hiredis]` if you want Redis-based state storage ([see Storage and State](17_StorageAndState.md#the-statemanager)), and `aiohttp` if you want the built-in webhook server ([see Webhooks](22_Webhooks.md#the-built-in-server)).

## Your first bot

Create a file called `bot.py` with the following content, replacing the placeholder with your real token from the environment.

```python
import asyncio
import os
from swiftbot import SwiftBot
from swiftbot.types import Message

bot = SwiftBot(token=os.environ["BOT_TOKEN"])

@bot.on(Message(text="/start"))
async def start_handler(ctx):
    await ctx.reply("Hi there! This is your first SwiftBot.")

@bot.on(Message(pattern=r"^.+"))
async def echo(ctx):
    await ctx.reply(f"You said: {ctx.text}")

asyncio.run(bot.run())
```

Run it with `BOT_TOKEN=your-token python bot.py`, find your bot on Telegram, and send `/start`. You should see a reply, and any other message gets echoed back. Here is what each piece does:

`SwiftBot(token=...)` creates the bot object. Nothing happens yet; the object only remembers your token and its defaults.

`@bot.on(...)` registers a **handler** — an `async` function that runs when an incoming update matches the condition you give it. `Message(text="/start")` matches a message whose text is exactly `/start`. The second handler uses `pattern=r"^.+"`, a regular expression matching any non-empty text, which catches everything the first handler missed.

`ctx` is the **context**, a wrapper around the incoming update with convenient methods such as `ctx.reply()`. `await ctx.reply(...)` sends a message back to the same chat. The `await` matters because sending a message over the network takes time; `async` handlers let the program keep working while it waits. Handlers must always be `async def`, and every network call inside them needs `await`.

`asyncio.run(bot.run())` connects to Telegram, starts pulling updates, and drives your handlers until you stop the program.

That is a complete working bot. The rest of this documentation explains every feature you can layer on top of this skeleton.
