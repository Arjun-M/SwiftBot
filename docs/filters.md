# Filters - Complete Reference

The filter system is the core of SwiftBot's routing logic. Filters determine which messages trigger which handlers.

## Table of Contents

1. [Basic Filters](#basic-filters)
2. [Filter Composition](#filter-composition)
3. [Advanced Filters](#advanced-filters)
4. [Custom Filters](#custom-filters)
5. [Real-World Examples](#real-world-examples)
6. [Edge Cases](#edge-cases)
7. [Performance Optimization](#performance-optimization)

---

## Basic Filters

### Chat Type Filters

Identify the type of chat where the message originated.

```python
from swiftbot import Filters as F

# Private chat (Direct message)
@client.on(Message(F.private))
async def private_handler(ctx):
    """Only matches direct messages"""
    pass

# Group chat
@client.on(Message(F.group))
async def group_handler(ctx):
    """Matches messages in groups"""
    pass

# Channel
@client.on(Message(F.channel))
async def channel_handler(ctx):
    """Matches channel messages"""
    pass
```

### Message Content Filters

Match specific message types.

```python
# Text messages
@client.on(Message(F.text))
async def text_handler(ctx):
    pass

# Media filters
@client.on(Message(F.photo))        # Photo message
async def photo(ctx): pass

@client.on(Message(F.video))        # Video message
async def video(ctx): pass

@client.on(Message(F.audio))        # Audio file
async def audio(ctx): pass

@client.on(Message(F.voice))        # Voice message
async def voice(ctx): pass

@client.on(Message(F.document))     # Document/file
async def doc(ctx): pass

@client.on(Message(F.sticker))      # Sticker
async def sticker(ctx): pass

@client.on(Message(F.animation))    # GIF/Animation
async def animation(ctx): pass

@client.on(Message(F.video_note))   # Round video
async def video_note(ctx): pass

# Location and contact
@client.on(Message(F.location))
async def location(ctx): pass

@client.on(Message(F.contact))
async def contact(ctx): pass

# Any media
@client.on(Message(F.media))
async def any_media(ctx):
    """Matches any type of media"""
    pass
```

### Message Status Filters

```python
# Forwarded messages
@client.on(Message(F.forwarded))
async def forwarded(ctx):
    """Message is forwarded from somewhere"""
    pass

# Reply to message
@client.on(Message(F.reply))
async def reply(ctx):
    """Message is a reply to another message"""
    await ctx.reply("You replied to something!")
    pass
```

---

## Filter Composition

Combine multiple filters to create complex logic.

### AND Operator (`&`)

Both conditions must be true.

```python
# Message is text AND in private chat
@client.on(Message(F.text & F.private))
async def private_text(ctx):
    pass

# Photo AND group chat
@client.on(Message(F.photo & F.group))
async def group_photo(ctx):
    pass

# Multiple AND conditions
@client.on(Message(F.text & F.private & F.regex(r"^/start")))
async def private_start_command(ctx):
    pass
```

### OR Operator (`|`)

At least one condition must be true.

```python
# Photo OR video
@client.on(Message(F.photo | F.video))
async def photo_or_video(ctx):
    pass

# Private OR group (any chat)
@client.on(Message(F.private | F.group))
async def any_chat(ctx):
    pass

# Multiple OR conditions
@client.on(Message(F.photo | F.video | F.document))
async def media_files(ctx):
    pass
```

### NOT Operator (`~`)

Negate a condition.

```python
# NOT forwarded (original message)
@client.on(Message(~F.forwarded))
async def original_message(ctx):
    pass

# NOT a reply
@client.on(Message(~F.reply))
async def not_reply(ctx):
    pass

# Text but not command (text without /)
@client.on(Message(F.text & ~F.regex(r"^/")))
async def regular_text(ctx):
    pass
```

### Complex Compositions

```python
# (Photo AND Group) OR (Video AND Private)
@client.on(Message((F.photo & F.group) | (F.video & F.private)))
async def complex(ctx):
    pass

# (Text OR Audio) AND NOT Forwarded
@client.on(Message((F.text | F.audio) & ~F.forwarded))
async def complex2(ctx):
    pass

# Any media that's NOT in channel
@client.on(Message(F.media & ~F.channel))
async def media_except_channel(ctx):
    pass
```

---

## Advanced Filters

### Command Filter

Match command messages like `/start`, `/help`, etc.

```python
# Single command
@client.on(Message(F.command("start")))
async def start(ctx):
    pass

# Multiple commands
@client.on(Message(F.command(["help", "info", "about"])))
async def help_cmd(ctx):
    pass

# Command with arguments
@client.on(Message(F.command("search")))
async def search(ctx):
    if ctx.args:
        query = " ".join(ctx.args)
        await ctx.reply(f"Searching: {query}")
    else:
        await ctx.reply("Usage: /search <query>")
```

**How it works:**
- `/start` matches `/start` command
- `/search hello world` → `ctx.args = ["hello", "world"]`
- `/help@botname` → matches (handles mentions)
- Automatically handles case-insensitivity

### Regex Filter

Match messages using regular expressions.

```python
import re

# Match messages starting with number
@client.on(Message(F.regex(r"^\d+")))
async def numbers_only(ctx):
    pass

# Email address
@client.on(Message(F.regex(r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b")))
async def email_handler(ctx):
    pass

# URL
@client.on(Message(F.regex(r"https?://\S+")))
async def url_handler(ctx):
    pass

# Case-insensitive matching
@client.on(Message(F.regex(r"hello", flags=re.IGNORECASE)))
async def hello_any_case(ctx):
    pass

# Extracting data with groups
@client.on(Message(F.regex(r"(\d+)\s+(\w+)")))
async def extract_data(ctx):
    number = ctx.match.group(1)
    word = ctx.match.group(2)
    await ctx.reply(f"Number: {number}, Word: {word}")
```

### Caption Regex Filter

Match media by caption (photo, video, etc. descriptions).

```python
# Photo with caption containing "important"
@client.on(Message(F.photo & F.caption_regex(r"important")))
async def important_photo(ctx):
    pass

# Document with .pdf extension mentioned
@client.on(Message(F.document & F.caption_regex(r"\.pdf$")))
async def pdf_document(ctx):
    pass
```

### User Filter

Match messages from specific users.

```python
# Single user
ADMIN_ID = 123456789
@client.on(Message(F.user(ADMIN_ID)))
async def admin_only(ctx):
    pass

# Multiple users
ALLOWED_USERS = [123456789, 987654321, 555555555]
@client.on(Message(F.user(ALLOWED_USERS)))
async def whitelist(ctx):
    pass

# Block specific user
@client.on(Message(~F.user(12345)))  # Anyone except this user
async def block_user(ctx):
    pass
```

### Chat Filter

Match messages from specific chats.

```python
# Single chat
GROUP_ID = -1001234567890
@client.on(Message(F.chat(GROUP_ID)))
async def specific_group(ctx):
    pass

# Multiple chats
ALLOWED_GROUPS = [-1001234567890, -1009876543210]
@client.on(Message(F.chat(ALLOWED_GROUPS)))
async def whitelisted_groups(ctx):
    pass
```

### Custom Filter

Create custom filter logic with a function.

```python
# Simple custom filter
def is_long_message(message):
    return len(message.text or "") > 100

@client.on(Message(F.custom(is_long_message, name="LongMessageFilter")))
async def long_message(ctx):
    pass

# Complex custom filter
def is_premium_user(message):
    """Check if user is premium"""
    user_id = message.from_user.id
    # Check your database
    return user_id in PREMIUM_USERS

@client.on(Message(F.custom(is_premium_user)))
async def premium_feature(ctx):
    pass

# Custom filter with lambda
@client.on(Message(F.custom(
    lambda msg: msg.from_user.id % 2 == 0,
    name="EvenUserID"
)))
async def even_user(ctx):
    pass
```

### Filter Helpers

```python
# Match ALL conditions (same as &)
@client.on(Message(F.all(F.text, F.private, F.regex(r"^hello"))))
async def all_match(ctx):
    """Equivalent to: F.text & F.private & F.regex(r"^hello")"""
    pass

# Match ANY condition (same as |)
@client.on(Message(F.any(F.photo, F.video, F.document)))
async def any_match(ctx):
    """Equivalent to: F.photo | F.video | F.document"""
    pass

# Edge case: empty filters
@client.on(Message(F.all()))  # Always True (allow all)
async def allow_all(ctx):
    pass

@client.on(Message(F.any()))  # Always False (deny all)
async def deny_all(ctx):
    pass
```

---

## Custom Filters

### Creating Reusable Filters

```python
# Define custom filter functions
def from_admin(message):
    return message.from_user.id in [123456789, 987654321]

def has_media(message):
    return any([
        message.photo,
        message.video,
        message.document,
        message.audio
    ])

def is_group_or_channel(message):
    return message.chat.type in ("group", "supergroup", "channel")

# Use them
@client.on(Message(F.custom(from_admin)))
async def admin_action(ctx):
    pass

@client.on(Message(F.custom(has_media)))
async def media_handler(ctx):
    pass

@client.on(Message(F.custom(is_group_or_channel)))
async def public_chat(ctx):
    pass
```

### Filter Classes

```python
class Filter:
    def __call__(self, message):
        raise NotImplementedError

class WeekendFilter(Filter):
    def __call__(self, message):
        from datetime import datetime
        day = datetime.now().weekday()
        return day >= 5  # Saturday, Sunday

class TimeRangeFilter(Filter):
    def __init__(self, start_hour, end_hour):
        self.start = start_hour
        self.end = end_hour
    
    def __call__(self, message):
        from datetime import datetime
        hour = datetime.now().hour
        return self.start <= hour < self.end

# Use custom filter class
@client.on(Message(F.custom(WeekendFilter(), "WeekendOnly")))
async def weekend_only(ctx):
    pass

@client.on(Message(F.custom(TimeRangeFilter(9, 17), "WorkHours")))
async def work_hours(ctx):
    pass
```

---

## Real-World Examples

### Content Filtering

```python
# Only allow specific file types
ALLOWED_EXTENSIONS = [".pdf", ".doc", ".docx", ".txt"]

@client.on(Message(F.document & F.caption_regex(
    r"\." + "|\.".join([x.replace(".", "") for x in ALLOWED_EXTENSIONS]) + "$"
)))
async def allowed_document(ctx):
    await ctx.reply("Document accepted!")

@client.on(Message(F.document))
async def any_document(ctx):
    await ctx.reply("File type not allowed!")
```

### Moderating Groups

```python
# Ban spam in groups
import re

def is_spam(message):
    if not message.text:
        return False
    
    spam_patterns = [
        r"https?://\S+bit\.ly",  # Bitly links
        r"(?:click|buy|visit)\s+(?:here|now)",
        r"(?:follow|subscribe)\s+@\w+"
    ]
    
    return any(re.search(p, message.text, re.I) for p in spam_patterns)

@client.on(Message(F.group & F.custom(is_spam)))
async def spam_detected(ctx):
    await ctx.delete()
    await client.restrict_chat_member(
        ctx.chat.id,
        ctx.user.id,
        permissions={}
    )
```

### Permission System

```python
ADMINS = [123456789, 987654321]
MODERATORS = [111111111, 222222222]

@client.on(Message(F.command("ban")))
async def ban_command(ctx):
    if ctx.user.id not in ADMINS:
        await ctx.reply("❌ Admin only")
        return
    
    if not ctx.args:
        await ctx.reply("Usage: /ban <user_id>")
        return
    
    user_id = int(ctx.args[0])
    await client.ban_chat_member(ctx.chat.id, user_id)
    await ctx.reply(f"✓ Banned user {user_id}")
```

---

## Edge Cases

### Handling Multiple Filters Carefully

```python
# Edge case: AND with filter that might return None
@client.on(Message(F.text & F.regex(r"\d+")))
async def handler(ctx):
    # Both text must exist AND contain digit
    # If no text, fails at first check
    pass

# Edge case: OR with similar filters
@client.on(Message(F.photo | F.video | F.document | F.audio))
async def media(ctx):
    # Matches ANY media type
    # Efficient because each is separate check
    pass

# Edge case: NOT with complex filter
@client.on(Message(~(F.text & F.regex(r"^/.*"))))
async def not_command(ctx):
    # True if: not (has text AND starts with /)
    # = True if: no text OR doesn't start with /
    pass
```

### Exception Handling in Filters

```python
def safe_filter(message):
    try:
        # Might raise exception
        data = some_external_call()
        return data is not None
    except Exception as e:
        # Return False on error
        print(f"Filter error: {e}")
        return False

@client.on(Message(F.custom(safe_filter)))
async def safe_handler(ctx):
    pass
```

### Performance Edge Cases

```python
# ✗ Bad: Expensive filter called on every message
@client.on(Message(F.custom(lambda msg: db_query(msg.user.id))))
async def expensive(ctx):
    pass

# ✓ Good: Filter cheaply, query in handler
@client.on(Message(F.text))
async def cheaper(ctx):
    user_data = db_query(ctx.user.id)
    if not user_data:
        return
    # Process
    pass
```

---

## Performance Optimization

### Filter Ordering

Order filters from cheapest to most expensive:

```python
# ✓ Good: Cheap checks first
@client.on(Message(
    F.text                              # Fastest (simple property check)
    & F.private                         # Fast (simple check)
    & F.regex(r"^\d+")                 # Medium (regex compile/match)
    & F.custom(expensive_check)        # Slowest (last)
))
async def optimized(ctx):
    pass

# ✗ Bad: Expensive check first
@client.on(Message(
    F.custom(expensive_check)          # Slowest (checked on every message!)
    & F.text
))
async def slow(ctx):
    pass
```

### Caching

```python
from functools import lru_cache

@lru_cache(maxsize=1000)
def get_user_level(user_id):
    """Cache user levels"""
    return user_id % 3  # Simplified

def check_level(message):
    return get_user_level(message.from_user.id) == 2

@client.on(Message(F.custom(check_level)))
async def level_check(ctx):
    pass
```

---

**Next:** See `buttons.md` for interactive UI elements.
