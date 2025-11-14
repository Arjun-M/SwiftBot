# Middleware System - Complete Guide

Middleware in SwiftBot processes all updates before they reach handlers. It's perfect for logging, authentication, rate limiting, statistics, and more.

## Table of Contents

1. [What is Middleware?](#what-is-middleware)
2. [Creating Middleware](#creating-middleware)
3. [Built-in Middleware](#built-in-middleware)
4. [Real-World Examples](#real-world-examples)
5. [Advanced Patterns](#advanced-patterns)
6. [Best Practices](#best-practices)
7. [Troubleshooting](#troubleshooting)

---

## What is Middleware?

Middleware is a function that runs **before every handler**. It can:
- ✅ Log all messages
- ✅ Track statistics
- ✅ Rate limit users
- ✅ Check permissions
- ✅ Modify context
- ✅ Block/allow updates
- ✅ Handle errors globally

### How Middleware Works

```
Update → Middleware 1 → Middleware 2 → Handler → Response
```

Each middleware can:
1. Process the update
2. Call `next_handler()` to continue
3. Or stop execution (block the update)

---

## Creating Middleware

### Basic Middleware Structure

```python
class MyMiddleware:
    async def on_update(self, ctx, next_handler):
        """
        Called for every update.
        
        Args:
            ctx: Context object with update data
            next_handler: Function to call next middleware/handler
        """
        # Do something before handler
        print(f"Before: {ctx.text}")
        
        # Call next middleware/handler
        await next_handler()
        
        # Do something after handler
        print(f"After: {ctx.text}")
```

### Registering Middleware

```python
from swiftbot import SwiftBot

client = SwiftBot(token="YOUR_TOKEN")

# Register middleware
client.use(MyMiddleware())

# Multiple middleware (executed in order)
client.use(LoggerMiddleware())
client.use(RateLimitMiddleware())
client.use(AuthMiddleware())
```

---

## Built-in Middleware

### 1. Logger Middleware

Log all incoming messages.

```python
import logging
from datetime import datetime

class LoggerMiddleware:
    def __init__(self, level=logging.INFO):
        self.logger = logging.getLogger("SwiftBot")
        self.logger.setLevel(level)
        
        handler = logging.StreamHandler()
        formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
        handler.setFormatter(formatter)
        self.logger.addHandler(handler)
    
    async def on_update(self, ctx, next_handler):
        """Log every update"""
        user_id = ctx.user.id if ctx.user else "Unknown"
        chat_type = ctx.chat.type if ctx.chat else "Unknown"
        text = ctx.text or "[Media]"
        
        self.logger.info(f"[{user_id}] [{chat_type}] {text}")
        
        await next_handler()

# Use
client.use(LoggerMiddleware(level=logging.DEBUG))
```

**Output:**
```
2025-11-15 00:00:01 - SwiftBot - INFO - [123456] [private] /start
2025-11-15 00:00:05 - SwiftBot - INFO - [123456] [private] hello
```

### 2. Statistics Middleware

Track bot usage statistics.

```python
from collections import defaultdict
import time

class StatisticsMiddleware:
    def __init__(self):
        self.stats = {
            'total_updates': 0,
            'users': set(),
            'messages_by_type': defaultdict(int),
            'start_time': time.time()
        }
    
    async def on_update(self, ctx, next_handler):
        """Track statistics"""
        self.stats['total_updates'] += 1
        
        if ctx.user:
            self.stats['users'].add(ctx.user.id)
        
        # Track message type
        if ctx.text:
            self.stats['messages_by_type']['text'] += 1
        elif ctx.message and ctx.message.photo:
            self.stats['messages_by_type']['photo'] += 1
        elif ctx.message and ctx.message.video:
            self.stats['messages_by_type']['video'] += 1
        
        await next_handler()
    
    def get_stats(self):
        """Get current statistics"""
        uptime = time.time() - self.stats['start_time']
        return {
            'total_updates': self.stats['total_updates'],
            'unique_users': len(self.stats['users']),
            'uptime_seconds': uptime,
            'messages_by_type': dict(self.stats['messages_by_type'])
        }

# Use
stats_middleware = StatisticsMiddleware()
client.use(stats_middleware)

# Get stats later
@client.on(Message(F.command("stats")))
async def show_stats(ctx):
    stats = stats_middleware.get_stats()
    await ctx.reply(f"""
<b>Bot Statistics:</b>
Total Updates: {stats['total_updates']}
Unique Users: {stats['unique_users']}
Uptime: {stats['uptime_seconds']:.0f}s
    """)
```

### 3. Rate Limiter Middleware

Prevent spam and abuse.

```python
import time
from collections import defaultdict

class RateLimitMiddleware:
    def __init__(self, max_requests=5, window=10):
        """
        Args:
            max_requests: Maximum requests per window
            window: Time window in seconds
        """
        self.max_requests = max_requests
        self.window = window
        self.user_requests = defaultdict(list)
    
    async def on_update(self, ctx, next_handler):
        """Rate limit by user"""
        if not ctx.user:
            await next_handler()
            return
        
        user_id = ctx.user.id
        now = time.time()
        
        # Clean old requests
        self.user_requests[user_id] = [
            t for t in self.user_requests[user_id]
            if now - t < self.window
        ]
        
        # Check rate limit
        if len(self.user_requests[user_id]) >= self.max_requests:
            await ctx.reply(
                f"⚠️ Rate limit exceeded! "
                f"Max {self.max_requests} requests per {self.window}s"
            )
            return  # Don't call next_handler (block)
        
        # Add request
        self.user_requests[user_id].append(now)
        
        await next_handler()

# Use - max 5 requests per 10 seconds
client.use(RateLimitMiddleware(max_requests=5, window=10))
```

### 4. Authentication Middleware

Restrict bot to specific users.

```python
class AuthMiddleware:
    def __init__(self, allowed_users=None, admin_only_commands=None):
        """
        Args:
            allowed_users: List of allowed user IDs (None = all)
            admin_only_commands: List of admin-only commands
        """
        self.allowed_users = set(allowed_users) if allowed_users else None
        self.admin_only_commands = admin_only_commands or []
    
    async def on_update(self, ctx, next_handler):
        """Check authentication"""
        if not ctx.user:
            return
        
        user_id = ctx.user.id
        
        # Check if user is allowed
        if self.allowed_users and user_id not in self.allowed_users:
            await ctx.reply("❌ Unauthorized. This bot is private.")
            return
        
        # Check admin commands
        if ctx.text:
            for cmd in self.admin_only_commands:
                if ctx.text.startswith(f"/{cmd}"):
                    if user_id not in self.allowed_users:
                        await ctx.reply("❌ Admin only command")
                        return
        
        await next_handler()

# Use
ADMINS = [123456789, 987654321]
client.use(AuthMiddleware(
    allowed_users=ADMINS,
    admin_only_commands=["ban", "kick", "broadcast"]
))
```

### 5. Error Handler Middleware

Global error handling.

```python
import traceback

class ErrorHandlerMiddleware:
    async def on_update(self, ctx, next_handler):
        """Handle errors globally"""
        try:
            await next_handler()
        except Exception as e:
            # Log error
            print(f"Error: {e}")
            print(traceback.format_exc())
            
            # Notify user
            try:
                await ctx.reply(
                    "❌ An error occurred. Please try again later."
                )
            except:
                pass
    
    async def on_error(self, ctx, exception):
        """Called when handler raises error"""
        print(f"Handler error: {exception}")

# Use
client.use(ErrorHandlerMiddleware())
```

---

## Real-World Examples

### Complete Bot with Multiple Middleware

```python
import asyncio
from SwiftBot import SwiftBot, Message, Filters as F
from datetime import datetime
import logging

client = SwiftBot(token="YOUR_TOKEN", parse_mode="HTML")

# 1. Logger
class LoggerMiddleware:
    def __init__(self):
        logging.basicConfig(level=logging.INFO)
        self.logger = logging.getLogger("Bot")
    
    async def on_update(self, ctx, next_handler):
        user = ctx.user.first_name if ctx.user else "Unknown"
        self.logger.info(f"{user}: {ctx.text or '[media]'}")
        await next_handler()

# 2. Statistics
class StatsMiddleware:
    def __init__(self):
        self.messages_today = 0
        self.users = set()
    
    async def on_update(self, ctx, next_handler):
        self.messages_today += 1
        if ctx.user:
            self.users.add(ctx.user.id)
        await next_handler()

# 3. Rate Limiter
class RateLimitMiddleware:
    def __init__(self):
        self.user_timestamps = {}
    
    async def on_update(self, ctx, next_handler):
        if not ctx.user:
            await next_handler()
            return
        
        import time
        user_id = ctx.user.id
        now = time.time()
        
        if user_id in self.user_timestamps:
            if now - self.user_timestamps[user_id] < 1:  # 1 sec cooldown
                await ctx.reply("⚠️ Please wait...")
                return
        
        self.user_timestamps[user_id] = now
        await next_handler()

# 4. Admin Check
ADMINS = [123456789]

class AdminMiddleware:
    async def on_update(self, ctx, next_handler):
        if ctx.text and ctx.text.startswith("/admin"):
            if ctx.user.id not in ADMINS:
                await ctx.reply("❌ Admin only")
                return
        await next_handler()

# Register middleware (order matters!)
client.use(LoggerMiddleware())
client.use(StatsMiddleware())
client.use(RateLimitMiddleware())
client.use(AdminMiddleware())

# Handlers
@client.on(Message(F.command("start")))
async def start(ctx):
    await ctx.reply("Welcome! 👋")

@client.on(Message(F.text))
async def echo(ctx):
    await ctx.reply(f"You said: {ctx.text}")

if __name__ == "__main__":
    asyncio.run(client.run_polling())
```

### Anti-Spam Middleware

```python
import re
from collections import defaultdict
import time

class AntiSpamMiddleware:
    def __init__(self):
        self.spam_patterns = [
            r'https?://t\.me/\+',  # Premium groups
            r'(?:join|click|visit)\s+(?:here|now)',
            r'(?:earn|make)\s+(?:\$|money|btc)',
        ]
        self.user_warnings = defaultdict(int)
        self.banned_users = set()
    
    async def on_update(self, ctx, next_handler):
        """Check for spam"""
        if not ctx.user or not ctx.text:
            await next_handler()
            return
        
        user_id = ctx.user.id
        
        # Check if banned
        if user_id in self.banned_users:
            return  # Silently ignore
        
        # Check spam patterns
        is_spam = any(
            re.search(pattern, ctx.text, re.I)
            for pattern in self.spam_patterns
        )
        
        if is_spam:
            self.user_warnings[user_id] += 1
            
            await ctx.delete()
            
            if self.user_warnings[user_id] >= 3:
                self.banned_users.add(user_id)
                await ctx.reply(f"User {ctx.user.first_name} banned for spam")
            else:
                await ctx.reply(
                    f"⚠️ Warning {self.user_warnings[user_id]}/3: "
                    f"No spam allowed!"
                )
            return
        
        await next_handler()

# Use
client.use(AntiSpamMiddleware())
```

### Database Logging Middleware

```python
import sqlite3
from datetime import datetime

class DatabaseMiddleware:
    def __init__(self, db_path="bot.db"):
        self.db_path = db_path
        self.init_db()
    
    def init_db(self):
        """Initialize database"""
        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()
        c.execute('''
            CREATE TABLE IF NOT EXISTS messages (
                id INTEGER PRIMARY KEY,
                user_id INTEGER,
                username TEXT,
                text TEXT,
                timestamp TEXT
            )
        ''')
        conn.commit()
        conn.close()
    
    async def on_update(self, ctx, next_handler):
        """Log to database"""
        if ctx.user and ctx.text:
            conn = sqlite3.connect(self.db_path)
            c = conn.cursor()
            c.execute(
                "INSERT INTO messages (user_id, username, text, timestamp) VALUES (?, ?, ?, ?)",
                (
                    ctx.user.id,
                    ctx.user.username or ctx.user.first_name,
                    ctx.text,
                    datetime.now().isoformat()
                )
            )
            conn.commit()
            conn.close()
        
        await next_handler()

# Use
client.use(DatabaseMiddleware())
```

---

## Advanced Patterns

### Conditional Middleware

Run middleware only for specific conditions:

```python
class ConditionalMiddleware:
    def __init__(self, condition, middleware):
        """
        Args:
            condition: Function that returns True/False
            middleware: Middleware to run if condition is True
        """
        self.condition = condition
        self.middleware = middleware
    
    async def on_update(self, ctx, next_handler):
        if self.condition(ctx):
            await self.middleware.on_update(ctx, next_handler)
        else:
            await next_handler()

# Example: Rate limit only in groups
def is_group(ctx):
    return ctx.chat and ctx.chat.type in ('group', 'supergroup')

client.use(
    ConditionalMiddleware(
        condition=is_group,
        middleware=RateLimitMiddleware()
    )
)
```

### Middleware with State

Store data between requests:

```python
class SessionMiddleware:
    def __init__(self):
        self.sessions = {}
    
    async def on_update(self, ctx, next_handler):
        """Attach session to context"""
        user_id = ctx.user.id if ctx.user else None
        
        if user_id:
            if user_id not in self.sessions:
                self.sessions[user_id] = {
                    'created_at': time.time(),
                    'message_count': 0
                }
            
            self.sessions[user_id]['message_count'] += 1
            ctx.session = self.sessions[user_id]
        
        await next_handler()

# Use in handlers
@client.on(Message(F.command("session")))
async def show_session(ctx):
    if hasattr(ctx, 'session'):
        await ctx.reply(f"""
<b>Your Session:</b>
Messages: {ctx.session['message_count']}
Created: {ctx.session['created_at']}
        """)
```

### Middleware Composition

Combine multiple middleware:

```python
class CompositeMiddleware:
    def __init__(self, *middlewares):
        self.middlewares = middlewares
    
    async def on_update(self, ctx, next_handler):
        """Chain middleware"""
        async def chain(index):
            if index >= len(self.middlewares):
                await next_handler()
            else:
                await self.middlewares[index].on_update(
                    ctx,
                    lambda: chain(index + 1)
                )
        
        await chain(0)

# Use
client.use(CompositeMiddleware(
    LoggerMiddleware(),
    RateLimitMiddleware(),
    AuthMiddleware()
))
```

---

## Best Practices

### 1. Order Matters

```python
# ✓ Good order
client.use(LoggerMiddleware())       # Log first
client.use(RateLimitMiddleware())    # Then rate limit
client.use(AuthMiddleware())         # Then check auth
client.use(ErrorHandlerMiddleware()) # Catch errors last

# ✗ Bad order
client.use(ErrorHandlerMiddleware()) # Catches everything!
client.use(LoggerMiddleware())       # Never logs errors
```

### 2. Always Call next_handler()

```python
# ✗ Bad - blocks all updates
async def on_update(self, ctx, next_handler):
    print("Processing...")
    # Forgot to call next_handler()!

# ✓ Good
async def on_update(self, ctx, next_handler):
    print("Processing...")
    await next_handler()  # Always call this
```

### 3. Handle Errors

```python
async def on_update(self, ctx, next_handler):
    try:
        # Your logic
        await next_handler()
    except Exception as e:
        print(f"Middleware error: {e}")
        # Don't let errors propagate
```

### 4. Keep Middleware Fast

```python
# ✗ Bad - blocks event loop
async def on_update(self, ctx, next_handler):
    result = requests.get("...")  # Blocking!
    await next_handler()

# ✓ Good - use async
import httpx
async def on_update(self, ctx, next_handler):
    async with httpx.AsyncClient() as client:
        result = await client.get("...")
    await next_handler()
```

### 5. Clean Up Resources

```python
class ResourceMiddleware:
    def __init__(self):
        self.cache = {}
    
    async def on_update(self, ctx, next_handler):
        await next_handler()
    
    async def cleanup(self):
        """Clean up resources"""
        self.cache.clear()

# Register cleanup
import atexit
middleware = ResourceMiddleware()
atexit.register(lambda: asyncio.run(middleware.cleanup()))
```

---

## Troubleshooting

### Middleware Not Running

```python
# Check if registered
client.use(MyMiddleware())  # Must call use()

# Check if next_handler called
async def on_update(self, ctx, next_handler):
    # Do stuff
    await next_handler()  # Must call this!
```

### Handler Never Executes

```python
# Check middleware chain
async def on_update(self, ctx, next_handler):
    # If condition blocks, handler won't run
    if some_condition:
        return  # Handler never called!
    await next_handler()
```

### Memory Leaks

```python
# ✗ Bad - grows forever
class LeakyMiddleware:
    def __init__(self):
        self.data = []
    
    async def on_update(self, ctx, next_handler):
        self.data.append(ctx.text)  # Never cleaned!
        await next_handler()

# ✓ Good - bounded size
from collections import deque

class BoundedMiddleware:
    def __init__(self):
        self.data = deque(maxlen=1000)  # Max 1000 items
    
    async def on_update(self, ctx, next_handler):
        self.data.append(ctx.text)
        await next_handler()
```

---

## Complete Example: Production Bot

```python
import asyncio
import logging
from swiftbot import SwiftBot, Message, Filters as F
from collections import defaultdict
import time

client = SwiftBot(token="YOUR_TOKEN", parse_mode="HTML")

# Complete middleware stack
class LoggerMiddleware:
    def __init__(self):
        logging.basicConfig(level=logging.INFO)
        self.logger = logging.getLogger("Bot")
    
    async def on_update(self, ctx, next_handler):
        user = ctx.user.first_name if ctx.user else "Unknown"
        self.logger.info(f"{user}: {ctx.text or '[media]'}")
        await next_handler()

class RateLimitMiddleware:
    def __init__(self):
        self.timestamps = defaultdict(list)
    
    async def on_update(self, ctx, next_handler):
        if not ctx.user:
            await next_handler()
            return
        
        user_id = ctx.user.id
        now = time.time()
        
        self.timestamps[user_id] = [
            t for t in self.timestamps[user_id]
            if now - t < 60
        ]
        
        if len(self.timestamps[user_id]) >= 20:
            await ctx.reply("⚠️ Rate limited (20 msg/min)")
            return
        
        self.timestamps[user_id].append(now)
        await next_handler()

class AuthMiddleware:
    def __init__(self):
        self.admins = [123456789]
    
    async def on_update(self, ctx, next_handler):
        if ctx.text and ctx.text.startswith("/admin"):
            if ctx.user.id not in self.admins:
                await ctx.reply("❌ Admin only")
                return
        await next_handler()

class ErrorMiddleware:
    async def on_update(self, ctx, next_handler):
        try:
            await next_handler()
        except Exception as e:
            logging.error(f"Error: {e}")
            await ctx.reply("❌ Error occurred")

# Register
client.use(LoggerMiddleware())
client.use(RateLimitMiddleware())
client.use(AuthMiddleware())
client.use(ErrorMiddleware())

# Handlers
@client.on(Message(F.command("start")))
async def start(ctx):
    await ctx.reply("Welcome! 👋")

if __name__ == "__main__":
    asyncio.run(client.run_polling())
```

---

**Next:** See `USAGE.md` for complete bot setup guide.
