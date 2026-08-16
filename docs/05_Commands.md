# 5. Commands

Telegram commands are messages beginning with `/`, such as `/start` or `/score Alice 10`. SwiftBot gives you two ways to handle them: lightweight pattern matching for simple bots, and the declarative `BotCommands` system for bots where commands deserve real argument parsing and documentation.

## Simple command handling

The quickest route is a filter on the command name. `CommandFilter` matches the command and automatically skips the bot username when commands arrive in groups as `/start@mybot`:

```python
from swiftbot import F
from swiftbot.types import Message

@bot.on(Message(filters=F.command("start")))
async def start(ctx):
    await ctx.reply("Welcome!")

@bot.on(Message(filters=F.command("help")))
async def help_cmd(ctx):
    await ctx.reply("Commands: /start, /help, /score <name> <points>")
```

Regex patterns work as well for commands that carry free-form arguments, as shown in [Filters](04_Filters.md) — you split `ctx.text` by hand when the arguments are simple.

## BotCommands — declarative commands <a id="botcommands-declarative-commands"></a>

For anything more involved, SwiftBot ships a feature most Python bot frameworks lack: commands as a **declaration**. You describe each command once, and argument parsing, validation, and `/help` generation follow automatically.

```python
from swiftbot.commands import BotCommands, CommandsMiddleware

class Cmd(BotCommands):
    start = "start your session"
    name = "greet someone | /name <first> <last>"
    score = "record a score | /score <name> <points:int>"
```

The syntax reads naturally. The value is `"description | /cmd <arg> <arg2>"` — everything after `|` is the usage line. Angle brackets declare typed arguments: types default to `str`, and appending `:int`, `:float`, or any callable parser casts the argument automatically. Wire it up with the middleware:

```python
bot.use(CommandsMiddleware(Cmd))

@bot.on(Message(filters=Cmd.start))
async def start(ctx):
    await ctx.reply("Session started. Try /help")

@bot.on(Message(filters=Cmd.name))
async def name(ctx):
    first, last = ctx.command.args
    await ctx.reply(f"Hello {first} {last}!")

@bot.on(Message(filters=Cmd.score))
async def score(ctx):
    name, points = ctx.command.args
    # points is already an int
    await ctx.reply(f"{name}: {points}")
```

Every command name on the class becomes a filter you can pass to `Message(filters=...)`, and `ctx.command.args` carries the parsed, typed arguments when the command router matched. `Cmd.parse("/score Alice 10")` also works outside handlers, returning a `ParsedCommand` or `None` — handy for custom routing.

What happens on bad input: missing or malformed arguments raise a `ValidationError`, and the `CommandsMiddleware` reports the usage line back to the user instead of letting your handler crash. You never hand-parse `sys.argv`-style strings again.

## Unknown-command handling

When a message starts with `/` but matches no route at all, `@bot.on_unknown_command` fires (see the routing priority table in [Handlers and the Context](03_HandlersAndContext.md#how-routing-decides)). Combined with `BotCommands` this gives you a polite "unknown command, try /help" behaviour for free.
