"""
SwiftBot Advanced Example
Copyright (c) 2025 Arjun-M/SwiftBot

This example demonstrates advanced features:
- Middleware (logging, rate limiting, authentication)
- User data persistence with Redis
- Broadcasting with progress tracking
- State management (FSM)
- Multiple storage backends
"""

import asyncio
import redis
from swiftbot import SwiftBot
from swiftbot.types import Message, CallbackQuery
from swiftbot.filters import Filters as F
from swiftbot.middleware import Logger, RateLimiter, Auth, UserDataMiddleware
from swiftbot.storage import RedisStore, FileStore
from swiftbot.broadcast import Broadcaster


# Initialize bot with advanced configuration
client = SwiftBot(
    token="YOUR_BOT_TOKEN_HERE",
    parse_mode="HTML",
    worker_pool_size=50,
    max_connections=100,
    enable_http2=True,
    connection_pool={
        'max_connections': 100,
        'max_keepalive_connections': 50,
        'keepalive_expiry': 30.0,
    },
    retry_config={
        'max_retries': 3,
        'backoff_factor': 0.5,
        'retry_on_status': [429, 500, 502, 503, 504],
    },
)

# Setup storage (Redis recommended for production)
# Option 1: Redis (recommended for production)
try:
    redis_conn = redis.Redis(host='localhost', port=6379, db=0, decode_responses=False)
    storage = RedisStore(connection=redis_conn, prefix="swiftbot")
    print("Using Redis storage")
except:
    # Option 2: File storage (fallback for development)
    storage = FileStore(base_path="./data")
    print("Using File storage")

# Add middleware
# 1. Logging middleware
client.use(Logger(
    level="INFO",
    format="text",
    include_updates=True,
    include_responses=False
))

# 2. Rate limiting middleware
client.use(RateLimiter(
    rate=10,  # 10 requests
    per=60,   # per 60 seconds
    strategy="sliding_window",
    storage=redis_conn if 'redis_conn' in locals() else None,
    key_func=lambda ctx: f"user:{ctx.user.id}",
    on_exceeded=lambda ctx: ctx.reply("⚠️ Slow down! Too many requests.")
))

# 3. Authentication middleware
ADMIN_IDS = [123456789]  # Replace with your user ID
BANNED_IDS = []

client.use(Auth(
    admin_list=ADMIN_IDS,
    blacklist=BANNED_IDS,
    on_unauthorized=lambda ctx: ctx.reply("🚫 You are banned from using this bot.")
))

# 4. User data persistence middleware
client.use(UserDataMiddleware(
    storage=storage,
    auto_create=True,
    cache_ttl=300
))

# Initialize broadcaster
broadcaster = Broadcaster(
    bot=client,
    storage=storage,
    workers=20,
    rate_limit=30
)


# ===== Command Handlers =====

@client.on(Message(F.command("start")))
async def start_command(ctx):
    """
    Start command with user data tracking.
    Demonstrates user data persistence.
    """
    # Track user start
    await ctx.user_data.set("started", True)
    await ctx.user_data.set("start_count", 
        await ctx.user_data.get("start_count", 0) + 1
    )

    start_count = await ctx.user_data.get("start_count")

    await ctx.reply(
        f"<b>👋 Welcome to SwiftBot Advanced!</b>\n\n"
        f"This is your <b>visit #{start_count}</b>\n\n"
        f"<b>Available commands:</b>\n"
        f"/start - Start the bot\n"
        f"/profile - Your profile\n"
        f"/setname <name> - Set your name\n"
        f"/broadcast - Broadcast (admin only)\n"
        f"/stats - Bot statistics"
    )


@client.on(Message(F.command("profile")))
async def profile_command(ctx):
    """
    Show user profile from stored data.
    Demonstrates reading user data.
    """
    name = await ctx.user_data.get("name", "Not set")
    start_count = await ctx.user_data.get("start_count", 0)
    subscribed = await ctx.user_data.get("subscribed", False)

    text = (
        f"<b>👤 Your Profile</b>\n\n"
        f"<b>User ID:</b> {ctx.user.id}\n"
        f"<b>Username:</b> @{ctx.user.username or 'None'}\n"
        f"<b>Name:</b> {name}\n"
        f"<b>Visits:</b> {start_count}\n"
        f"<b>Subscribed:</b> {'Yes' if subscribed else 'No'}"
    )

    await ctx.reply(text)


@client.on(Message(F.command("setname")))
async def setname_command(ctx):
    """
    Set user name in storage.
    Demonstrates writing user data.
    """
    if not ctx.args:
        await ctx.reply("Usage: /setname <your name>")
        return

    name = " ".join(ctx.args)
    await ctx.user_data.set("name", name)

    await ctx.reply(f"✅ Name set to: {name}")


@client.on(Message(F.command("subscribe")))
async def subscribe_command(ctx):
    """
    Subscribe to broadcasts.
    Demonstrates boolean user data.
    """
    await ctx.user_data.set("subscribed", True)
    await ctx.reply("✅ You are now subscribed to broadcasts!")


@client.on(Message(F.command("unsubscribe")))
async def unsubscribe_command(ctx):
    """Unsubscribe from broadcasts"""
    await ctx.user_data.set("subscribed", False)
    await ctx.reply("❌ You are now unsubscribed from broadcasts.")


@client.on(Message(F.command("broadcast")))
async def broadcast_command(ctx):
    """
    Admin-only broadcast command.
    Demonstrates admin check and broadcasting with progress.
    """
    # Check if user is admin
    if not hasattr(ctx, 'is_admin') or not ctx.is_admin:
        await ctx.reply("🚫 This command is admin-only.")
        return

    if not ctx.args:
        await ctx.reply("Usage: /broadcast <message>")
        return

    message_text = " ".join(ctx.args)

    # Get all subscribed users
    # Note: In production, implement proper user listing from storage
    user_ids = [ctx.user.id]  # Demo: just send to yourself

    status_msg = await ctx.reply("📢 Broadcasting... 0%")

    # Broadcast with progress updates
    async for progress in broadcaster.send_with_progress(
        text=f"📢 <b>Broadcast Message:</b>\n\n{message_text}",
        users=user_ids
    ):
        # Update progress
        percentage = (progress.sent / progress.total) * 100
        await status_msg.edit(
            f"📢 Broadcasting... {percentage:.1f}%\n"
            f"Sent: {progress.sent}/{progress.total}\n"
            f"Failed: {progress.failed}"
        )

    await status_msg.edit(
        f"✅ Broadcast complete!\n"
        f"Sent: {progress.sent}\n"
        f"Failed: {progress.failed}"
    )


@client.on(Message(F.command("stats")))
async def stats_command(ctx):
    """
    Show bot statistics.
    Demonstrates accessing bot stats.
    """
    stats = client.get_stats()

    text = (
        f"<b>📊 Bot Statistics</b>\n\n"
        f"<b>Status:</b> {'Running' if stats['running'] else 'Stopped'}\n"
        f"<b>Workers:</b> {stats['worker_pool']['num_workers']}\n"
        f"<b>Queue Size:</b> {stats['worker_pool']['queue_size']}\n"
        f"<b>Processed:</b> {stats['worker_pool']['processed']}\n"
        f"<b>Failed:</b> {stats['worker_pool']['failed']}\n"
        f"<b>HTTP/2:</b> {'Enabled' if stats['connection_pool']['http2_enabled'] else 'Disabled'}\n"
        f"<b>Max Connections:</b> {stats['connection_pool']['max_connections']}\n"
        f"<b>Handlers:</b> {sum(stats['router'].values())}\n"
        f"<b>Middleware:</b> {stats['middleware_count']}"
    )

    await ctx.reply(text)


# ===== Pattern Matching Examples =====

@client.on(Message(pattern=r"^price\s+(\w+)$"))
async def price_check(ctx):
    """
    Check price using regex pattern.
    Demonstrates regex capture groups.
    """
    ticker = ctx.match.group(1).upper()
    await ctx.reply(f"💰 Checking price for {ticker}...")
    # Add your price checking logic here


@client.on(Message(pattern=r"(?P<action>buy|sell)\s+(?P<qty>\d+)\s+(?P<ticker>\w+)"))
async def trading_command(ctx):
    """
    Trading command with named capture groups.
    Demonstrates advanced regex with named groups.
    """
    action = ctx.match.group('action')
    quantity = int(ctx.match.group('qty'))
    ticker = ctx.match.group('ticker').upper()

    await ctx.reply(
        f"📈 <b>Trading Order:</b>\n"
        f"Action: {action.upper()}\n"
        f"Quantity: {quantity}\n"
        f"Ticker: {ticker}"
    )


# ===== Callback Query Handlers =====

@client.on(CallbackQuery(pattern=r"page_(\d+)"))
async def pagination_handler(ctx):
    """
    Handle pagination buttons.
    Demonstrates callback query with regex.
    """
    page = int(ctx.match.group(1))

    await ctx.answer()  # Answer the callback query
    await ctx.edit(f"📄 Showing page {page}")


# ===== Filter Composition Examples =====

@client.on(Message((F.photo | F.video) & F.caption))
async def media_with_caption(ctx):
    """
    Handle media with captions.
    Demonstrates filter composition with OR and AND.
    """
    media_type = "photo" if hasattr(ctx.message, 'photo') else "video"
    await ctx.reply(f"📸 Got {media_type} with caption: {ctx.caption}")


@client.on(Message(F.text & F.private & ~F.forwarded))
async def private_original_text(ctx):
    """
    Handle non-forwarded text in private chats.
    Demonstrates filter composition with NOT.
    """
    # Handle private, non-forwarded text messages
    pass


async def main():
    """Main function to run the bot"""
    print("=" * 50)
    print("SwiftBot Advanced Example")
    print("Copyright (c) 2025 Arjun-M/SwiftBot")
    print("=" * 50)
    print()
    print("Starting bot...")
    print(f"Storage: {type(storage).__name__}")
    print(f"Middleware: {len(client.middleware)} active")
    print()
    print("Press Ctrl+C to stop")
    print("=" * 50)

    try:
        await client.run_polling(
            timeout=30,
            limit=100,
            drop_pending_updates=False,
        )
    except KeyboardInterrupt:
        print("\n" + "=" * 50)
        print("Stopping bot...")
        client.stop()
        print("Bot stopped successfully")
        print("=" * 50)


if __name__ == "__main__":
    asyncio.run(main())
