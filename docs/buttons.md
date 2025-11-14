# Buttons & Keyboards - Interactive UI

Buttons and keyboards provide interactive UI for users. SwiftBot supports inline buttons (above message) and reply buttons (below message).

## Table of Contents

1. [Inline Buttons](#inline-buttons)
2. [Reply Buttons](#reply-buttons)
3. [Keyboard Types](#keyboard-types)
4. [Real-World Examples](#real-world-examples)
5. [Advanced Techniques](#advanced-techniques)
6. [Edge Cases](#edge-cases)

---

## Inline Buttons

Inline buttons appear above the message input field. They trigger callback queries.

### Creating Inline Buttons

```python
from swiftbot import Button, InlineKeyboard

# Simple inline button
btn = Button.inline("Click me", "callback_data")

# Button with emoji
btn = Button.inline("👍 Like", "like_data")

# URL button (opens link, no callback)
btn = Button.url("🔗 Google", "https://google.com")

# Web App button (opens web app)
btn = Button.web_app("🌐 Open App", "https://myapp.com")
```

### Organizing Buttons in Keyboard

```python
# Single row, single button
keyboard = InlineKeyboard(buttons=[
    [Button.inline("OK", "ok")]
])

# Single row, multiple buttons
keyboard = InlineKeyboard(buttons=[
    [
        Button.inline("Yes", "yes"),
        Button.inline("No", "no")
    ]
])

# Multiple rows
keyboard = InlineKeyboard(buttons=[
    [Button.inline("1", "1"), Button.inline("2", "2")],
    [Button.inline("3", "3"), Button.inline("4", "4")]
])

# Building incrementally
keyboard = InlineKeyboard(buttons=[])
keyboard.add_row(Button.inline("Row 1", "r1"))
keyboard.add_row(Button.inline("Row 2", "r2"))
keyboard.add_button(Button.inline("Add to last row", "add"))
```

### Sending with Inline Button

```python
@client.on(Message(F.command("start")))
async def start(ctx):
    keyboard = InlineKeyboard(buttons=[[
        Button.inline("📊 Stats", "stats"),
        Button.inline("⚙️ Settings", "settings")
    ]])
    
    await ctx.reply(
        "Choose an option:",
        reply_markup=keyboard.to_dict()
    )

# Handle callback
@client.on(CallbackQuery(pattern="stats"))
async def show_stats(ctx):
    await ctx.answer_callback()  # Dismiss loading state
    await ctx.edit("📊 <b>Statistics</b>\n\nUsers: 1000")
```

---

## Reply Buttons

Reply buttons appear as a keyboard layout below the message input field.

### Creating Reply Buttons

```python
from swiftbot import Button, ReplyKeyboard

# Text button
btn = Button.text("Option 1")

# Button row
keyboard = ReplyKeyboard(buttons=[
    [Button.text("A"), Button.text("B"), Button.text("C")],
    [Button.text("D"), Button.text("E")]
])

# Special buttons
keyboard.add_row(Button.contact("📱 Share Contact"))
keyboard.add_row(Button.location("📍 Share Location"))
keyboard.add_row(Button.poll("🗳️ Create Poll"))
```

### Keyboard Properties

```python
# One-time keyboard (disappears after use)
keyboard = ReplyKeyboard(buttons=[[Button.text("Done")]], one_time_keyboard=True)

# Resizable keyboard
keyboard = ReplyKeyboard(buttons=[[...]], resize_keyboard=True)

# Selective keyboard (only for certain users)
keyboard = ReplyKeyboard(buttons=[[...]], selective=True)

# Placeholder text
keyboard = ReplyKeyboard(
    buttons=[[...]],
    input_field_placeholder="Type here..."
)
```

### Sending Reply Keyboard

```python
@client.on(Message(F.command("menu")))
async def show_menu(ctx):
    keyboard = ReplyKeyboard(buttons=[
        [Button.text("📊 Stats"), Button.text("❓ Help")],
        [Button.text("⚙️ Settings"), Button.text("❌ Cancel")]
    ], one_time_keyboard=True)
    
    await ctx.reply(
        "Choose an option:",
        reply_markup=keyboard.to_dict()
    )
```

---

## Keyboard Types

### Button Types Reference

```python
# Inline buttons (callback)
Button.inline("Text", "callback_data")

# URL button (opens in browser)
Button.url("Text", "https://example.com")

# Web App button
Button.web_app("Open App", "https://webapp.com")

# Switch inline (inline mode)
Button.switch_inline("Search", "initial query")
Button.switch_inline("Same Chat", "query", same_peer=True)

# Payment button
Button.pay("💳 Pay $10")

# User/Chat request buttons (Bot API 9.0+)
Button.request_user("Select User", request_id=1)
Button.request_chat("Select Chat", request_id=2)

# Copy text to clipboard
Button.copy_text("Copy", "text to copy")

# Login button
Button.login("Login", "https://site.com/login")

# Reply buttons
Button.text("Option")
Button.contact("Share Contact")
Button.location("Share Location")
Button.poll("Create Poll")
```

---

## Real-World Examples

### Pagination

```python
@client.on(Message(F.command("items")))
async def show_items(ctx):
    page = 1
    items_per_page = 5
    
    await show_page(ctx, page)

async def show_page(ctx, page):
    items = ["Item 1", "Item 2", "Item 3", "Item 4", "Item 5",
             "Item 6", "Item 7", "Item 8", "Item 9", "Item 10"]
    
    start = (page - 1) * 5
    end = start + 5
    
    text = "<b>Items:</b>\n"
    for i, item in enumerate(items[start:end], start + 1):
        text += f"{i}. {item}\n"
    
    # Build pagination buttons
    buttons = []
    if page > 1:
        buttons.append(Button.inline("◀️ Previous", f"page_{page-1}"))
    if end < len(items):
        buttons.append(Button.inline("Next ▶️", f"page_{page+1}"))
    
    keyboard = InlineKeyboard(buttons=[buttons] if buttons else [])
    
    if hasattr(ctx, 'message'):
        await ctx.edit(text, reply_markup=keyboard.to_dict())
    else:
        await ctx.reply(text, reply_markup=keyboard.to_dict())

@client.on(CallbackQuery(pattern=r"page_(\d+)"))
async def handle_page(ctx):
    page = int(ctx.match.group(1))
    await ctx.answer_callback()
    await show_page(ctx, page)
```

### Menu with Submenus

```python
@client.on(Message(F.command("menu")))
async def main_menu(ctx):
    keyboard = InlineKeyboard(buttons=[
        [Button.inline("📊 Analytics", "submenu_analytics")],
        [Button.inline("⚙️ Settings", "submenu_settings")],
        [Button.inline("❓ Help", "submenu_help")]
    ])
    
    await ctx.reply("Main Menu:", reply_markup=keyboard.to_dict())

@client.on(CallbackQuery(pattern="submenu_analytics"))
async def analytics_submenu(ctx):
    keyboard = InlineKeyboard(buttons=[
        [Button.inline("📈 Daily Stats", "stats_daily")],
        [Button.inline("📊 Weekly Stats", "stats_weekly")],
        [Button.inline("◀️ Back", "menu_back")]
    ])
    
    await ctx.answer_callback()
    await ctx.edit("📊 Analytics:", reply_markup=keyboard.to_dict())

@client.on(CallbackQuery(pattern="menu_back"))
async def back_to_menu(ctx):
    keyboard = InlineKeyboard(buttons=[
        [Button.inline("📊 Analytics", "submenu_analytics")],
        [Button.inline("⚙️ Settings", "submenu_settings")],
        [Button.inline("❓ Help", "submenu_help")]
    ])
    
    await ctx.answer_callback()
    await ctx.edit("Main Menu:", reply_markup=keyboard.to_dict())
```

### Confirmation Dialog

```python
@client.on(Message(F.command("delete")))
async def delete_command(ctx):
    keyboard = InlineKeyboard(buttons=[
        [
            Button.inline("✓ Confirm", "confirm_delete"),
            Button.inline("✗ Cancel", "cancel_delete")
        ]
    ])
    
    await ctx.reply(
        "Are you sure? This cannot be undone.",
        reply_markup=keyboard.to_dict()
    )

@client.on(CallbackQuery(pattern="confirm_delete"))
async def confirm(ctx):
    await ctx.answer_callback("Item deleted!", show_alert=True)
    await ctx.edit("✓ Deleted")

@client.on(CallbackQuery(pattern="cancel_delete"))
async def cancel(ctx):
    await ctx.answer_callback()
    await ctx.edit("❌ Cancelled")
```

### Like/Rating System

```python
@client.on(Message(F.command("rate")))
async def rate_post(ctx):
    keyboard = InlineKeyboard(buttons=[
        [
            Button.inline("👍 0", "like_like"),
            Button.inline("👎 0", "like_dislike"),
            Button.inline("❤️ 0", "like_heart")
        ]
    ])
    
    await ctx.reply("Rate this post:", reply_markup=keyboard.to_dict())

# Track reactions in database/memory
reactions = {}

@client.on(CallbackQuery(pattern=r"like_(\w+)"))
async def handle_reaction(ctx):
    reaction = ctx.match.group(1)
    post_id = ctx.message.message_id
    
    # Update count (in real app, use database)
    key = f"{post_id}_{reaction}"
    reactions[key] = reactions.get(key, 0) + 1
    
    keyboard = InlineKeyboard(buttons=[
        [
            Button.inline(f"👍 {reactions.get(f'{post_id}_like', 0)}", "like_like"),
            Button.inline(f"👎 {reactions.get(f'{post_id}_dislike', 0)}", "like_dislike"),
            Button.inline(f"❤️ {reactions.get(f'{post_id}_heart', 0)}", "like_heart")
        ]
    ])
    
    await ctx.answer_callback()
    await ctx.edit("Rate this post:", reply_markup=keyboard.to_dict())
```

### Dynamic Button List

```python
@client.on(Message(F.command("users")))
async def list_users(ctx):
    users = ["Alice", "Bob", "Charlie", "Diana"]
    
    buttons = [[Button.inline(user, f"select_{i}")] for i, user in enumerate(users)]
    keyboard = InlineKeyboard(buttons=buttons)
    
    await ctx.reply("Select a user:", reply_markup=keyboard.to_dict())

@client.on(CallbackQuery(pattern=r"select_(\d+)"))
async def select_user(ctx):
    user_idx = int(ctx.match.group(1))
    users = ["Alice", "Bob", "Charlie", "Diana"]
    selected = users[user_idx]
    
    await ctx.answer_callback(f"Selected: {selected}")
    await ctx.edit(f"✓ Selected: {selected}")
```

---

## Advanced Techniques

### URL Buttons with Parameters

```python
# Pass data in URL
@client.on(Message(F.command("share")))
async def share(ctx):
    user_id = ctx.user.id
    username = ctx.user.username or ctx.user.first_name
    
    # Create shareable link
    share_url = f"https://t.me/your_bot?start=ref_{user_id}"
    
    keyboard = InlineKeyboard(buttons=[[
        Button.url("🔗 Share", share_url)
    ]])
    
    await ctx.reply("Share your referral:", reply_markup=keyboard.to_dict())
```

### Inline Buttons with User Data

```python
# Store user choice in memory
user_choices = {}

@client.on(Message(F.command("choose")))
async def choose(ctx):
    keyboard = InlineKeyboard(buttons=[
        [Button.inline("Option A", "choice_a")],
        [Button.inline("Option B", "choice_b")],
        [Button.inline("Option C", "choice_c")]
    ])
    
    await ctx.reply("Choose one:", reply_markup=keyboard.to_dict())

@client.on(CallbackQuery(pattern=r"choice_(\w)"))
async def handle_choice(ctx):
    choice = ctx.match.group(1).upper()
    user_choices[ctx.user.id] = choice
    
    await ctx.answer_callback(f"Saved choice: {choice}")
    await ctx.edit(f"✓ You chose: {choice}")
```

---

## Edge Cases

### Callback Data Size Limit

```python
# ❌ Bad: Callback data too large (max 64 bytes)
Button.inline("Get full data", json.dumps({"user": user_dict}))

# ✓ Good: Store data separately, reference with ID
button_cache = {}
cache_id = str(uuid.uuid4())
button_cache[cache_id] = user_dict

Button.inline("Get data", cache_id)  # Short ID
```

### Removing Keyboard

```python
@client.on(Message(F.text))
async def remove_keyboard(ctx):
    from swiftbot import RemoveKeyboard
    
    await ctx.reply(
        "Keyboard removed",
        reply_markup=RemoveKeyboard().to_dict()
    )
```

### Button State Management

```python
# Track button sequences
button_sequence = {}

@client.on(Message(F.command("sequence")))
async def start_sequence(ctx):
    button_sequence[ctx.user.id] = []
    
    keyboard = InlineKeyboard(buttons=[
        [Button.inline("Step 1", "seq_1")]
    ])
    
    await ctx.reply("Start sequence:", reply_markup=keyboard.to_dict())

@client.on(CallbackQuery(pattern=r"seq_(\d)"))
async def sequence_step(ctx):
    step = int(ctx.match.group(1))
    button_sequence[ctx.user.id].append(step)
    
    next_step = step + 1
    keyboard = InlineKeyboard(buttons=[
        [Button.inline(f"Step {next_step}", f"seq_{next_step}")]
    ])
    
    await ctx.answer_callback()
    await ctx.edit(f"You're on step {step}", reply_markup=keyboard.to_dict())
```

---

**Next:** See `real-world-usage.md` for complete bot examples.
