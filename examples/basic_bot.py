"""
Basic SwiftBot example — polling mode, command routing, FSM state, and errors.

Usage:
    BOT_TOKEN=123:ABC python examples/basic_bot.py

State survives restarts because the bot is configured with a persistent
storage backend (``JSONFileStorage``). Conversation steps are tracked via
the context-level FSM helpers ``ctx.set_state`` / ``ctx.get_state`` /
``ctx.clear_state``.
"""

import asyncio
import os
from swiftbot import SwiftBot
from swiftbot.types import Message
from swiftbot.storage import JSONFileStorage
from swiftbot.exceptions import ChatNotFound, Forbidden


bot = SwiftBot(
    token=os.environ["BOT_TOKEN"],
    storage=JSONFileStorage("bot_state.json"),
    state_ttl=3600,  # expire idle conversation state after 1 hour
)


# --- Commands -----------------------------------------------------------

@bot.on(Message(text="/start"))
async def cmd_start(ctx):
    await ctx.set_state({"step": "name"})
    await ctx.reply("Hi! What is your name?")


@bot.on(Message(text="/cancel"))
async def cmd_cancel(ctx):
    await ctx.clear_state()
    await ctx.reply("Cancelled. State cleared.")


# --- A multi-step conversation (FSM) ------------------------------------

@bot.on(Message(pattern=r"^.+"))
async def on_any_text(ctx):
    state = await ctx.get_state()
    if state and state.get("step") == "name":
        name = ctx.text
        await ctx.set_state({"step": "age", "name": name})
        await ctx.reply(f"Nice to meet you, {name}! How old are you?")
        return

    if state and state.get("step") == "age":
        age = ctx.text
        name = state.get("name", "friend")
        await ctx.clear_state()
        await ctx.reply(f"Got it — {name}, {age} years old. Done!")
        return

    await ctx.reply("Send /start to begin a conversation, or /cancel to reset.")


# --- Typed error handling -------------------------------------------------

async def safe_send(chat_id, text):
    """Send a message and classify Telegram errors instead of catching
    bare ``Exception``."""
    try:
        await bot.send_message(chat_id, text)
    except ChatNotFound:
        print(f"chat {chat_id} no longer exists — delete from DB")
    except Forbidden:
        print(f"bot was blocked by {chat_id}")
    except Exception as exc:  # noqa: BLE001 — log everything else
        print(f"unexpected telegram error: {exc}")


async def main():
    await bot.run_polling(allowed_updates=["message"])


if __name__ == "__main__":
    asyncio.run(main())
