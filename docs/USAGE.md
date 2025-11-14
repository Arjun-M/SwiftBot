# SwiftBot - Complete Usage Guide

SwiftBot is an ultra-fast Telegram bot framework with Telethon-inspired syntax, 30× faster routing via Trie data structure, and enterprise-grade features including middleware, filters, and HTTP/2 connection pooling.

## Table of Contents

1. [Installation & Setup](#installation--setup)
2. [Quick Start](#quick-start)
3. [Core Concepts](#core-concepts)
4. [Messages & Handlers](#messages--handlers)
5. [Filters System](#filters-system)
6. [Buttons & Keyboards](#buttons--keyboards)
7. [Context Object](#context-object)
8. [Advanced Features](#advanced-features)
9. [Error Handling](#error-handling)
10. [Performance Tips](#performance-tips)

---

## Installation & Setup

### Install from PyPI

```bash
pip install swiftbot
```

### Basic Initialization

```python
from swiftbot import SwiftBot, Message, Filters

# Create bot instance with configuration
client = SwiftBot(
    token="YOUR_BOT_TOKEN",           # Required: from @BotFather
    parse_mode="HTML",                # Default parse mode for all messages
    worker_pool_size=50,              # Concurrent message processors
    max_connections=100,              # HTTP connection pool size
    timeout=30.0,                     # Request timeout
    enable_http2=True,                # Enable HTTP/2 for speed
    debug=False                       # Debug mode
)
```

### Environment Variables

```python
import os
from dotenv import load_dotenv

load_dotenv()
token = os.getenv("BOT_TOKEN")
client = SwiftBot(token=token)
```

---

## Quick Start

### Minimal Echo Bot

```python
from swiftbot import SwiftBot, Message, Filters as F

client = SwiftBot(token="YOUR_TOKEN")

@client.on(Message(F.text))
async def echo_handler(ctx):
    await ctx.reply(f"You said: {ctx.text}")

# Start bot
if __name__ == "__main__":
    import asyncio
    asyncio.run(client.run_polling())
```

### Start Command

```python
@client.on(Message(F.command("start")))
async def start(ctx):
    await ctx.reply("Welcome! 👋")
```

### Running the Bot

**Polling Mode (Recommended for Development):**
```python
await client.run_polling(
    timeout=30,
    limit=100,
    drop_pending_updates=True
)
```

**Webhook Mode (Production):**
```python
await client.run_webhook(
    host="0.0.0.0",
    port=8443,
    webhook_url="https://your-domain.com/webhook",
    cert_path="/path/to/cert.pem",
    key_path="/path/to/key.pem"
)
```

---

## Core Concepts

### Event Types

SwiftBot provides event types for different Telegram updates:

| Event Type | Triggered By |
|-----------|-------------|
| `Message` | Text/media messages |
| `CallbackQuery` | Inline button clicks |
| `InlineQuery` | Inline mode searches |
| `EditedMessage` | Message edits |
| `ChatMemberUpdated` | User joins/leaves |

```python
# Message handler
@client.on(Message())
async def any_message(ctx):
    pass

# Callback query handler
@client.on(CallbackQuery())
async def callback(ctx):
    await ctx.answer_callback("Button clicked!")

# Inline query handler
@client.on(InlineQuery())
async def inline(ctx):
    await client.answer_inline_query(ctx.inline_query.id, results=[])
```

---

## Messages & Handlers

### Text Messages

```python
# Exact text match
@client.on(Message(text="hello"))
async def hello_handler(ctx):
    await ctx.reply("Hello there!")

# Pattern match (regex)
@client.on(Message(pattern=r"^/start"))
async def start(ctx):
    await ctx.reply("Command matched!")

# Multiple patterns
@client.on(Message(pattern=[r"^hi", r"^hey", r"^hello"]))
async def greet(ctx):
    await ctx.reply("Hi there!")

# Custom function filter
@client.on(Message(func=lambda msg: len(msg.text or "") > 100))
async def long_message(ctx):
    await ctx.reply("That's a long message!")
```

### Media Messages

```python
# Photo message
@client.on(Message(F.photo))
async def photo_handler(ctx):
    photo = ctx.message.photo[-1]  # Get highest quality
    await ctx.reply(f"Got photo: {photo.file_id}")

# Video message
@client.on(Message(F.video))
async def video_handler(ctx):
    await ctx.reply("Video received!")

# Any media
@client.on(Message(F.media))
async def any_media(ctx):
    await ctx.reply("Media received!")
```

### Commands

```python
# Single command
@client.on(Message(F.command("start")))
async def start(ctx):
    await ctx.reply("Started!")

# Multiple commands
@client.on(Message(F.command(["help", "info", "about"])))
async def help_cmd(ctx):
    await ctx.reply("Help information")

# Commands with arguments
@client.on(Message(F.command("search")))
async def search(ctx):
    if ctx.args:
        query = " ".join(ctx.args)  # Join all arguments
        await ctx.reply(f"Searching for: {query}")
    else:
        await ctx.reply("Usage: /search <query>")
```

### Message Handler Priority

```python
# Higher priority handlers execute first
@client.on(Message(F.text), priority=10)
async def important_handler(ctx):
    pass

@client.on(Message(F.text), priority=5)
async def less_important(ctx):
    pass
```

---

## Filters System

### Basic Filters

```python
from swiftbot import Filters as F

# Chat type filters
F.private      # Private chat
F.group        # Group chat
F.channel      # Channel

# Message type filters
F.text         # Has text
F.photo        # Photo message
F.video        # Video message
F.audio        # Audio file
F.document     # Document file
F.voice        # Voice message
F.sticker      # Sticker
F.location     # Location
F.contact      # Contact
F.media        # Any media

# Forward/reply filters
F.forwarded    # Forwarded message
F.reply        # Reply to message
```

### Filter Composition

```python
# AND - both conditions must be true
@client.on(Message(F.text & F.private))
async def private_text(ctx):
    pass

# OR - at least one condition must be true
@client.on(Message(F.photo | F.video))
async def photo_or_video(ctx):
    pass

# NOT - negate condition
@client.on(Message(~F.forwarded))
async def not_forwarded(ctx):
    pass

# Complex combinations
@client.on(Message((F.text & F.private) | (F.photo & F.group)))
async def complex(ctx):
    pass
```

### Advanced Filters

```python
# Command filter
F.command("start")
F.command(["help", "info"])

# Regex filter
F.regex(r"^/\w+")
F.regex(r"\d+", flags=re.IGNORECASE)

# Caption regex (for media)
F.caption_regex(r"^important")

# User filter
F.user(123456789)
F.user([123456789, 987654321])

# Chat filter
F.chat(-1001234567890)
F.chat([-1001234567890, -1009876543210])

# Custom filter
def my_filter(message):
    return len(message.text or "") > 50

F.custom(my_filter, name="LongMessageFilter")
```

### Filter Helper Methods

```python
# Match all conditions (AND)
@client.on(Message(F.all(F.text, F.private, F.regex(r"^hello"))))
async def all_conditions(ctx):
    pass

# Match any condition (OR)
@client.on(Message(F.any(F.photo, F.video, F.document)))
async def any_media_type(ctx):
    pass
```

---

## Buttons & Keyboards

### Inline Buttons

Inline buttons appear above the message input field and trigger callbacks.

```python
from swiftbot import Button, InlineKeyboard

# Create inline button
button = Button.inline("Click me", "callback_data")

# Create keyboard with multiple buttons
keyboard = InlineKeyboard(buttons=[[button]])
keyboard.add_row(
    Button.inline("Button 1", "btn_1"),
    Button.inline("Button 2", "btn_2")
)

# Send message with keyboard
await ctx.reply(
    "Choose an option:",
    reply_markup=keyboard.to_dict()
)

# Handle callback
@client.on(CallbackQuery(pattern="callback_data"))
async def handle_callback(ctx):
    await ctx.answer_callback("Button clicked!")
    await ctx.edit("Updated message")
```

### Button Types

```python
# Standard inline button
Button.inline("Text", "data")

# URL button
Button.url("Open Google", "https://google.com")

# Web App button
Button.web_app("Open App", "https://your-app.com")

# Switch inline button (inline mode)
Button.switch_inline("Search", "query text")
Button.switch_inline("Same Chat", "query", same_peer=True)

# Payment button
Button.pay("Pay $10")

# User/Chat request buttons
Button.request_user("Select User", request_id=1)
Button.request_chat("Select Chat", request_id=2)

# Copy text button
Button.copy_text("Copy", "text to copy")

# Login button
Button.login("Login", "https://your-site.com/login")
```

### Reply Buttons

Reply buttons appear as keyboard layout below the message.

```python
from swiftbot import Button, ReplyKeyboard

# Create reply button
button = Button.text("Click me")

# Create keyboard
keyboard = ReplyKeyboard(buttons=[[button]])
keyboard.add_row(Button.text("Option 1"), Button.text("Option 2"))

# Request buttons
keyboard.add_row(Button.contact("Share Contact"))
keyboard.add_row(Button.location("Share Location"))
keyboard.add_row(Button.poll("Create Poll"))

# Send message with keyboard
await ctx.reply(
    "Choose an option:",
    reply_markup=keyboard.to_dict()
)
```

### Button Examples

```python
# Pagination buttons
async def show_page(ctx, page=1):
    prev_btn = Button.inline("< Previous", f"page_{page-1}")
    next_btn = Button.inline("Next >", f"page_{page+1}")
    
    keyboard = InlineKeyboard(buttons=[[prev_btn, next_btn]])
    await ctx.reply(f"Page {page}", reply_markup=keyboard.to_dict())

# Main menu
async def main_menu(ctx):
    keyboard = InlineKeyboard(buttons=[
        [Button.inline("📊 Stats", "stats")],
        [Button.inline("⚙️ Settings", "settings")],
        [Button.inline("❓ Help", "help")]
    ])
    await ctx.reply("Main Menu:", reply_markup=keyboard.to_dict())

# Dynamic buttons from data
items = ["Item 1", "Item 2", "Item 3"]
keyboard = InlineKeyboard(buttons=[
    [Button.inline(item, f"select_{i}")] 
    for i, item in enumerate(items)
])
```

---

## Context Object

The `Context` object (ctx) provides access to update data and helper methods.

### Message Data

```python
@client.on(Message())
async def handler(ctx):
    # Message info
    ctx.message.message_id
    ctx.message.date
    ctx.message.text
    ctx.message.caption
    
    # User info
    ctx.user.id
    ctx.user.first_name
    ctx.user.last_name
    ctx.user.username
    ctx.user.is_bot
    
    # Chat info
    ctx.chat.id
    ctx.chat.type  # 'private', 'group', 'supergroup', 'channel'
    ctx.chat.title
    ctx.chat.username
    
    # Command args
    @client.on(Message(F.command("search")))
    async def search(ctx):
        ctx.args  # List of arguments: ["/search", "term"] → ctx.args = ["term"]
        
    # Regex match
    @client.on(Message(pattern=r"(\d+)"))
    async def numbers(ctx):
        ctx.match.group(1)  # Access regex groups
```

### Sending Messages

```python
# Simple reply
await ctx.reply("Hello!")

# With HTML formatting
await ctx.reply("<b>Bold</b> <i>italic</i>", parse_mode="HTML")

# With Markdown
await ctx.reply("**bold** *italic*", parse_mode="Markdown")

# With keyboard
await ctx.reply("Choose:", reply_markup=keyboard.to_dict())

# Edit message
await ctx.edit("Updated text")

# Delete message
await ctx.delete()

# Forward message
await ctx.forward_to(target_chat_id)
```

### Sending Media

```python
# Photo
await ctx.send_photo(photo_file_id, caption="Photo caption")

# Video
await ctx.send_video(video_file_id, caption="Video caption", duration=60)

# Audio
await ctx.send_audio(audio_file_id, title="Song", performer="Artist")

# Document
await ctx.send_document(document_file_id, caption="Document")

# Voice
await ctx.send_voice(voice_file_id, caption="Voice message")

# Animation (GIF)
await ctx.send_animation(animation_file_id, caption="GIF")

# Sticker
await ctx.send_sticker(sticker_file_id)

# Poll
await ctx.send_poll(
    question="What's your favorite?",
    options=["Option 1", "Option 2", "Option 3"]
)

# Location
await ctx.send_location(latitude=40.7128, longitude=-74.0060)
```

### Callback Queries

```python
@client.on(CallbackQuery())
async def handle_callback(ctx):
    # Callback data
    ctx.data  # Callback data string
    
    # Original message
    ctx.message.text
    ctx.message.reply_markup
    
    # Answer callback
    await ctx.answer_callback("Notification text")
    await ctx.answer_callback("Alert!", show_alert=True)  # Shows alert
    
    # Edit original message
    await ctx.edit("Updated message")
    
    # Replace keyboard
    new_keyboard = InlineKeyboard(...)
    await ctx.edit(
        "New message",
        reply_markup=new_keyboard.to_dict()
    )
```

---

## Advanced Features

### Middleware

Middleware processes all updates before reaching handlers:

```python
class LoggingMiddleware:
    async def on_update(self, ctx, next_handler):
        print(f"User: {ctx.user.id}, Message: {ctx.text}")
        await next_handler()

class RateLimitMiddleware:
    def __init__(self):
        self.user_requests = {}
    
    async def on_update(self, ctx, next_handler):
        user_id = ctx.user.id
        import time
        now = time.time()
        
        if user_id not in self.user_requests:
            self.user_requests[user_id] = []
        
        # Keep last 10 seconds
        self.user_requests[user_id] = [
            t for t in self.user_requests[user_id] 
            if now - t < 10
        ]
        
        if len(self.user_requests[user_id]) > 5:
            await ctx.reply("Rate limited! Please wait.")
            return
        
        self.user_requests[user_id].append(now)
        await next_handler()

# Register middleware
client.use(LoggingMiddleware())
client.use(RateLimitMiddleware())
```

### State Management (FSM)

Finite State Machine for multi-step conversations:

```python
class States:
    WAITING_NAME = "waiting_name"
    WAITING_AGE = "waiting_age"
    CONFIRMING = "confirming"

@client.on(Message(F.command("register")))
async def start_register(ctx):
    await ctx.set_state(States.WAITING_NAME)
    await ctx.reply("What's your name?")

@client.on(Message(), priority=10)
async def handle_by_state(ctx):
    state = await ctx.get_state()
    
    if state == States.WAITING_NAME:
        await ctx.user_data.set("name", ctx.text)
        await ctx.set_state(States.WAITING_AGE)
        await ctx.reply("What's your age?")
    
    elif state == States.WAITING_AGE:
        await ctx.user_data.set("age", ctx.text)
        await ctx.set_state(States.CONFIRMING)
        
        name = await ctx.user_data.get("name")
        await ctx.reply(f"Confirm: {name}, age {ctx.text}?\nReply /confirm or /cancel")
    
    elif state == States.CONFIRMING:
        if ctx.text.lower() == "/confirm":
            await ctx.reply("✓ Registered!")
            await ctx.clear_state()
        elif ctx.text.lower() == "/cancel":
            await ctx.reply("Cancelled")
            await ctx.clear_state()
```

### Data Persistence

```python
# User-level data
await ctx.user_data.set("key", "value")
value = await ctx.user_data.get("key")
await ctx.user_data.delete("key")

# Chat-level data
await ctx.chat_data.set("key", "value")
value = await ctx.chat_data.get("key")
```

### Statistics & Monitoring

```python
# Get bot statistics
stats = client.get_stats()
print(f"Updates processed: {stats['updates_processed']}")
print(f"Handlers executed: {stats['handlers_executed']}")
print(f"Errors: {stats['errors_handled']}")
print(f"Router info: {stats['router']}")
```

---

## Error Handling

### Exception Handling

```python
@client.on(Message())
async def handler(ctx):
    try:
        # Your code
        await ctx.reply("Processing...")
    except ValueError as e:
        await ctx.reply(f"Invalid input: {e}")
    except Exception as e:
        await ctx.reply("An error occurred")
        print(f"Error: {e}")
```

### Global Error Handler

```python
class ErrorHandlerMiddleware:
    async def on_error(self, ctx, exception):
        print(f"Error: {exception}")
        if ctx:
            await ctx.reply("Sorry, an error occurred. Please try again.")

client.use(ErrorHandlerMiddleware())
```

---

## Performance Tips

### 1. Use Filters Efficiently

```python
# ✓ Good - filter early
@client.on(Message(F.text & F.private))
async def handler(ctx):
    pass

# ✗ Bad - filter inside handler
@client.on(Message())
async def handler(ctx):
    if not ctx.text or ctx.chat.type != 'private':
        return
```

### 2. Connection Pooling

```python
client = SwiftBot(
    token="...",
    max_connections=100,        # Optimal pool size
    enable_http2=True,          # Use HTTP/2
    worker_pool_size=50         # Concurrent workers
)
```

### 3. Avoid Blocking Operations

```python
# ✗ Bad - blocks event loop
import time
time.sleep(5)  # Never do this!

# ✓ Good - use async
import asyncio
await asyncio.sleep(5)
```

### 4. Batch Operations

```python
# ✗ Bad - sends 100 requests sequentially
for user_id in users:
    await client.send_message(user_id, "Hello!")

# ✓ Good - send concurrently
import asyncio
tasks = [client.send_message(uid, "Hello!") for uid in users]
await asyncio.gather(*tasks)
```

### 5. Cache Expensive Operations

```python
from functools import lru_cache

@lru_cache(maxsize=128)
def get_user_config(user_id):
    # Expensive operation
    return config_data

# Telegram API calls are cached automatically
bot_info = await client.get_me(use_cache=True)  # Uses cache after first call
```

---

## Complete Example Bot

```python
import asyncio
from swiftbot import SwiftBot, Message, CallbackQuery, Filters as F, Button, InlineKeyboard

client = SwiftBot(token="YOUR_TOKEN", parse_mode="HTML")

# Middleware for logging
class LogMiddleware:
    async def on_update(self, ctx, next):
        print(f"[{ctx.user.id}] {ctx.text or 'media'}")
        await next()

client.use(LogMiddleware())

# Commands
@client.on(Message(F.command("start")))
async def start(ctx):
    keyboard = InlineKeyboard(buttons=[
        [Button.inline("📊 Stats", "stats")],
        [Button.inline("⚙️ Settings", "settings")]
    ])
    await ctx.reply(
        f"Welcome {ctx.user.first_name}! 👋",
        reply_markup=keyboard.to_dict()
    )

@client.on(Message(F.command("help")))
async def help_cmd(ctx):
    await ctx.reply("""
<b>Available Commands:</b>
/start - Start bot
/help - Show this help
/about - About bot
    """)

# Text handler
@client.on(Message(F.text & F.private))
async def text_handler(ctx):
    await ctx.reply(f"You said: <b>{ctx.text}</b>")

# Callback handlers
@client.on(CallbackQuery(pattern="stats"))
async def stats(ctx):
    await ctx.answer_callback()
    await ctx.edit("<b>📊 Statistics</b>\n\nUsers: 1000\nMessages: 5000")

@client.on(CallbackQuery(pattern="settings"))
async def settings(ctx):
    await ctx.answer_callback()
    await ctx.edit("<b>⚙️ Settings</b>\n\nNotifications: ON")

# Main
if __name__ == "__main__":
    asyncio.run(client.run_polling(drop_pending_updates=True))
```

---

**For more examples, see the `docs/` folder in the repository.**
