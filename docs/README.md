# SwiftBot Documentation Index

Complete documentation for SwiftBot - Ultra-Fast Telegram Bot Framework

## 📚 Documentation Structure

### Main Documentation
- **[USAGE.md](USAGE.md)** - Complete usage guide covering everything from installation to performance tips

### Detailed Guides (docs/ folder)

| File | Content |
|------|---------|
| **[docs/filters.md](docs/filters.md)** | Complete filter system reference with examples |
| **[docs/buttons.md](docs/buttons.md)** | Interactive UI - inline & reply buttons with real examples |
| **[docs/example.md](docs/example.md)** | Production-ready examples: E-commerce, Analytics, Moderation, etc. |
| **[docs/edge-cases.md](docs/edge-cases.md)** | Edge cases, troubleshooting, limits, and FAQ |

---

## 🚀 Quick Start

### Installation
```bash
pip install swiftbot
```

### First Bot
```python
from swiftbot import SwiftBot, Message, Filters as F

client = SwiftBot(token="YOUR_TOKEN")

@client.on(Message(F.text))
async def echo(ctx):
    await ctx.reply(f"You said: {ctx.text}")

# Run
import asyncio
asyncio.run(client.run_polling())
```

---

## 📖 Learning Path

**Beginner:**
1. Read [USAGE.md - Installation & Setup](USAGE.md#installation--setup)
2. Try [USAGE.md - Quick Start](USAGE.md#quick-start)
3. Explore [docs/filters.md - Basic Filters](docs/filters.md#basic-filters)

**Intermediate:**
1. Learn [USAGE.md - Buttons & Keyboards](USAGE.md#buttons--keyboards)
2. Study [docs/filters.md - Filter Composition](docs/filters.md#filter-composition)
3. Check [docs/example.md](docs/example.md) examples

**Advanced:**
1. Master [docs/filters.md - Custom Filters](docs/filters.md#custom-filters)
2. Implement [USAGE.md - Advanced Features](USAGE.md#advanced-features)
3. Handle [docs/edge-cases.md](docs/edge-cases.md) properly

---

## 🔍 By Topic

### Core Features
- **Messages & Handlers:** [USAGE.md](USAGE.md#messages--handlers)
- **Filters System:** [docs/filters.md](docs/filters.md)
- **Buttons & Keyboards:** [docs/buttons.md](docs/buttons.md)
- **Context Object:** [USAGE.md](USAGE.md#context-object)

### Advanced
- **Middleware:** [USAGE.md#middleware](USAGE.md#middleware)
- **State Management (FSM):** [USAGE.md#state-management-fsm](USAGE.md#state-management-fsm)
- **Custom Filters:** [docs/filters.md#custom-filters](docs/filters.md#custom-filters)
- **Error Handling:** [USAGE.md#error-handling](USAGE.md#error-handling)

### Examples
- **E-Commerce Bot:** [docs/example.md#e-commerce-bot](docs/example.md#e-commerce-bot)
- **Analytics Bot:** [docs/example.md#statistics--analytics-bot](docs/example.md#statistics--analytics-bot)
- **Content Moderator:** [docs/example.md#content-moderator](docs/example.md#content-moderator)
- **Multi-Language Bot:** [docs/example.md#multi-language-bot](docs/example.md#multi-language-bot)

---

## 🛠️ Common Tasks

### I want to...

**Match specific message types**
→ See [docs/filters.md#basic-filters](docs/filters.md#basic-filters)

**Create interactive buttons**
→ See [docs/buttons.md](docs/buttons.md)

**Handle multi-step conversations**
→ See [docs/example.md#state-management](docs/example.md#state-management)

**Optimize performance**
→ See [USAGE.md#performance-tips](USAGE.md#performance-tips)

**Handle errors gracefully**
→ See [docs/edge-cases.md#error-handling](docs/edge-cases.md#error-handling)

**Integrate with database**
→ See [docs/example.md#database-integration](docs/example.md#database-integration)

**Implement admin commands**
→ See [docs/edge-cases.md#faq](docs/edge-cases.md#faq)

**Handle payment processing**
→ See [docs/example.md#payment-processing](docs/example.md#payment-processing)

---

## 📝 API Quick Reference

### Core Classes
```python
from swiftbot import SwiftBot, Message, CallbackQuery, Filters, Button, InlineKeyboard

# Create bot
client = SwiftBot(token="...", parse_mode="HTML")

# Register handler
@client.on(Message(...))
async def handler(ctx): pass

# Send message
await ctx.reply("text")

# Send with buttons
keyboard = InlineKeyboard(...)
await ctx.reply("text", reply_markup=keyboard.to_dict())

# Run bot
asyncio.run(client.run_polling())
```

### Common Filters
```python
F.text              # Has text
F.private           # Private chat
F.group             # Group chat
F.command("cmd")    # Command
F.regex(r"pattern") # Regex match
F.photo | F.video   # Photo OR video
F.text & F.private  # Text AND private
~F.forwarded        # NOT forwarded
F.custom(func)      # Custom function
```

### Context Methods
```python
await ctx.reply("text")           # Reply to message
await ctx.edit("text")            # Edit message
await ctx.delete()                # Delete message
await ctx.send_photo(...)         # Send photo
await ctx.answer_callback("text") # Answer callback
await ctx.set_state(state)        # Set user state
value = await ctx.user_data.get("key")  # Get user data
```

---

## 🐛 Troubleshooting

**Bot not responding?**
→ Check [docs/edge-cases.md#error-handling](docs/edge-cases.md#error-handling)

**Filters not working?**
→ See [docs/filters.md#filter-edge-cases](docs/filters.md#filter-edge-cases)

**Buttons not showing?**
→ Check [docs/buttons.md#edge-cases](docs/buttons.md#edge-cases)

**Performance issues?**
→ See [docs/edge-cases.md#performance-issues](docs/edge-cases.md#performance-issues)

---

## 📚 Additional Resources

- **Complete Examples:** [docs/example.md](docs/example.md)
- **FAQ:** [docs/edge-cases.md#faq](docs/edge-cases.md#faq)
- **Telegram Limits:** [docs/edge-cases.md#telegram-limits](docs/edge-cases.md#telegram-limits)

---

## ✅ Verification Checklist

After reading documentation:

- [ ] Can install and run SwiftBot
- [ ] Understand message handlers and events
- [ ] Know how to use filters effectively
- [ ] Can create interactive buttons
- [ ] Understand context object methods
- [ ] Know performance optimization tips
- [ ] Can handle common edge cases
- [ ] Ready to build production bots

---

**Happy coding! 🚀**

For issues or questions, check [docs/edge-cases.md#faq](docs/edge-cases.md#faq).
