# 12. Plugins

Plugins are ready-made middleware for the problems most bots face in production: flooding, double deliveries, and unwanted users. SwiftBot ships four official plugins, all implemented as plain middleware so they compose with everything in [Middleware](11_Middleware.md).

## The four plugins <a id="the-four-plugins"></a>

```python
from swiftbot import plugins

bot.use(plugins.spam_deflector(threshold=10, window=60))
bot.use(plugins.session_limiter(min_interval=2.0))
bot.use(plugins.idempotency(window=5.0))
bot.use(plugins.whitelist(user_ids={12345, 67890}))
```

| Plugin | Behaviour |
|---|---|
| `spam_deflector(threshold, window)` | Counts a user's messages per window; floods are dropped silently before handlers see them |
| `session_limiter(min_interval)` | Enforces a minimum interval between a user's accepted messages — it throttles by delaying, never blocking |
| `idempotency(window)` | Hashes updates; identical duplicates arriving within the window are ignored. Essential for webhook retries and double-taps |
| `whitelist(user_ids=, chat_ids=)` | Drops updates from any user or chat not listed. The strictest firewall available |

## Choosing what you need

A personal bot for a few friends rarely needs any of these. `idempotency` is the one nearly everyone should add the moment they switch to webhooks (see [Webhooks](22_Webhooks.md#registering-the-webhook)), because Telegram retries webhook deliveries and a user can double-tap a button. `spam_deflector` and `session_limiter` matter for public bots that receive bursts — giveaways, announcements, groups. `whitelist` is for bots that should never talk to strangers, such as internal tools.

## Composing with other middleware

Because plugins are plain middleware, order matters in the usual way (see [Middleware](11_Middleware.md#writing-middleware)): first registered is outermost. A sensible default stack for a public bot is:

```python
bot.use(plugins.whitelist(user_ids=ADMIN_IDS))          # firewall first
bot.use(plugins.spam_deflector(threshold=10, window=60))
bot.use(Logger(format="colored"))
```

For traffic-sliced application — say, rate limiting only private chats — attach plugins to scopes instead, as shown in [Scopes](13_Scopes.md).
