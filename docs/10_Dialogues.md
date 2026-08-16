# 10. Dialogues and Wizards

Bots often need multi-step conversations: ask a name, then an email, then confirm. Plain handlers cannot do this on their own, because handlers are stateless — they forget everything between messages. `Dialogue` and `Wizard` give you state machines that remember where each user is in a conversation.

Both require a storage backend, because the state must survive between updates:

```python
from swiftbot import SwiftBot
from swiftbot.storage import MemoryStorage

bot = SwiftBot(token="YOUR_TOKEN", storage=MemoryStorage())
```

`MemoryStorage` is fine for development; use `JSONFileStorage` or `RedisStorage` in production (see [Storage and State](17_StorageAndState.md#choosing-a-backend)).

## Dialogue — state machines with transitions

A `Dialogue` is a set of named steps. Each step asks its question and returns a transition telling the dialogue where to go next. The dialogue middleware — registered automatically when you create the dialogue — checks every incoming update and runs the current step for users mid-conversation. **Active dialogues take priority over all other handlers** (see the routing table in [Handlers and the Context](03_HandlersAndContext.md)).

```python
dlg = bot.dialogue("onboarding")

@dlg.state("ask_name")
async def ask_name(ctx, prev=None):
    # prev is the answer from the previous step; None on entry
    if prev is not None:
        await ctx.set_state({"step": "ask_email", "name": prev})
        return dlg.next("ask_email")
    await ctx.reply("What's your name?")
    return dlg.next("ask_email")

@dlg.state("ask_email")
async def ask_email(ctx, prev=None):
    name = (await ctx.get_state()).get("name", "friend")
    await ctx.set_state({"step": "done", "name": name, "email": prev})
    return dlg.end()

@dlg.state("done")
async def done(ctx, prev=None):
    name = (await ctx.get_state()).get("name", "friend")
    await ctx.reply(f"Thanks {name}! Your email {prev} is saved.")
    return dlg.end()
```

The pieces, for a beginner:

`bot.dialogue("name")` creates the dialogue and registers it. Each `@dlg.state("x")` defines one step. A step returns one of two transition objects: `dlg.next("y")` advances to step `y`, and `dlg.end()` finishes the conversation and clears the user's state. The `prev` parameter carries the answer the user gave in the previous step, which is how steps validate and stash data. State is stored per user under keys such as `dialogue/<name>`, so different users never interfere with each other.

While the dialogue is active, any message from that user advances it — you do not need special handlers. If a user abandons the conversation, their state expires automatically via `state_ttl` on the bot constructor (see [Storage and State](17_StorageAndState.md#choosing-a-backend)).

## Wizard — step stacks

`Wizard` is the lower-level sibling: a stack of named steps with explicit control and optional hooks:

```python
from swiftbot.wizard import Wizard

survey = Wizard("survey", storage=bot.storage)

@survey.step("ask_name")
async def ask_name(ctx):
    await ctx.reply("Your name?")

@survey.step("ask_age")
async def ask_age(ctx):
    await ctx.reply("Your age?")

@survey.finish
async def finish(ctx, data):
    await ctx.reply(f"Recorded: {data}")
```

Beyond `@survey.step` and `@survey.finish`, a wizard accepts optional `@survey.on_enter` and `@survey.on_leave` hooks that run when a conversation starts and ends. Driving a wizard is manual: `bot.wizard("survey")` returns a `WizardAccessor` with `current(name)`, `step(name, step_name)`, and `exit(name)` methods. This explicit control suits admin-triggered flows and scripted sequences; for ordinary user-facing conversations, `Dialogue` is the easier choice.

## Which should you use?

Use `Dialogue` for question-and-answer flows driven by the user — its transitions and the automatic priority routing cover the common case completely. Reach for `Wizard` when you need to push a user through steps programmatically or inspect and manipulate the step stack from outside the conversation.
