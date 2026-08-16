# 6. Reply Helpers

This page covers every way a handler talks back: the basic reply and answer helpers on the context, and the fluent `Reply` builder for messages with many options.

## The basics on `Context` <a id="the-basics-on-context"></a>

`ctx.reply(text)` is the workhorse. It replies in the same chat, applying the bot's default `parse_mode` from the constructor (see [Bot Core](02_BotCore.md#the-constructor)), and it accepts all the keyword arguments of Telegram's `sendMessage`:

```python
await ctx.reply("Hello <b>world</b>", parse_mode="HTML")
await ctx.reply("Hello", disable_notification=True)   # silent send
```

The family of reply helpers covers the rest of everyday use:

```python
await ctx.answer("Saved!")                              # answer a callback, ephemeral banner
await ctx.answer_callback("Done", show_alert=True)      # answer with a popup alert
await ctx.edit("Updated message text")                  # edit the triggering message
await ctx.forward(from_chat_id, message_id)             # forward into this chat
await ctx.delete_message(message_id)                    # delete a message
await ctx.chat_action("typing")                         # typing / upload indicators
await ctx.send_photo(photo=file_or_url, caption="...")  # the full send_* family
```

Two of these deserve emphasis. **`ctx.answer` / `ctx.answer_callback`** close the loop on inline button presses — Telegram shows a spinning wheel on unanswered presses and logs warnings, so always answer callbacks (see [Buttons and Keyboards](07_Buttons.md#inline-keyboards)) for when this happens). **`ctx.edit`** edits the message that triggered the handler, which is how bots update status messages in place.

## The fluent `Reply` builder

When one message needs many options — text, media, keyboard, silent delivery, forwards protection — chaining reads better than a long argument list:

```python
from swiftbot.reply import Reply

await Reply(ctx).text("See this photo").photo(photo_file) \
                 .caption("My caption").markup(keyboard) \
                 .silent().protect().send()
```

Every option method returns the builder, so they chain in any order, and `.send()` transmits the message and returns the API result. The available options:

| Option | What it sets |
|---|---|
| `.text(msg)` | the message body |
| `.answer(msg)` | same as `.text`, reads naturally for callback answers |
| `.photo(file)`, `.document(file)` | the attached media |
| `.caption(text)` | media caption |
| `.markup(keyboard)` | the reply markup (inline or reply keyboard) |
| `.reply_to(message_id)` | reply to a specific message |
| `.silent()` | `disable_notification=True` |
| `.protect()` | forwards-protection content flag |
| `.parse_mode(mode)` | override the bot's default parse mode |

## When to use which

Reach for `ctx.reply(...)` when the message is simple, for `ctx.answer(...)` in callback handlers, and for the `Reply` builder whenever a message has three or more options. All three paths end up going through the same API layer (see [API Reference](20_API.md#how-calls-flow)) and therefore benefit from the same transformers, throttling, and error handling.
