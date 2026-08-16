# 11. Middleware

Middleware is code that runs **around** every handler — on the way in, before your handler, and on the way out, after it returns. Think of it as a checkpoint that applies to many handlers at once, so you never repeat logging, auth, or rate-limiting code inside each one.

## Writing middleware <a id="writing-middleware"></a>

Subclass `Middleware` and implement `on_update`:

```python
from swiftbot.middleware import Middleware

class Tracer(Middleware):
    async def on_update(self, ctx, next_handler):
        print("before:", ctx.text)
        await next_handler()     # run the handler (and further middleware)
        print("after")

bot.use(Tracer())
```

Calling `await next_handler()` is what actually runs the handler — and any middleware registered after yours. Skip that call, and the handler never executes: that is how auth rejections and spam blocking short-circuit the chain. The order you call `bot.use()` in is the order middleware runs in, with the first registered being the outermost.

## Built-in middleware

| Middleware | What it does |
|---|---|
| `Logger` | Logs every update and response with a configurable format (`"text"`, `"json"`, `"colored"`) and destination |
| `Auth` | Access control via `whitelist`, `blacklist`, and a custom async `auth_fn` |
| `RateLimiter` | Per-user rate limiting with automatic cache cleanup |
| `AnalyticsCollector` | Tracks sessions, command usage, and errors; query with `.get_stats()` and `.get_current_metrics()` |

```python
from swiftbot.middleware import Logger, Auth, RateLimiter, AnalyticsCollector

bot.use(Logger(format="colored"))
bot.use(Auth(whitelist=[12345]))                  # only this user id gets through
bot.use(RateLimiter(max_calls=20, window=60))
bot.use(AnalyticsCollector())
```

`Auth` is the most configurable of the four: a whitelist alone accepts only listed user ids, a blacklist alone blocks listed ids, and `auth_fn` accepts any async function of the context that returns a boolean.

## Where middleware fits

Middleware from this page is **global** — it runs for every update. For middleware that should run only on part of your traffic, see [Scopes](13_Scopes.md). For middleware bundled into modules with their own error handlers, see [Composer](14_Composer.md). And for a curated set of production-ready middleware, see the plugins in [Plugins](12_Plugins.md).

## Writing correct middleware

Three rules keep middleware from misbehaving. First, always `await next_handler()` when you want the update to continue — forgetting it silently drops the update. Second, wrap `next_handler()` in try/except only when you intend to handle the error; otherwise let it bubble to the centralized handler (see [Exceptions](18_Exceptions.md#the-hierarchy)). Third, keep middleware fast: it runs for every update, so heavy work inside it slows the whole bot.
