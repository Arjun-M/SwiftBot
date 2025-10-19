# SwiftBot - Complete Usage Guide

**Copyright (c) 2025 Arjun-M/SwiftBot**

This guide provides comprehensive documentation on how to use SwiftBot framework effectively.

## Table of Contents

1. [Installation](#installation)
2. [Quick Start](#quick-start)
3. [Core Concepts](#core-concepts)
4. [Event Handlers](#event-handlers)
5. [Filters](#filters)
6. [Context Object](#context-object)
7. [Middleware](#middleware)
8. [Storage Backends](#storage-backends)
9. [Broadcasting](#broadcasting)
10. [Advanced Features](#advanced-features)
11. [Best Practices](#best-practices)
12. [Troubleshooting](#troubleshooting)

---

## Installation

### Basic Installation

```bash
pip install swiftbot
```

### With Optional Dependencies

```bash
# Redis support (recommended for production)
pip install swiftbot[redis]

# PostgreSQL support
pip install swiftbot[postgres]

# MongoDB support
pip install swiftbot[mongo]

# All optional dependencies
pip install swiftbot[full]
```

### Manual Installation from Source

```bash
# Clone or extract the SwiftBot package
cd SwiftBot
pip install -e .
```

---

## Quick Start

### Minimal Bot

```python
import asyncio
from swiftbot import SwiftBot
from swiftbot.types import Message

# Initialize bot
client = SwiftBot(token="YOUR_BOT_TOKEN")

# Define handler
@client.on(Message(text="hello"))
async def hello_handler(ctx):
    await ctx.reply("Hello!")

# Run bot
asyncio.run(client.run())
```

### Recommended Setup

```python
import asyncio
from swiftbot import SwiftBot
from swiftbot.types import Message
from swiftbot.filters import Filters as F

# Initialize with recommended settings
client = SwiftBot(
    token="YOUR_BOT_TOKEN",
    parse_mode="HTML",           # Default parse mode
    worker_pool_size=50,         # 50 concurrent workers
    max_connections=100,         # 100 HTTP connections
    enable_http2=True,           # Enable HTTP/2
)

@client.on(Message(F.command("start")))
async def start_command(ctx):
    await ctx.reply("<b>Welcome to my bot!</b>")

asyncio.run(client.run())
```

---

## Core Concepts

### 1. Client Initialization

The SwiftBot client is the main entry point:

```python
client = SwiftBot(
    token="YOUR_BOT_TOKEN",      # Required: Bot token from @BotFather
    parse_mode="HTML",            # Default: "HTML", "Markdown", or "MarkdownV2"
    async_mode=True,              # Use async mode (recommended)
    worker_pool_size=50,          # Number of concurrent workers
    max_connections=100,          # Max HTTP connections
    timeout=30,                   # Request timeout in seconds
    enable_http2=True,            # Enable HTTP/2 (faster)
)
```

### 2. Performance Configuration

For production, configure connection pooling:

```python
client = SwiftBot(
    token="YOUR_BOT_TOKEN",
    connection_pool={
        'max_connections': 100,          # Maximum connections
        'max_keepalive_connections': 50, # Persistent connections
        'keepalive_expiry': 30.0,        # Keep-alive duration
    },
    retry_config={
        'max_retries': 3,                # Retry failed requests
        'backoff_factor': 0.5,           # Exponential backoff
        'retry_on_status': [429, 500, 502, 503, 504],
    },
)
```

### 3. Decorator-Based Handlers

Register handlers using decorators:

```python
@client.on(EventType(...))
async def handler_name(ctx):
    # Handler logic
    await ctx.reply("Response")
```

---

## Event Handlers

### Message Handlers

Handle different types of messages:

```python
from swiftbot.types import Message

# Handle all messages
@client.on(Message())
async def all_messages(ctx):
    pass

# Exact text match
@client.on(Message(text="hello"))
async def exact_match(ctx):
    await ctx.reply("Hello!")

# Regex pattern matching
@client.on(Message(pattern=r"^/start"))
async def start_command(ctx):
    await ctx.reply("Starting...")

# Multiple patterns
@client.on(Message(pattern=[r"^buy .+", r"^purchase .+"]))
async def buy_handler(ctx):
    pass
```

### Callback Query Handlers

Handle inline keyboard button clicks:

```python
from swiftbot.types import CallbackQuery

# Handle all callbacks
@client.on(CallbackQuery())
async def all_callbacks(ctx):
    await ctx.answer("Processing...")
    await ctx.edit("Done!")

# Specific callback data
@client.on(CallbackQuery(data="button_1"))
async def button_1_handler(ctx):
    await ctx.answer()
    await ctx.edit("Button 1 clicked!")

# Regex pattern for callbacks
@client.on(CallbackQuery(pattern=r"page_(\d+)"))
async def pagination_handler(ctx):
    page = int(ctx.match.group(1))
    await ctx.answer()
    await ctx.edit(f"Page {page}")
```

### Inline Query Handlers

Handle inline mode queries:

```python
from swiftbot.types import InlineQuery

@client.on(InlineQuery())
async def inline_handler(ctx):
    query = ctx.query
    # Build results
    results = build_inline_results(query)
    await ctx.answer(results)

@client.on(InlineQuery(pattern=r"^search (.+)"))
async def inline_search(ctx):
    search_term = ctx.match.group(1)
    results = search_database(search_term)
    await ctx.answer(results)
```

### Other Event Types

```python
from swiftbot.types import (
    EditedMessage,
    ChatMemberUpdated,
    PollAnswer,
)

@client.on(EditedMessage())
async def edited_handler(ctx):
    await ctx.reply("Message was edited")

@client.on(ChatMemberUpdated())
async def member_updated(ctx):
    if ctx.new_member.status == "member":
        await ctx.reply(f"Welcome {ctx.new_member.user.first_name}!")
```

---

## Filters

Filters provide powerful message filtering capabilities.

### Basic Filters

```python
from swiftbot.filters import Filters as F

# Text messages
@client.on(Message(F.text))

# Private chats
@client.on(Message(F.private))

# Group chats
@client.on(Message(F.group))

# Forwarded messages
@client.on(Message(F.forwarded))

# Reply messages
@client.on(Message(F.reply))
```

### Media Filters

```python
# Photos
@client.on(Message(F.photo))

# Videos
@client.on(Message(F.video))

# Audio
@client.on(Message(F.audio))

# Documents
@client.on(Message(F.document))

# Voice messages
@client.on(Message(F.voice))

# Stickers
@client.on(Message(F.sticker))
```

### Command Filter

```python
# Single command
@client.on(Message(F.command("start")))
async def start(ctx):
    pass

# Multiple commands
@client.on(Message(F.command(["help", "h"])))
async def help_handler(ctx):
    pass
```

### Regex Filters

```python
# Text regex
@client.on(Message(F.regex(r"^\d+$")))
async def numbers_only(ctx):
    pass

# Caption regex (for media)
@client.on(Message(F.caption_regex(r"#\w+")))
async def hashtag_media(ctx):
    pass
```

### Custom Filters

```python
# Custom filter function
def is_admin(message):
    admin_ids = [123, 456, 789]
    return message.from_user.id in admin_ids

@client.on(Message(F.custom(is_admin)))
async def admin_only(ctx):
    pass
```

### Filter Composition

Combine filters using logical operators:

```python
# AND operator (&)
@client.on(Message(F.text & F.private))
async def private_text(ctx):
    pass

# OR operator (|)
@client.on(Message(F.photo | F.video))
async def media_handler(ctx):
    pass

# NOT operator (~)
@client.on(Message(F.text & ~F.forwarded))
async def original_text(ctx):
    pass

# Complex combinations
@client.on(Message((F.photo | F.video) & F.caption & F.private))
async def private_media_with_caption(ctx):
    pass
```

---

## Context Object

The context object (`ctx`) provides access to update data and helper methods.

### Accessing Update Data

```python
@client.on(Message())
async def handler(ctx):
    # Message data
    text = ctx.text              # Message text
    caption = ctx.caption        # Media caption

    # User information
    user = ctx.user              # User object
    user_id = ctx.user.id
    first_name = ctx.user.first_name
    username = ctx.user.username

    # Chat information
    chat = ctx.chat              # Chat object
    chat_id = ctx.chat.id
    chat_type = ctx.chat.type    # 'private', 'group', 'supergroup'

    # Command arguments
    args = ctx.args              # List of arguments

    # Regex match
    if ctx.match:
        matched_text = ctx.match.group(0)
        captured_group = ctx.match.group(1)
```

### Reply Methods

```python
@client.on(Message())
async def handler(ctx):
    # Send text message
    await ctx.reply("Hello!")

    # With formatting
    await ctx.reply(
        "<b>Bold</b> <i>Italic</i> <code>Code</code>",
        parse_mode="HTML"
    )

    # With reply markup
    await ctx.reply(
        "Choose an option:",
        reply_markup={
            "inline_keyboard": [[
                {"text": "Button 1", "callback_data": "btn_1"},
                {"text": "Button 2", "callback_data": "btn_2"}
            ]]
        }
    )
```

### Edit and Delete

```python
@client.on(CallbackQuery())
async def callback_handler(ctx):
    # Edit message text
    await ctx.edit("Updated text!")

    # Edit with new markup
    await ctx.edit(
        "New text",
        reply_markup={"inline_keyboard": [[...]]}
    )

    # Delete message
    await ctx.delete()
```

### Send Media

```python
@client.on(Message(F.command("photo")))
async def send_photo_handler(ctx):
    # Send photo by file_id
    await ctx.send_photo(
        photo="AgACAgIAAxkBAAI...",
        caption="Photo caption"
    )

    # Send video
    await ctx.send_video(
        video="BAACAgIAAxkBAAI...",
        caption="Video caption"
    )

    # Send document
    await ctx.send_document(
        document="BQACAgIAAxkBAAI...",
        caption="Document caption"
    )
```

### User Data (with UserDataMiddleware)

```python
@client.on(Message(F.command("save")))
async def save_data(ctx):
    # Set user data
    await ctx.user_data.set("name", "John")
    await ctx.user_data.set("age", 25)

    # Get user data
    name = await ctx.user_data.get("name")
    age = await ctx.user_data.get("age", default=0)

    # Delete user data
    await ctx.user_data.delete("age")

    # Clear all user data
    await ctx.user_data.clear()
```

### State Management (FSM)

```python
@client.on(Message(F.command("register")))
async def start_registration(ctx):
    await ctx.set_state("awaiting_name")
    await ctx.reply("What's your name?")

@client.on(Message(F.text))
async def process_input(ctx):
    state = await ctx.get_state()

    if state == "awaiting_name":
        await ctx.update_data(name=ctx.text)
        await ctx.set_state("awaiting_age")
        await ctx.reply("How old are you?")

    elif state == "awaiting_age":
        await ctx.update_data(age=ctx.text)
        name = await ctx.get_data("name")
        age = await ctx.get_data("age")
        await ctx.clear_state()
        await ctx.reply(f"Registered! Name: {name}, Age: {age}")
```

---

## Middleware

Middleware intercepts updates before they reach handlers.

### Built-in Middleware

#### Logger Middleware

```python
from swiftbot.middleware import Logger

client.use(Logger(
    level="INFO",                # DEBUG, INFO, WARNING, ERROR
    format="text",               # text, json, colored
    include_updates=True,        # Log incoming updates
    include_responses=False,     # Log outgoing responses
))
```

#### Rate Limiter Middleware

```python
from swiftbot.middleware import RateLimiter
import redis

redis_conn = redis.Redis(host='localhost', port=6379, db=0)

client.use(RateLimiter(
    rate=10,                     # Max requests
    per=60,                      # Per seconds
    strategy="sliding_window",   # fixed_window, sliding_window, token_bucket
    storage=redis_conn,          # Redis connection
    key_func=lambda ctx: f"user:{ctx.user.id}",
    on_exceeded=lambda ctx: ctx.reply("Too many requests!")
))
```

#### Auth Middleware

```python
from swiftbot.middleware import Auth

ADMIN_IDS = [123456789]
BANNED_IDS = [999888777]

client.use(Auth(
    whitelist=None,              # None = allow all
    blacklist=BANNED_IDS,
    admin_list=ADMIN_IDS,
    check_func=lambda ctx: ctx.user.id not in banned_users,
    on_unauthorized=lambda ctx: ctx.reply("Access denied")
))
```

#### User Data Middleware

```python
from swiftbot.middleware import UserDataMiddleware
from swiftbot.storage import RedisStore
import redis

redis_conn = redis.Redis()
storage = RedisStore(connection=redis_conn)

client.use(UserDataMiddleware(
    storage=storage,
    auto_create=True,
    cache_ttl=300
))
```

### Custom Middleware

Create custom middleware by extending the Middleware class:

```python
from swiftbot.middleware import Middleware

class CustomMiddleware(Middleware):
    async def on_update(self, ctx, next_handler):
        # Pre-processing
        print(f"Before: {ctx.user.id}")

        # Call next middleware or handler
        await next_handler()

        # Post-processing
        print(f"After: {ctx.user.id}")

    async def on_error(self, ctx, error):
        # Error handling
        print(f"Error: {error}")

# Register middleware
client.use(CustomMiddleware())
```

---

## Storage Backends

SwiftBot supports multiple storage backends for user data persistence.

### Redis Storage (Recommended)

```python
from swiftbot.storage import RedisStore
import redis

# Create Redis connection
redis_conn = redis.Redis(
    host='localhost',
    port=6379,
    db=0,
    decode_responses=False  # Important: keep False
)

# Create storage adapter
storage = RedisStore(
    connection=redis_conn,
    prefix="swiftbot"  # Key prefix
)

# Use with middleware
from swiftbot.middleware import UserDataMiddleware
client.use(UserDataMiddleware(storage=storage))
```

### File Storage

```python
from swiftbot.storage import FileStore

# Create file storage
storage = FileStore(base_path="./data")

# Use with middleware
client.use(UserDataMiddleware(storage=storage))
```

### Custom Storage Adapter

Implement the StorageAdapter interface:

```python
from swiftbot.storage import StorageAdapter

class MyStorage(StorageAdapter):
    async def get(self, user_id: int, key: str):
        # Implement retrieval logic
        pass

    async def set(self, user_id: int, key: str, value, ttl=None):
        # Implement storage logic
        pass

    async def delete(self, user_id: int, key: str):
        # Implement deletion logic
        pass

    async def get_all(self, user_id: int):
        # Return all user data
        pass

    async def clear(self, user_id: int):
        # Clear all user data
        pass
```

---

## Broadcasting

Send messages to multiple users efficiently.

### Setup Broadcaster

```python
from swiftbot.broadcast import Broadcaster

broadcaster = Broadcaster(
    bot=client,
    storage=storage,        # Storage with user list
    workers=20,             # Concurrent workers
    rate_limit=30,          # Messages per second
    retry_failed=True,
    retry_attempts=3
)
```

### Broadcast Methods

```python
# Broadcast to all users
await broadcaster.send_to_all(
    text="Announcement!",
    filters=lambda user: user.data.get("subscribed", False)
)

# Broadcast to specific users
user_ids = [123, 456, 789, 1011]
await broadcaster.send_to_users(
    user_ids=user_ids,
    text="Targeted message",
    parse_mode="HTML"
)

# Broadcast with progress tracking
async for progress in broadcaster.send_with_progress(
    text="Broadcasting...",
    users=user_ids
):
    print(f"Sent: {progress.sent}/{progress.total}")
    print(f"Failed: {progress.failed}")
    print(f"Success rate: {progress.success_rate:.2%}")

# Broadcast with callbacks
async def on_success(user_id, message):
    print(f"Sent to {user_id}")

async def on_error(user_id, error):
    print(f"Failed for {user_id}: {error}")

await broadcaster.send_to_users(
    user_ids=user_ids,
    text="Message",
    on_success=on_success,
    on_error=on_error
)
```

---

## Advanced Features

### Handler Priority

Control handler execution order:

```python
# Higher priority = executed first
@client.on(Message(F.text), priority=10)
async def high_priority(ctx):
    pass

@client.on(Message(F.text), priority=0)
async def normal_priority(ctx):
    pass
```

### Bot Statistics

Get bot performance metrics:

```python
stats = client.get_stats()

print(f"Running: {stats['running']}")
print(f"Workers: {stats['worker_pool']['num_workers']}")
print(f"Processed: {stats['worker_pool']['processed']}")
print(f"Failed: {stats['worker_pool']['failed']}")
print(f"Handlers: {stats['router']}")
```

### Error Handling

Handle errors in middleware:

```python
class ErrorHandler(Middleware):
    async def on_error(self, ctx, error):
        # Log error
        print(f"Error: {error}")

        # Notify user
        await ctx.reply("An error occurred. Please try again.")

        # Notify admin
        await client.api.send_message(
            chat_id=ADMIN_ID,
            text=f"Error: {error}
User: {ctx.user.id}"
        )

client.use(ErrorHandler())
```

---

## Best Practices

### 1. Use Environment Variables

```python
import os
from dotenv import load_dotenv

load_dotenv()

client = SwiftBot(token=os.getenv("BOT_TOKEN"))
```

### 2. Proper Error Handling

```python
@client.on(Message(F.command("risky")))
async def risky_operation(ctx):
    try:
        result = perform_risky_operation()
        await ctx.reply(f"Success: {result}")
    except Exception as e:
        await ctx.reply("Operation failed. Please try again.")
        # Log error for debugging
        print(f"Error in risky_operation: {e}")
```

### 3. Use Redis for Production

```python
# Redis is faster and supports multiple bot instances
storage = RedisStore(connection=redis_conn)
```

### 4. Rate Limiting

```python
# Always use rate limiting in production
client.use(RateLimiter(rate=10, per=60, storage=redis_conn))
```

### 5. Graceful Shutdown

```python
import signal

def signal_handler(sig, frame):
    print("Stopping bot...")
    client.stop()

signal.signal(signal.SIGINT, signal_handler)
signal.signal(signal.SIGTERM, signal_handler)
```

---

## Troubleshooting

### Common Issues

**1. Bot not responding**
- Check if bot token is correct
- Verify bot is running: `await client.run()`
- Check handler patterns match your messages

**2. Rate limit errors**
- Implement rate limiting middleware
- Reduce broadcast speed
- Use connection pooling

**3. Memory issues**
- Reduce worker_pool_size
- Implement proper cleanup in handlers
- Use Redis instead of file storage

**4. Slow performance**
- Enable HTTP/2: `enable_http2=True`
- Increase worker pool: `worker_pool_size=50`
- Use connection pooling

**5. Import errors**
- Install required dependencies: `pip install swiftbot[redis]`
- Check Python version: Python 3.10+

### Debug Mode

Enable debug logging:

```python
from swiftbot.middleware import Logger

client.use(Logger(
    level="DEBUG",
    format="text",
    include_updates=True,
    include_responses=True
))
```

---

## Additional Resources

- **GitHub Repository**: [https://github.com/Arjun-M/SwiftBot](https://github.com/Arjun-M/SwiftBot)
- **Examples**: See `example_basic.py` and `example_advanced.py`
- **API Reference**: Check inline documentation in source code

---

**Copyright (c) 2025 Arjun-M/SwiftBot**  
**License: MIT**
