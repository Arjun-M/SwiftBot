# Real-World Usage & Examples

Complete, production-ready examples for common use cases.

## Table of Contents

1. [E-Commerce Bot](#e-commerce-bot)
2. [Statistics & Analytics Bot](#statistics--analytics-bot)
3. [Content Moderator](#content-moderator)
4. [Multi-Language Bot](#multi-language-bot)
5. [State Management](#state-management)
6. [Database Integration](#database-integration)
7. [Payment Processing](#payment-processing)

---

## E-Commerce Bot

```python
import asyncio
from swiftbot import SwiftBot, Message, CallbackQuery, Filters as F, Button, InlineKeyboard

client = SwiftBot(token="YOUR_TOKEN", parse_mode="HTML")

# Database (use real DB in production)
products = {
    "1": {"name": "Laptop", "price": 999, "desc": "Gaming laptop"},
    "2": {"name": "Mouse", "price": 25, "desc": "Wireless mouse"},
    "3": {"name": "Keyboard", "price": 75, "desc": "Mechanical keyboard"}
}

cart = {}  # user_id -> {product_id: quantity}

@client.on(Message(F.command("start")))
async def start(ctx):
    keyboard = InlineKeyboard(buttons=[
        [Button.inline("🛍️ Browse Products", "browse")],
        [Button.inline("🛒 View Cart", "cart")],
        [Button.inline("❓ Help", "help")]
    ])
    
    await ctx.reply(
        f"Welcome {ctx.user.first_name}! 🎉\n\nBrowse our products below.",
        reply_markup=keyboard.to_dict()
    )

@client.on(CallbackQuery(pattern="browse"))
async def show_products(ctx):
    text = "<b>📦 Our Products:</b>\n\n"
    buttons = []
    
    for pid, product in products.items():
        text += f"<b>{product['name']}</b> - ${product['price']}\n{product['desc']}\n\n"
        buttons.append([Button.inline(f"Add {product['name']}", f"add_{pid}")])
    
    keyboard = InlineKeyboard(buttons=buttons)
    await ctx.answer_callback()
    await ctx.edit(text, reply_markup=keyboard.to_dict())

@client.on(CallbackQuery(pattern=r"add_(\d)"))
async def add_to_cart(ctx):
    product_id = ctx.match.group(1)
    user_id = ctx.user.id
    
    if user_id not in cart:
        cart[user_id] = {}
    
    cart[user_id][product_id] = cart[user_id].get(product_id, 0) + 1
    
    product = products[product_id]
    await ctx.answer_callback(f"✓ Added {product['name']} to cart!", show_alert=False)

@client.on(CallbackQuery(pattern="cart"))
async def show_cart(ctx):
    user_id = ctx.user.id
    
    if user_id not in cart or not cart[user_id]:
        await ctx.answer_callback()
        await ctx.edit("🛒 Your cart is empty")
        return
    
    total = 0
    text = "<b>🛒 Shopping Cart:</b>\n\n"
    
    for pid, qty in cart[user_id].items():
        product = products[pid]
        price = product["price"] * qty
        total += price
        text += f"<b>{product['name']}</b> x{qty} - ${price}\n"
    
    text += f"\n<b>Total:</b> ${total}"
    
    keyboard = InlineKeyboard(buttons=[
        [Button.inline("💳 Checkout", "checkout")],
        [Button.inline("🔄 Continue Shopping", "browse")]
    ])
    
    await ctx.answer_callback()
    await ctx.edit(text, reply_markup=keyboard.to_dict())

@client.on(CallbackQuery(pattern="checkout"))
async def checkout(ctx):
    await ctx.answer_callback()
    await ctx.edit("✓ Order placed! Thank you for shopping with us.")
    cart[ctx.user.id] = {}

if __name__ == "__main__":
    asyncio.run(client.run_polling())
```

---

## Statistics & Analytics Bot

```python
import asyncio
from datetime import datetime, timedelta
from swiftbot import SwiftBot, Message, CallbackQuery, Filters as F, Button, InlineKeyboard

client = SwiftBot(token="YOUR_TOKEN", parse_mode="HTML")

# Statistics storage
stats = {
    "messages_today": 0,
    "users_active": set(),
    "start_time": datetime.now()
}

class StatsMiddleware:
    async def on_update(self, ctx, next_handler):
        stats["messages_today"] += 1
        if ctx.user:
            stats["users_active"].add(ctx.user.id)
        await next_handler()

client.use(StatsMiddleware())

@client.on(Message(F.command("stats")))
async def show_stats(ctx):
    uptime = datetime.now() - stats["start_time"]
    hours = uptime.seconds // 3600
    
    keyboard = InlineKeyboard(buttons=[
        [Button.inline("📊 Detailed", "stats_detailed")],
        [Button.inline("🔄 Refresh", "stats_refresh")]
    ])
    
    text = f"""<b>📊 Bot Statistics:</b>

Messages Today: {stats['messages_today']}
Active Users: {len(stats['users_active'])}
Uptime: {hours}h {(uptime.seconds % 3600) // 60}m

Last Updated: {datetime.now().strftime('%H:%M:%S')}
"""
    
    await ctx.reply(text, reply_markup=keyboard.to_dict())

@client.on(CallbackQuery(pattern="stats_detailed"))
async def detailed_stats(ctx):
    text = f"""<b>📊 Detailed Statistics:</b>

<b>Messages:</b>
• Today: {stats['messages_today']}
• Average per user: {stats['messages_today'] // max(1, len(stats['users_active']))}

<b>Users:</b>
• Active today: {len(stats['users_active'])}

<b>System:</b>
• Uptime: {(datetime.now() - stats['start_time']).total_seconds() / 3600:.1f}h
• Last Updated: {datetime.now().strftime('%H:%M:%S')}
"""
    
    await ctx.answer_callback()
    await ctx.edit(text)

@client.on(CallbackQuery(pattern="stats_refresh"))
async def refresh_stats(ctx):
    await ctx.answer_callback("✓ Refreshed", show_alert=False)
    # Trigger stats_command again to update
    await show_stats(ctx)

if __name__ == "__main__":
    asyncio.run(client.run_polling())
```

---

## Content Moderator

```python
import asyncio
import re
from swiftbot import SwiftBot, Message, Filters as F, Button, InlineKeyboard

client = SwiftBot(token="YOUR_TOKEN")

# Moderation rules
SPAM_PATTERNS = [
    r"(?:click|buy|visit)\s+(?:here|now)",
    r"(?:follow|subscribe)\s+@\w+",
    r"https?://t\.me/\+\w+",  # Premium groups
    r"(?:earn|make)\s+(?:money|cash|btc)"
]

BANNED_WORDS = ["banned_word1", "banned_word2"]

def check_spam(text):
    for pattern in SPAM_PATTERNS:
        if re.search(pattern, text, re.I):
            return True
    return False

def check_banned_words(text):
    for word in BANNED_WORDS:
        if word.lower() in text.lower():
            return True
    return False

@client.on(Message(F.group & F.text))
async def moderate_message(ctx):
    text = ctx.text
    
    # Check spam
    if check_spam(text):
        await ctx.delete()
        await client.restrict_chat_member(
            ctx.chat.id,
            ctx.user.id,
            permissions={"can_send_messages": False}
        )
        
        await client.send_message(
            ctx.chat.id,
            f"⚠️ User {ctx.user.first_name} was restricted for spam"
        )
        return
    
    # Check banned words
    if check_banned_words(text):
        await ctx.delete()
        warning_msg = await client.send_message(
            ctx.chat.id,
            f"⚠️ {ctx.user.first_name}, that word is not allowed here"
        )
        
        # Auto-delete warning after 5 seconds
        await asyncio.sleep(5)
        await client.delete_message(ctx.chat.id, warning_msg['message_id'])

@client.on(Message(F.group & F.media))
async def moderate_media(ctx):
    # Check media description/caption for spam
    caption = ctx.caption or ""
    if check_spam(caption):
        await ctx.delete()
        await client.send_message(ctx.chat.id, "⚠️ Media removed due to spam")

if __name__ == "__main__":
    asyncio.run(client.run_polling())
```

---

## Multi-Language Bot

```python
import asyncio
from swiftbot import SwiftBot, Message, CallbackQuery, Filters as F, Button, InlineKeyboard

client = SwiftBot(token="YOUR_TOKEN", parse_mode="HTML")

# Translation dictionary
translations = {
    "en": {
        "start": "Welcome!",
        "help": "How can I help?",
        "lang": "Language"
    },
    "es": {
        "start": "¡Bienvenido!",
        "help": "¿Cómo puedo ayudar?",
        "lang": "Idioma"
    },
    "fr": {
        "start": "Bienvenue!",
        "help": "Comment puis-je vous aider?",
        "lang": "Langue"
    }
}

user_lang = {}  # user_id -> language

def get_text(user_id, key):
    lang = user_lang.get(user_id, "en")
    return translations.get(lang, {}).get(key, translations["en"].get(key))

@client.on(Message(F.command("start")))
async def start(ctx):
    keyboard = InlineKeyboard(buttons=[
        [Button.inline("🇬🇧 English", "lang_en")],
        [Button.inline("🇪🇸 Español", "lang_es")],
        [Button.inline("🇫🇷 Français", "lang_fr")]
    ])
    
    await ctx.reply("Select your language:", reply_markup=keyboard.to_dict())

@client.on(CallbackQuery(pattern=r"lang_(\w+)"))
async def set_language(ctx):
    lang = ctx.match.group(1)
    user_lang[ctx.user.id] = lang
    
    text = get_text(ctx.user.id, "start")
    
    keyboard = InlineKeyboard(buttons=[
        [Button.inline(get_text(ctx.user.id, "help"), "help")]
    ])
    
    await ctx.answer_callback(f"✓ Language set to {lang.upper()}")
    await ctx.edit(text, reply_markup=keyboard.to_dict())

@client.on(CallbackQuery(pattern="help"))
async def help_cmd(ctx):
    text = get_text(ctx.user.id, "help")
    await ctx.answer_callback()
    await ctx.edit(text)

if __name__ == "__main__":
    asyncio.run(client.run_polling())
```

---

## State Management

Complete example with FSM for multi-step registration:

```python
import asyncio
from swiftbot import SwiftBot, Message, CallbackQuery, Filters as F, Button, InlineKeyboard
from enum import Enum

client = SwiftBot(token="YOUR_TOKEN", parse_mode="HTML")

class State(str, Enum):
    IDLE = "idle"
    WAITING_NAME = "waiting_name"
    WAITING_AGE = "waiting_age"
    WAITING_EMAIL = "waiting_email"
    CONFIRMING = "confirming"

@client.on(Message(F.command("register")))
async def start_registration(ctx):
    await ctx.set_state(State.WAITING_NAME)
    await ctx.reply("Let's register! What's your name?")

@client.on(Message(), priority=10)
async def handle_by_state(ctx):
    state = await ctx.get_state()
    
    if state == State.WAITING_NAME:
        await ctx.user_data.set("name", ctx.text)
        await ctx.set_state(State.WAITING_AGE)
        await ctx.reply(f"Nice to meet you, {ctx.text}! How old are you?")
    
    elif state == State.WAITING_AGE:
        try:
            age = int(ctx.text)
            if age < 13 or age > 120:
                await ctx.reply("Please enter a valid age")
                return
            
            await ctx.user_data.set("age", age)
            await ctx.set_state(State.WAITING_EMAIL)
            await ctx.reply(f"Got it! You're {age} years old. What's your email?")
        except ValueError:
            await ctx.reply("Please enter a valid number")
    
    elif state == State.WAITING_EMAIL:
        import re
        if not re.match(r"[^@]+@[^@]+\.[^@]+", ctx.text):
            await ctx.reply("Please enter a valid email")
            return
        
        await ctx.user_data.set("email", ctx.text)
        
        name = await ctx.user_data.get("name")
        age = await ctx.user_data.get("age")
        email = ctx.text
        
        text = f"""<b>Confirm your information:</b>

Name: {name}
Age: {age}
Email: {email}
"""
        
        keyboard = InlineKeyboard(buttons=[
            [
                Button.inline("✓ Confirm", "confirm_reg"),
                Button.inline("✗ Cancel", "cancel_reg")
            ]
        ])
        
        await ctx.set_state(State.CONFIRMING)
        await ctx.reply(text, reply_markup=keyboard.to_dict())

@client.on(CallbackQuery(pattern="confirm_reg"))
async def confirm_registration(ctx):
    # Save to database
    name = await ctx.user_data.get("name")
    
    await ctx.answer_callback("✓ Registered!")
    await ctx.edit(f"Welcome, {name}! Registration complete.")
    await ctx.clear_state()

@client.on(CallbackQuery(pattern="cancel_reg"))
async def cancel_registration(ctx):
    await ctx.answer_callback()
    await ctx.edit("Registration cancelled")
    await ctx.clear_state()

if __name__ == "__main__":
    asyncio.run(client.run_polling())
```

---

## Database Integration

```python
import asyncio
import sqlite3
from swiftbot import SwiftBot, Message, Filters as F

client = SwiftBot(token="YOUR_TOKEN")

# Database setup
def init_db():
    conn = sqlite3.connect("bot.db")
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS users
                 (id INTEGER PRIMARY KEY, user_id INTEGER, name TEXT, balance INTEGER)''')
    conn.commit()
    conn.close()

def add_user(user_id, name):
    conn = sqlite3.connect("bot.db")
    c = conn.cursor()
    c.execute("INSERT OR IGNORE INTO users (user_id, name, balance) VALUES (?, ?, 0)",
              (user_id, name))
    conn.commit()
    conn.close()

def get_balance(user_id):
    conn = sqlite3.connect("bot.db")
    c = conn.cursor()
    c.execute("SELECT balance FROM users WHERE user_id = ?", (user_id,))
    result = c.fetchone()
    conn.close()
    return result[0] if result else 0

def add_balance(user_id, amount):
    conn = sqlite3.connect("bot.db")
    c = conn.cursor()
    c.execute("UPDATE users SET balance = balance + ? WHERE user_id = ?",
              (amount, user_id))
    conn.commit()
    conn.close()

# Handlers
@client.on(Message(F.command("start")))
async def start(ctx):
    add_user(ctx.user.id, ctx.user.first_name)
    balance = get_balance(ctx.user.id)
    await ctx.reply(f"Balance: ${balance}")

@client.on(Message(F.command("add")))
async def add_funds(ctx):
    if not ctx.args:
        await ctx.reply("Usage: /add <amount>")
        return
    
    try:
        amount = int(ctx.args[0])
        add_balance(ctx.user.id, amount)
        balance = get_balance(ctx.user.id)
        await ctx.reply(f"✓ Added ${amount}. New balance: ${balance}")
    except ValueError:
        await ctx.reply("Invalid amount")

if __name__ == "__main__":
    init_db()
    asyncio.run(client.run_polling())
```

---

## Payment Processing

```python
import asyncio
from swiftbot import SwiftBot, Message, Filters as F, Button, InlineKeyboard

client = SwiftBot(token="YOUR_TOKEN")

# Stripe integration (example)
stripe_token = "YOUR_STRIPE_TOKEN"

@client.on(Message(F.command("buy")))
async def buy_item(ctx):
    keyboard = InlineKeyboard(buttons=[
        [Button.inline("💳 Pay with Card", "pay_card")],
        [Button.inline("🏦 Bank Transfer", "pay_bank")]
    ])
    
    await ctx.reply(
        "Choose payment method (Item: $10)",
        reply_markup=keyboard.to_dict()
    )

@client.on(CallbackQuery(pattern="pay_card"))
async def pay_with_card(ctx):
    # Send invoice to Telegram
    await client.send_invoice(
        chat_id=ctx.chat.id,
        title="SwiftBot Premium",
        description="Premium subscription for 1 month",
        payload="premium_monthly",
        provider_token=stripe_token,
        currency="USD",
        prices=[{"label": "Premium", "amount": 1000}]  # in cents
    )

if __name__ == "__main__":
    asyncio.run(client.run_polling())
```

---

**See `edge-cases.md` for handling common issues.**
