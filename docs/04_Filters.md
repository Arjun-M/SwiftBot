# 4. Filters

Filters decide whether an update matches a handler. SwiftBot's filter system is built on a simple algebra: filters combine with `&` (and), `|` (or), and `~` (not), exactly like sets in mathematics. This page covers the `F` shortcut object, the preset filters, and how to build your own.

## The `F` algebra

```python
from swiftbot import F
from swiftbot.types import Message

cond = F.text & F.private & ~F.reply

@bot.on(Message(filters=cond))
async def handle(ctx):
    await ctx.reply("Got it!")
```

The expression above matches a message that has text, arrives in a private chat, and is not a reply to another message. Combine as many conditions as you like; parentheses control precedence just as in ordinary Python.

## Presets

These presets are the common building blocks:

| Preset | Meaning |
|---|---|
| `F.text` | message has text |
| `F.private`, `F.group`, `F.supergroup`, `F.channel` | chat type |
| `F.forwarded` | the message is forwarded |
| `F.reply` | the message is a reply to another message |
| `F.photo`, `F.video`, `F.audio`, `F.document`, `F.voice`, `F.sticker`, `F.animation`, `F.video_note`, `F.location`, `F.contact` | the message's media type |
| `F.media` | any media message |

## Parameterised filters

Some filters need arguments, and `F` offers short-cut methods for them:

```python
F.command("start", "help")       # matches /start and /help
F.regex(r"^vip:")                # regex match on the message text
F.user(12345, 67890)             # only these Telegram user ids
F.chat(-1001234567890)           # only this chat (negative ids are groups)
F.custom(lambda msg: ...)        # your own function returning True/False
```

`F.command` deserves a special mention: it correctly handles commands written with the bot username attached, such as `/start@mybot`, which is how commands arrive in group chats.

## The `Filters` class

`Filters` exposes the same presets as plain classes for people who prefer explicit construction, and every `F` preset is an instance of one of them:

```python
from swiftbot import Filters

cond = Filters.private() & (Filters.photo() | Filters.video())
```

## Pattern matching with regex

For text handlers, `Message(pattern=...)` runs a regular expression against the message text, and the match object is reachable in the handler so you can extract groups without re-parsing:

```python
@bot.on(Message(pattern=r"^/setname (.+)"))
async def setname(ctx):
    name = ctx._match.group(1)
    await ctx.reply(f"Set name to {name}")
```

## Writing custom filters

A filter is any callable that returns a boolean (or a truthy value) given a message object. The `CustomFilter` class wraps one for you:

```python
from swiftbot.filters import CustomFilter

def is_vip(msg):
    return getattr(msg, "from_user", None) and msg.from_user.id in VIP_IDS

vip_only = CustomFilter(is_vip)
```

Because `F.custom(...)` accepts the same callable, `F.custom(is_vip)` is the one-line equivalent.
