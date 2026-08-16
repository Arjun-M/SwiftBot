# 14. Composer

As a bot grows, one flat list of `bot.use(...)` calls becomes hard to reason about. A `Composer` bundles middleware into a named unit that can be nested and given its own error handler — module boundaries for middleware.

## Bundling middleware <a id="bundling-middleware"></a>

```python
from swiftbot.composer import Composer
from swiftbot.middleware import Logger

admin = Composer(Logger(), admin_auth_middleware)
todo = Composer()
todo.use(list_middleware)
```

A `Composer` is constructed with middleware or filled with `.use(...)` calls afterwards — both styles are equivalent. The real power is the error boundary: each bundle can catch its own errors instead of letting them bubble to a single global handler.

```python
admin.catch(lambda ctx, e: ctx.reply("Admin area error."))

todo.on_error = lambda ctx, e: log_error(e)
```

Use `.catch(fn)` for a handler that may reply to the user, and `.on_error` for side-effect handling such as logging. Errors inside the bundle's middleware and handlers reach the bundle's catcher; errors outside it do not.

## Nesting and installing

Composers nest freely, and the bot flattens them on install while preserving each bundle's catch boundary:

```python
root = Composer(Logger())
root.use(admin, todo)            # bundles inside a bundle
root.use(main_middleware)

root.install_on(bot)             # install everything onto the SwiftBot client
```

A `Composer` can also be passed directly to `bot.use()` — the client flattens nested bundles automatically:

```python
bot.use(admin, todo)
```

## Why this helps

In a large bot, the admin area, the user-facing flow, and the analytics pipeline each want different middleware and different failure behaviour. Composers let each area own its boundary: an error in the admin area is answered by the admin area, logged by the analytics bundle, and never mixes with the user-facing flow. Small bots can skip this page entirely; `bot.use(...)` with global middleware is all they need.
