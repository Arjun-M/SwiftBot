# Edge Cases & Advanced Troubleshooting

Common edge cases, gotchas, and how to handle them.

## Table of Contents

1. [Message Handling Edge Cases](#message-handling-edge-cases)
2. [Filter Edge Cases](#filter-edge-cases)
3. [Callback Query Issues](#callback-query-issues)
4. [Performance Issues](#performance-issues)
5. [Error Handling](#error-handling)
6. [Telegram Limits](#telegram-limits)
7. [FAQ](#faq)

---

## Message Handling Edge Cases

### Empty or Null Messages

```python
# ✗ Bad: Will crash if message has no text
@client.on(Message(F.text))
async def handler(ctx):
    words = ctx.text.split()  # Crashes if text is None

# ✓ Good: Check for None
@client.on(Message(F.text))
async def handler(ctx):
    if not ctx.text:
        return
    words = ctx.text.split()
```

### Unicode and Special Characters

```python
# Handle emoji and special characters
@client.on(Message(F.text))
async def emoji_handler(ctx):
    # Python 3 handles unicode natively
    if "🔥" in ctx.text:
        await ctx.reply("Fire emoji detected!")
    
    # Proper length counting with emoji
    actual_length = len(ctx.text.encode('utf-8'))
    await ctx.reply(f"Length: {actual_length} bytes")
```

### Very Long Messages

```python
# Telegram max message length is 4096 characters
@client.on(Message(F.text))
async def long_message_handler(ctx):
    if len(ctx.text) > 4096:
        # Split into chunks
        for i in range(0, len(ctx.text), 4096):
            await ctx.reply(ctx.text[i:i+4096])
    else:
        await ctx.reply(ctx.text)
```

### Edited Messages

```python
# EditedMessage is a separate event type
@client.on(EditedMessage(F.text))
async def on_edit(ctx):
    await ctx.reply(f"Message edited! New text: {ctx.text}")
```

### Media with Caption

```python
@client.on(Message(F.photo))
async def photo_handler(ctx):
    # Caption might be None
    caption = ctx.caption or "No caption"
    
    # Photo contains list of PhotoSize objects
    photo = ctx.message.photo[-1]  # Get highest quality
    file_id = photo.file_id
    
    await ctx.reply(f"Photo: {file_id}, Caption: {caption}")
```

---

## Filter Edge Cases

### Regex Matching Edge Cases

```python
import re

# ✗ Bad: Regex doesn't escape special characters
pattern = "/start+path"  # Means "start" repeated 1+ times

# ✓ Good: Escape special characters
pattern = re.escape("/start+path")

# Edge case: Empty match
@client.on(Message(F.regex(r"a*")))  # Matches everything (0+ a's)
async def handler(ctx):
    pass

# ✓ Better: Use anchors and require at least one char
@client.on(Message(F.regex(r"^a+$")))  # Only "aaa", "aaaa", etc.
async def handler(ctx):
    pass
```

### Filter Composition Order

```python
# ✗ Bad: Expensive check first
@client.on(Message(F.custom(db_lookup) & F.text))
async def bad_order(ctx):
    pass

# ✓ Good: Cheap checks first
@client.on(Message(F.text & F.custom(db_lookup)))
async def good_order(ctx):
    pass
```

### NOT Filter with Complex Conditions

```python
# ✓ Proper negation of compound condition
# NOT (text AND command)
@client.on(Message(~(F.text & F.regex(r"^/"))))
async def not_command(ctx):
    # True if: not text OR not a command
    pass

# ✗ Easy to get wrong
@client.on(Message(~F.text & ~F.regex(r"^/")))
async def wrong_negation(ctx):
    # This is: (not text) AND (not command) - Different meaning!
    pass
```

### Empty Filter Groups

```python
# Edge case: Empty filters
F.all()  # Always True
F.any()  # Always False

# This works but might not be intended
@client.on(Message(F.all() & F.text))  # Same as F.text
async def handler(ctx):
    pass
```

---

## Callback Query Issues

### Callback Data Size Limit

```python
# Telegram limit: callback_data max 64 bytes
import json

# ✗ Bad: Too large
callback_data = json.dumps({"user_dict": user_dict})  # Way over 64 bytes

# ✓ Good: Use ID reference
cache = {}
cache_id = str(uuid.uuid4())[:8]  # Keep it short
cache[cache_id] = user_dict

button = Button.inline("Click", cache_id)
```

### Callback Query Timeout

```python
# Callback queries must be answered within 30 seconds
@client.on(CallbackQuery())
async def callback(ctx):
    try:
        # Long operation
        result = await long_operation()
    except asyncio.TimeoutError:
        # Still answer the callback
        await ctx.answer_callback("Timeout!")
        await ctx.edit("Operation timed out")
```

### Multiple Callback Edits

```python
# ✗ Bad: Race condition - multiple edits at once
async def multi_edit(ctx):
    await ctx.edit("1")
    await ctx.edit("2")  # Might fail if first hasn't finished

# ✓ Good: Wait between edits
async def safe_edit(ctx):
    await ctx.edit("1")
    await asyncio.sleep(0.1)
    await ctx.edit("2")
```

### Editing Deleted Messages

```python
# Error if message was deleted
@client.on(CallbackQuery())
async def callback(ctx):
    try:
        await ctx.edit("New text")
    except Exception as e:
        if "message not modified" in str(e):
            # Message might have been deleted
            await ctx.answer_callback("Message expired")
        else:
            raise
```

---

## Performance Issues

### Rate Limiting

```python
# Telegram has rate limits
from collections import defaultdict
import time

request_times = defaultdict(list)
MAX_REQUESTS = 30
WINDOW = 1  # Second

class RateLimitMiddleware:
    async def on_update(self, ctx, next_handler):
        user_id = ctx.user.id
        now = time.time()
        
        # Keep only recent requests
        request_times[user_id] = [
            t for t in request_times[user_id]
            if now - t < WINDOW
        ]
        
        if len(request_times[user_id]) >= MAX_REQUESTS:
            await ctx.reply("Rate limited!")
            return
        
        request_times[user_id].append(now)
        await next_handler()
```

### Large Message Batches

```python
# ✗ Bad: Send all at once, might get rate limited
for user_id in users:
    await client.send_message(user_id, "Message")

# ✓ Good: Send concurrently with semaphore
import asyncio

async def batch_send(user_ids, message):
    semaphore = asyncio.Semaphore(10)  # Max 10 concurrent
    
    async def send_with_limit(uid):
        async with semaphore:
            await client.send_message(uid, message)
    
    await asyncio.gather(*[send_with_limit(uid) for uid in user_ids])
```

### Memory Leaks

```python
# ✗ Bad: Growing dictionary
user_cache = {}

@client.on(Message())
async def handler(ctx):
    user_cache[ctx.user.id] = ctx.message  # Never deleted!

# ✓ Good: Bounded cache
from functools import lru_cache

@lru_cache(maxsize=1000)
def get_user_cache(user_id):
    return {}

# Or use explicit cache with TTL
import time
user_cache = {}
CACHE_TTL = 3600

async def cleanup_cache():
    while True:
        now = time.time()
        expired = [uid for uid, (data, ts) in user_cache.items() if now - ts > CACHE_TTL]
        for uid in expired:
            del user_cache[uid]
        await asyncio.sleep(CACHE_TTL)
```

---

## Error Handling

### Network Errors

```python
@client.on(Message())
async def handler(ctx):
    try:
        result = await client.send_message(ctx.chat.id, "Message")
    except ConnectionError:
        print("Network error - will retry")
    except Exception as e:
        print(f"Error: {e}")
```

### Invalid Commands

```python
# Handle command with missing args
@client.on(Message(F.command("search")))
async def search(ctx):
    if not ctx.args:
        await ctx.reply("Usage: /search <query>")
        return
    
    query = " ".join(ctx.args)
    # Search...
```

### Graceful Shutdown

```python
import signal

async def main():
    try:
        await client.run_polling()
    except KeyboardInterrupt:
        print("Shutting down...")
        # Cleanup
        client.stop()

# Handle signals
loop = asyncio.get_event_loop()
loop.add_signal_handler(signal.SIGINT, lambda: client.stop())
```

---

## Telegram Limits

| Limit | Value |
|-------|-------|
| Message text | 4,096 characters |
| Caption | 1,024 characters |
| Callback data | 64 bytes |
| Callback answer timeout | 30 seconds |
| Inline keyboard buttons per row | 8 |
| Inline buttons per message | Unlimited |
| Reply keyboard buttons | 100 |
| Command parameter | Various (e.g., file 50MB) |

### Handling File Size Limits

```python
# File upload limits vary by type:
# Photo: 5 MB
# Video: 50 MB
# Audio: 50 MB
# Document: 50 MB

MAX_FILE_SIZE = 50 * 1024 * 1024

@client.on(Message(F.document))
async def file_handler(ctx):
    doc = ctx.message.document
    
    if doc.file_size > MAX_FILE_SIZE:
        await ctx.reply(f"❌ File too large (max {MAX_FILE_SIZE / 1024 / 1024}MB)")
        return
    
    # Process file
```

---

## FAQ

### Q: How do I prevent command case sensitivity issues?

**A:** Filters handle this automatically:

```python
@client.on(Message(F.command("help")))
async def help_cmd(ctx):
    # Matches /help, /HELP, /Help, etc.
    pass
```

### Q: How do I reply to specific messages?

**A:**

```python
@client.on(Message())
async def handler(ctx):
    # Reply to message
    await client.send_message(
        ctx.chat.id,
        "Reply",
        reply_to_message_id=ctx.message.message_id
    )
```

### Q: Can I edit bot's own messages?

**A:** Yes, keep track of message IDs:

```python
@client.on(Message(F.command("test")))
async def test_cmd(ctx):
    msg = await ctx.reply("Original")
    await asyncio.sleep(2)
    await client.edit_message_text(
        "Updated",
        chat_id=ctx.chat.id,
        message_id=msg['message_id']
    )
```

### Q: How do I handle multiple languages?

**A:** See `real-world-usage.md` for full example.

### Q: How do I implement admin commands?

**A:**

```python
ADMINS = [123456789]

@client.on(Message(F.command("ban")))
async def ban_cmd(ctx):
    if ctx.user.id not in ADMINS:
        await ctx.reply("❌ Admin only")
        return
    
    # Ban logic
```

### Q: Can I schedule tasks?

**A:**

```python
import asyncio

async def daily_task():
    while True:
        # Run every 24 hours
        await asyncio.sleep(86400)
        # Do something
        print("Daily task ran")

async def main():
    asyncio.create_task(daily_task())
    await client.run_polling()

asyncio.run(main())
```

---

**See `USAGE.md` for complete API reference.**
