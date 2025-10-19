"""
SwiftBot Basic Example
Copyright (c) 2025 Arjun-M/SwiftBot

This example demonstrates basic SwiftBot usage with simple handlers.
"""

import asyncio
from swiftbot import SwiftBot
from swiftbot.types import Message, CallbackQuery
from swiftbot.filters import Filters as F


# Initialize bot with your token
client = SwiftBot(
    token="YOUR_BOT_TOKEN_HERE",
    parse_mode="HTML",
    worker_pool_size=50,
    max_connections=100,
    enable_http2=True
)


# Simple command handler
@client.on(Message(F.command("start")))
async def start_command(ctx):
    """
    Handle /start command.
    This is the first message users see when they start the bot.

    Args:
        ctx: Context object containing message data and helper methods
    """
    await ctx.reply(
        f"<b>👋 Welcome to SwiftBot!</b>\n\n"
        f"Hi {ctx.user.first_name}! I'm an ultra-fast Telegram bot "
        f"built with SwiftBot framework.\n\n"
        f"Available commands:\n"
        f"/help - Show help\n"
        f"/info - Bot information\n"
        f"/echo <text> - Echo your message"
    )


# Help command
@client.on(Message(F.command("help")))
async def help_command(ctx):
    """Show help information"""
    await ctx.reply(
        "<b>📚 SwiftBot Help</b>\n\n"
        "<b>Commands:</b>\n"
        "/start - Start the bot\n"
        "/help - Show this help\n"
        "/info - Bot statistics\n"
        "/echo <text> - Echo text\n\n"
        "<b>Features:</b>\n"
        "• 30× faster routing\n"
        "• HTTP/2 connection pooling\n"
        "• Worker pool for concurrency\n"
        "• Enterprise middleware\n"
        "• Multiple storage backends"
    )


# Info command showing bot stats
@client.on(Message(F.command("info")))
async def info_command(ctx):
    """
    Show bot information and statistics.
    Demonstrates accessing bot statistics.
    """
    stats = client.get_stats()

    text = (
        f"<b>🤖 Bot Information</b>\n\n"
        f"<b>Status:</b> {'Running' if stats['running'] else 'Stopped'}\n"
        f"<b>Workers:</b> {stats['worker_pool']['num_workers']}\n"
        f"<b>Processed:</b> {stats['worker_pool']['processed']}\n"
        f"<b>Failed:</b> {stats['worker_pool']['failed']}\n"
        f"<b>HTTP/2:</b> {'Enabled' if stats['connection_pool']['http2_enabled'] else 'Disabled'}\n"
        f"<b>Handlers:</b> {sum(stats['router'].values())}\n"
        f"<b>Middleware:</b> {stats['middleware_count']}"
    )

    await ctx.reply(text)


# Echo command with arguments
@client.on(Message(F.command("echo")))
async def echo_command(ctx):
    """
    Echo command that repeats user's text.
    Demonstrates accessing command arguments.
    """
    if not ctx.args:
        await ctx.reply("Usage: /echo <text>")
        return

    text = " ".join(ctx.args)
    await ctx.reply(f"🔊 You said: {text}")


# Regex pattern matching
@client.on(Message(pattern=r"^hello|hi|hey", flags=0))
async def greeting_handler(ctx):
    """
    Handle greetings using regex pattern.
    Matches messages starting with hello, hi, or hey.
    """
    await ctx.reply(f"Hello {ctx.user.first_name}! 👋")


# Filter-based handler for photos
@client.on(Message(F.photo))
async def photo_handler(ctx):
    """
    Handle photo messages.
    Demonstrates media handling.
    """
    caption = ctx.caption or "(no caption)"
    await ctx.reply(f"📸 Nice photo! Caption: {caption}")


# Callback query handler
@client.on(CallbackQuery(pattern=r"button_(.+)"))
async def button_handler(ctx):
    """
    Handle inline keyboard button clicks.
    Demonstrates callback query handling with regex.
    """
    button_id = ctx.match.group(1)
    await ctx.answer(f"Button {button_id} clicked!")
    await ctx.edit(f"✅ You clicked button: {button_id}")


# Private chat only handler
@client.on(Message(F.private & F.text))
async def private_message_handler(ctx):
    """
    Handle any text message in private chats.
    Demonstrates filter composition.
    """
    # This will be called for any text message in private chat
    # that wasn't handled by other handlers
    pass


async def main():
    """
    Main function to start the bot.
    Uses async/await for proper async handling.
    """
    print("Starting SwiftBot...")
    print("Press Ctrl+C to stop")

    try:
        # Start bot in polling mode
        await client.run_polling(
            timeout=30,
            drop_pending_updates=False,
        )
    except KeyboardInterrupt:
        print("\nStopping bot...")
        client.stop()


if __name__ == "__main__":
    # Run the bot
    asyncio.run(main())
