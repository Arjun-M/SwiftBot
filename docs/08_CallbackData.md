# 8. Typed Callback Data

Telegram limits inline button payloads to 64 bytes, and a raw payload is just a string. Passing structured information — an action name plus an item id, for example — as hand-built strings is fragile: nothing stops two buttons from colliding, and a malformed payload fails silently. `CallbackData` solves both problems with typed, namespaced packing.

## Defining a callback schema

```python
from swiftbot import CallbackData, Button
from swiftbot.types import Message, CallbackQuery

buy = CallbackData("buy", str, int)   # prefix "buy", then a string and an int
```

A `CallbackData` factory declares its prefix and the types of the values it carries. Supported types are `str`, `int`, `float`, `bool`, and `bytes`.

## Packing buttons

`pack()` turns typed values into a single URL-safe string:

```python
data = buy.pack("premium", 42)   # -> "buy:s:premium:i:42"
```

The format is `prefix:<type-tag>:<value>:<type-tag>:<value>`. Type tags (`s`, `i`, `f`, `b`, `y`) are internal — you never need to write them by hand. Use `pack()` wherever you build an inline button:

```python
@bot.on(Message(text="/shop"))
async def shop(ctx):
    kb = InlineKeyboard().row(Button.inline("Buy premium", buy.pack("premium", 42)))
    await ctx.reply("Shop:", reply_markup=kb.build())
```

## Unpacking in the handler

```python
@bot.on(CallbackQuery(pattern=buy.pattern()))
async def on_buy(ctx):
    item, item_id = buy.unpack(ctx.callback_query.data)
    # item == "premium", item_id == 42 — already the right types
    await ctx.answer(f"Buying {item} #{item_id}")
```

`unpack()` returns your values with the declared types restored, and `buy.pattern()` gives you a regex filter for the router so the handler only fires for valid payloads.

## Why this matters <a id="why-this-matters"></a>

Three guarantees make `CallbackData` worth using. **No collisions:** the prefix namespaces the payload, so two different factories never decode each other's data. **Typed round-trips:** `str`, `int`, `float`, `bool`, and `bytes` all survive the trip through Telegram exactly. **Loud failures:** `CallbackDataInvalid` is raised on corrupt or wrong-prefix data, so a bad click can never silently mis-parse — you catch it explicitly instead.

If you prefer exact-style matching without a regex, `buy.filter()` returns a filter-like matcher for the router.

One practical note: payloads are bounded by Telegram's 64 bytes. For short IDs and tokens this is plenty; for larger data, store the data in your storage backend (see [Storage and State](17_StorageAndState.md#the-statemanager)) and put only a lookup key in the callback.
