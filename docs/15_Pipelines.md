# 15. Pipelines

A `Pipeline` is SwiftBot's declarative handler tree: a set of **branches**, each guarded by a filter, where the first matching branch handles the update. Its distinctive feature is **dependency injection** — handlers declare the services they need by parameter name, and the pipeline supplies them automatically.

## Building a pipeline

```python
from swiftbot import F
from swiftbot.pipeline import Pipeline

pipe = bot.pipeline()

pipe.deps(db="fake_db", config={"max": 5})   # register dependencies

@pipe.handle(F.private)                      # branch: any private message
async def greet(ctx, db, config):            # db and config injected by name
    await ctx.reply(f"Hi! db={db}, max={config['max']}")

@pipe.handle(F.photo)                        # another branch
async def photo_handler(ctx):
    await ctx.reply("Nice photo!")
```

`pipe.handle(filter, handler)` adds a branch. The filter receives the raw update object; a truthy return selects the branch. The builder-style equivalent is `pipe.branch(F.private).handle(...)`.

## Dependency injection rules

Handler parameters are injected automatically when their name is one of the following: `ctx` (the context), `bot` (the client), `match` (the filter match, where applicable), or any name registered through `pipe.deps(...)`. Anything else raises `PipelineDependencyMissing` at handler-call time — typos are loud and obvious rather than silently receiving `None`.

Register dependencies once, usually at startup:

```python
pipe.deps(database=my_db, settings=my_config, cache=my_cache)
```

Every branch in the pipeline can then request any of them by name, which removes manual service passing as the handler count grows.

## Where pipelines sit

In the routing order from [Handlers and the Context](03_HandlersAndContext.md#how-routing-decides), pipelines run after dialogues and scopes, and before the decorator handlers. The first matching branch handles the update; if no branch matches, processing continues down the priority list.

## When to reach for pipelines

Pipelines suit larger bots where many handlers share services — a database, configuration, a cache — and you want the wiring checked at runtime rather than hand-plumbed through every function. For a small bot with a handful of handlers, plain `@bot.on(...)` decorators are simpler and cover everything.
