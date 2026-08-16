# 23. Troubleshooting and Pitfalls

This page collects the mistakes newcomers hit most, with what causes them and how to fix them. Keep it open while you write your first bot.

## "Nothing happens when I message the bot"

The most common newcomer experience, and it is almost always one of four things. Your handler never registered — check the decorator argument matches what you send (`Message(text="/start")` only matches exactly `/start`, never `/start@mybot` in groups; use `F.command("start")` for that). Your handler is registered in the wrong order — the first matching handler wins (see the priority table in [Handlers and the Context](03_HandlersAndContext.md#how-routing-decides)), so a broad `Message()` handler above your specific one eats the update. Your pattern regex is anchored wrong — `r"hello"` does not match `"hello world"` unless you use `search` semantics, which SwiftBot's `pattern` uses, but `r"^hello$"` would reject it. And finally, you forgot `await` or `async def` — a non-async handler or a missing `await ctx.reply(...)` either crashes silently inside the pool or never sends anything.

## "My inline button spins forever"

You did not answer the callback. Every `CallbackQuery` handler must end with `ctx.answer(...)` or `ctx.answer_callback(...)`. Telegram renders a spinning wheel on un-answered presses and records warnings for your bot. If the press should trigger visible feedback for everyone, use `show_alert=True`.

## "My callback handler never fires"

Callback routing matches `data` *exactly* by default — `data="buy"` does not match a press with `buy:42`. For payloads, use a regex: `CallbackQuery(pattern=r"^buy:")` or the type-safe `CallbackData` from [Typed Callback Data](08_CallbackData.md#why-this-matters).

## "MemoryStorage loses everything on restart"

That is what `MemoryStorage` is. Swap to `JSONFileStorage` or `RedisStorage` (see the backends table in [Storage and State](17_StorageAndState.md#the-statemanager)).

## "I ran webhook and polling at once" <a id="i-ran-webhook-and-polling-at-once"></a>

Telegram refuses, and when it does not, updates arrive twice. Pick one mode (see [Webhooks](22_Webhooks.md#webhooks-vs-polling)).

## "My token works locally but..." 

...then it is fine — but never commit it. Store it in an environment variable, never in source, docs, or screenshots. A leaked token means anyone can act as your bot; if that happens, rotate it immediately in [@BotFather](https://t.me/BotFather) via `/revoke`.

## Telegram limits that bite <a id="telegram-limits-that-bite"></a>

| Limit | Effect | Defence |
|---|---|---|
| 30 messages/second global (approx) | `TooManyRequests` | The pool honours `Retry-After` automatically; add `throttle` for headroom (see [Transformers](16_Transformers.md#built-in-transformers)) |
| Per-chat pacing | flooding one chat fails fastest | `throttle(per_chat=1.0)` |
| Callback data 64 bytes | truncation errors | `CallbackData` warns loudly; store big data in state, not payloads |
| Inline caption length | `MessageCaptionTooLong` | catch via [Exceptions](18_Exceptions.md#the-hierarchy) and trim |
| Poll interval minimums | `TooManyRequests` on get_updates | increase `timeout` (30–60s) on `run_polling` |
| Webhook redeliveries | duplicate updates | `plugins.idempotency` |

## Error signals in the logs

`Unauthorized` means your token is invalid or revoked — the token, not your code. `Forbidden` means the bot is blocked by that user or kicked from that chat — handle it with the "send safely" pattern in [Exceptions](18_Exceptions.md#the-send-safely-pattern). `MigrateToChat` means a group became a supergroup and your chat id changed — update your records to the new id from the exception. `UserNotFound` and `ChatNotFound` mean the target vanished — stop messaging it.

## The async trap

Handlers run concurrently in the pool, which means state in plain global variables is shared between handlers — use `ctx.set_state`/`get_state` for per-user data (see the backends table in [Storage and State](17_StorageAndState.md#the-statemanager)), and use `asyncio.Lock` for any shared structure. Similarly, blocking calls (heavy CPU work, synchronous HTTP) inside a handler stall the whole pool; offload them with `await asyncio.to_thread(...)` or an executor.

## When you are stuck

Read the routing priority table (part 3) top to bottom and find where your update should stop — that is almost always the answer to "why didn't X run". The typed exception hierarchy tells you exactly what Telegram complained about ([Exceptions](18_Exceptions.md#the-hierarchy)). And the offline test harness (part 21) reproduces any routing question in seconds without touching Telegram.
