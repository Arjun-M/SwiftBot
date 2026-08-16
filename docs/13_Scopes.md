# 13. Scopes

Global middleware registered with `bot.use(...)` runs for **every** update. A scope attaches middleware to a slice of traffic instead — moderation middleware only in groups, a slow analytics path only for private chats, rate limiting only for non-admins.

## Creating a scope

```python
from swiftbot import F
from swiftbot import plugins
from swiftbot.scopes import Scope

bot.scope(F.private).use(plugins.session_limiter(min_interval=1.0))
```

`bot.scope(predicate)` returns a `Scope` — a middleware chain guarded by a predicate over the raw update dictionary. Call `.use(...)` on it to attach middleware, exactly as on the bot itself. The predicate can be any callable returning a boolean:

```python
def is_group(upd):
    msg = upd.get("message") or {}
    return msg.get("chat", {}).get("type") in ("group", "supergroup")

bot.scope(is_group).use(heavy_mod_middleware)
```

`F` filters work as predicates too, which is the idiomatic choice — they are shorter and read naturally, as in `F.private` above.

## Composition

Scopes compose freely. The same middleware can live in several scopes, and a scope can hold a `Composer` bundle (see [Composer](14_Composer.md#bundling-middleware)) with its own error boundary:

```python
from swiftbot.composer import Composer

bot.scope(F.group).use(Composer(Logger(), moderation_bundle))
```

In the routing order from [Handlers and the Context](03_HandlersAndContext.md#how-routing-decides), scoped middleware runs after active dialogues and before pipelines — so a scope can still guard pipeline handlers and fallback behaviour.

## When to use scopes

Reach for scopes whenever a piece of middleware does not belong to every update. Typical cases: expensive logging only on certain chats, admin-only middleware filtered by user id, chat-type-specific rate limits, and per-feature bundles in a large bot where global middleware would touch traffic it has no business with.
