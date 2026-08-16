# 7. Buttons and Keyboards

Telegram offers two kinds of keyboards, and SwiftBot has builders for both. An **inline keyboard** attaches buttons to a specific message — clicking one fires a **callback query**, which your bot receives as an update. A **reply keyboard** pins buttons at the bottom of the chat — clicking one sends a normal text message.

## Inline keyboards <a id="inline-keyboards"></a>

```python
from swiftbot import Button, InlineKeyboard

keyboard = InlineKeyboard().row(
    Button.inline("Approve", callback_data="approve:123"),
    Button.inline("Deny",   callback_data="deny:123"),
).row(
    Button.url("Website", "https://example.com"),
)

await ctx.reply("Choose:", reply_markup=keyboard.build())
```

`Button.inline(text, callback_data)` makes a callback button; `Button.url(text, url)` makes a link button that opens a URL without contacting your bot. `InlineKeyboard.row(...)` adds one row of buttons, and you chain `.row()` calls for multiple rows.

Handle the presses with `CallbackQuery`:

```python
from swiftbot.types import CallbackQuery

@bot.on(CallbackQuery(data="approve:123"))
async def on_approve(ctx):
    await ctx.answer("Approved!")
```

For payloads that carry structured data rather than fixed strings, use `CallbackData` from [Typed Callback Data](08_CallbackData.md) instead of hand-rolled strings — it is type-safe and collision-free.

The golden rule of inline buttons: **always answer the callback** with `ctx.answer(...)` or `ctx.answer_callback(...)`. Unanswered presses leave Telegram showing a spinning wheel on the user's button, and Telegram's servers log warnings for your bot.

## Reply keyboards

```python
from swiftbot import ReplyKeyboard, RemoveKeyboard

kb = ReplyKeyboard().row(
    ReplyKeyboard.button("Menu"), ReplyKeyboard.button("Help"),
).row(
    ReplyKeyboard.button("Contact"),
)
await ctx.reply("Pick an option:", reply_markup=kb.build())
```

Two modifiers make reply keyboards friendlier on phones: `.resize()` shrinks the buttons to fit the screen, and `.one_time()` hides the keyboard after the first click. Combine them: `ReplyKeyboard().resize().one_time()`.

## Removing a keyboard

To clear a pinned reply keyboard, send any message with a remove markup:

```python
await ctx.reply("Done.", reply_markup=RemoveKeyboard().build())
```

Clicks on reply keyboards arrive as ordinary text messages, so you handle them with the same `Message(text=...)` handlers as normal chat input — no special event type is needed.
