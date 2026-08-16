# 9. Deep Linking

Deep linking lets a bot start with extra information baked into the link itself. When someone clicks `https://t.me/YourBot?start=ref_123`, Telegram opens your bot and delivers the payload `ref_123` as the argument of the `/start` command. This is how referral systems, share links, and group-invite flows are built.

## The two link styles

| Link | What the bot receives | Visibility |
|---|---|---|
| `https://t.me/YourBot?start=payload` | `/start payload` | Visible in group chats |
| `https://t.me/YourBot?startgroup=payload` | the payload, sent privately when the bot is added to a group | Hidden from the group |

Payloads are limited to 64 base64url characters — enough for short tokens and IDs.

## Building links

```python
from swiftbot.deep_linking import (
    create_start_link, create_start_link_custom,
    encode_payload, decode_payload, parse_start_param,
)

# Public start link:
link = create_start_link(bot_info, "ref_123")
# => "https://t.me/YourBot?start=ref_123"

# Private startgroup link — the payload never appears in the group chat:
link = create_start_link(bot_info, "secret", private=True)
# => "https://t.me/YourBot?startgroup=secret"

# bot_info accepts a username string, {"username": "..."}, or the
# cached get_me() result (it has a .username attribute).

# Custom URL template, e.g. tg:// links:
link = create_start_link_custom(bot_info, "payload",
    url_template="tg://resolve?domain={username}&start={payload}")
```

## Encoding arbitrary data

Plain payloads must be short text, but `encode_payload` / `decode_payload` safely pack small structured data into the 64-character base64 envelope:

```python
token = encode_payload({"user": 12345, "plan": "pro"})
payload = decode_payload(token)   # {"user": 12345, "plan": "pro"}
```

Both raise `DeepLinkError` (a `ValueError`) on garbage input, so always decode inside a try/except when the payload came from an untrusted link.

## Handling the start parameter

In the `/start` handler, the payload arrives as the command argument:

```python
from swiftbot import F
from swiftbot.types import Message
from swiftbot.deep_linking import parse_start_param

@bot.on(Message(filters=F.command("start")))
async def start(ctx):
    payload = parse_start_param(ctx.args)   # "ref_123", or None if plain /start
    if payload and payload.startswith("ref_"):
        await ctx.reply(f"Welcome! You were invited by {payload[4:]}")
    else:
        await ctx.reply("Welcome to the bot!")
```

`parse_start_param()` cleans the raw argument (it returns `None` when the user just typed `/start`).

## Full referral pattern

Putting it together, a working invite system looks like this:

```python
@bot.on(Message(filters=F.command("invite")))
async def invite(ctx):
    me = await bot.get_me()
    ref_token = encode_payload({"ref": str(ctx.user.id)})
    link = create_start_link(me, ref_token)
    await ctx.reply(f"Share this link: {link}")
```

When a friend starts the bot through that link, your `/start` handler decodes the token with `decode_payload` and credits the inviter. One caution from [Troubleshooting and Pitfalls](23_Troubleshooting.md): oversized payloads raise an error at encoding time, so keep payloads to IDs and short tokens rather than whole objects.
