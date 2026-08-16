"""
BotCommands — declarative, strongly-typed command specifications.

No Python Telegram framework ships a declarative command language: commands
are matched by loose text filters and arguments are parsed by hand inside each
handler. This module turns command handling into a declaration: args parse themselves and a correct ``/help`` is generated from the spec. Brings the
Python — commands are declared once as attributes on a class, then parsed,
validated and documented automatically.

Example::

    from swiftbot.commands import BotCommands
    from swiftbot import SwiftBot
    from swiftbot.middleware_commands import CommandsMiddleware

    class Cmd(BotCommands):
        start = "start your session"
        name = "greet someone | /name <first> <last>"
        score = "record a score | /score <name> <points:int>"

    bot = SwiftBot(token="...")
    bot.use(CommandsMiddleware(Cmd))

    @bot.on(Message(filters=Cmd.start))
    async def start(ctx):
        await ctx.reply(f"Hi {ctx.user.first_name}! Type /help")

    @bot.on(Message(filters=Cmd.name))
    async def name(ctx):
        first, last = ctx.command.args  # typed args
        await ctx.reply(f"Hello {first} {last}!")

    @bot.on(Message(filters=Cmd.score))
    async def score(ctx):
        name, points = ctx.command.args
        # points is already an int thanks to the <name:int> spec

Design notes
------------
- A command spec is ``name = "description | /name <first> <last:int>"``.
  Everything after ``|`` is the usage line; ``<arg:type>`` entries declare
  typed arguments (type defaults to str; ``int``, ``float``, ``bool``, or any
  callable parser).
- ``Cmd.parse("/name Arjun M", bot_username=None)`` returns a
  ``ParsedCommand`` or None.
- ``Cmd.help_text()`` returns a generated /help page.
- ``CommandsMiddleware`` populates ``ctx.command`` so handlers get typed args.

Copyright (c) 2026 Arjun-M/SwiftBot
"""

import logging
import re
from typing import Any, Callable, Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)

_USAGE_RE = re.compile(r"\|\s*(/.+)$")
_ARG_RE = re.compile(r"<([^>:]+)(?::([^>]+))?>")

# Built-in type parsers.
_TYPE_PARSERS: Dict[str, Callable[[str], Any]] = {
    "str": str,
    "int": int,
    "float": float,
    "bool": lambda s: s.strip().lower() not in {"0", "false", "no"},
}


class ParsedCommand:
    """Result of parsing a message against a BotCommands spec."""

    def __init__(self, name: str, raw_text: str, spec: str) -> None:
        self.name = name
        self.raw_text = raw_text
        self.spec = spec
        self.usage_line = self._extract_usage(spec)
        self.arg_specs = self._extract_arg_specs(self.usage_line)
        self.args: List[Any] = []
        self.description = self._extract_description(spec)

    @staticmethod
    def _extract_usage(spec: str) -> str:
        m = _USAGE_RE.search(spec)
        return m.group(1).strip() if m else ""

    @staticmethod
    def _extract_description(spec: str) -> str:
        return _USAGE_RE.split(spec)[0].strip()

    @staticmethod
    def _extract_arg_specs(usage_line: str) -> List[Tuple[str, Callable]]:
        out = []
        for name, type_name in _ARG_RE.findall(usage_line):
            parser: Callable = _TYPE_PARSERS.get((type_name or "str").strip(), str)
            out.append((name.strip(), parser))
        return out

    def parse_args(self, argv: List[str]) -> bool:
        """Parse positional argument strings according to arg specs.

        Returns True when the argument count matches the spec.
        """
        self.args = []
        for spec_name, parser in self.arg_specs:
            if len(argv) <= len(self.args):
                return False
            try:
                self.args.append(parser(argv[len(self.args)]))
            except (ValueError, TypeError) as exc:
                logger.warning("Bad argument for %s (%s): %s", self.name, spec_name, exc)
                return False
        return True


class BotCommandsMeta(type):
    """Metaclass that collects command specs and adds parsing helpers."""

    def __init__(cls, name: str, bases, namespace) -> None:
        super().__init__(name, bases, namespace)
        # Move string specs out of the class __dict__ into ``_commands`` so
        # that names like ``name`` or ``help`` never collide with built-in
        # ``type`` attributes (``type`` always finds class-dict entries
        # before ``__getattr__`` — hiding the spec behind a private name
        # sidesteps the collision entirely).
        commands: Dict[str, str] = {}
        for attr in list(namespace):
            if attr.startswith("_"):
                continue
            if not isinstance(namespace[attr], str):
                continue
            commands[attr] = namespace[attr]
            # Remove the spec from the class __dict__: ``type`` resolves
            # class-dict entries before ``__getattr__``, so a command named
            # ``name``/``help`` would otherwise be permanently shadowed.
            try:
                delattr(cls, attr)
            except AttributeError:
                pass
        cls._commands: Dict[str, str] = commands  # type: ignore[assignment]
        cls._filter_cache: Dict[str, Any] = {}

    def __getattr__(cls, item):  # type: ignore[override]
        """Lazy access: ``Cmd.start`` returns a callable filter + spec."""
        commands = object.__getattribute__(cls, "_commands")
        if item in commands:
            return _FilterOrSpec(cls, item, commands[item])
        raise AttributeError(item)

    def __setattr__(cls, name, value):  # type: ignore[override]
        """
        Keep command specs discoverable on the class body even when the
        attribute name collides with a built-in (``Cmd.name``, ``Cmd.help``).
        Without this, ``Cmd.name = "..."`` would fall back to type.__setattr__
        and be lost to ``__getattr__`` lookups of the same name.
        """
        if name not in {"_commands", "_filter_cache"} and not name.startswith("_") and isinstance(value, str):
            cls._commands[name] = value
        type.__setattr__(cls, name, value)

    def __contains__(cls, item) -> bool:
        return item in object.__getattribute__(cls, "_commands")

    def __iter__(cls):
        return iter(object.__getattribute__(cls, "_commands"))

    def __len__(cls) -> int:
        return len(object.__getattribute__(cls, "_commands"))

    # ------------------------------------------------------------------
    # Parsing
    # ------------------------------------------------------------------

    def parse(cls, text: str, bot_username: Optional[str] = None) -> Optional[ParsedCommand]:
        """
        Parse ``/cmd arg1 arg2`` text against this spec class.

        Args:
            text: incoming message text (may include other content).
            bot_username: if given, only ``/cmd@bot`` or ``/cmd`` addressed
                to this bot match.
        Returns:
            ``ParsedCommand`` with typed ``.args``, or None.
        """
        if not text:
            return None
        text = text.strip()
        for name, spec in cls._commands.items():  # type: ignore[attr-defined]
            usage_line = ParsedCommand._extract_usage(spec)
            n_args = len(_ARG_RE.findall(usage_line))
            pattern = re.compile(
                r"(?:^|\s)" + re.escape("/" + name)
                + (r"(?:@" + re.escape(bot_username or r"[\w]+") + r")?" if bot_username else r"(?:@[\w]+)?")
                + r"(?=\s|$)"
            )
            m = pattern.search(text)
            if not m:
                continue
            remainder = text[m.end():].strip()
            argv = remainder.split() if remainder else []
            parsed = ParsedCommand(name, text, spec)
            if n_args > 0:
                if len(argv) != n_args:
                    continue
                if not parsed.parse_args(argv):
                    continue
            elif argv:
                # command exists but user supplied arguments the spec has none for
                # -> still match, args stay empty (permissive by default)
                pass
            return parsed
        return None

    def help_text(cls, title: str = "Help", show_usage: bool = True) -> str:
        """Generate a /help page listing all commands and descriptions."""
        commands = object.__getattribute__(cls, "_commands")
        if not commands:
            return title
        lines = [f"*{title}*"]
        for name, spec in sorted(commands.items()):
            usage_line = ParsedCommand._extract_usage(spec)
            desc = ParsedCommand._extract_description(spec)
            if show_usage and usage_line:
                lines.append(f"``{usage_line}`` — {desc}")
            else:
                lines.append(f"``/{name}`` — {desc}")
        return "\n".join(lines)


class _FilterOrSpec:
    """Dual-purpose attribute: works as a filter callable and exposes the spec string."""

    def __init__(self, owner_cls, name: str, spec: str) -> None:
        self._owner = owner_cls
        self.name = name
        self.spec = spec

    def __call__(self, update_obj) -> bool:
        """Filter callable: matches when the update's text is this command."""
        text = getattr(update_obj, "text", None)
        return bool(text) and self._owner.parse(text) is not None and \
            self._owner.parse(text).name == self.name

    def __str__(self) -> str:
        return self.spec

    def __repr__(self) -> str:
        return f"<Command {self.name}>"


class BotCommands(metaclass=BotCommandsMeta):
    """
    Declare bot commands as class attributes::

        class Cmd(BotCommands):
            start = "start the bot"
            name = "greet someone | /name <first> <last>"
    """
    pass


class CommandsMiddleware:
    """
    Populates ``ctx.command`` with the parsed ``ParsedCommand`` whenever the
    update text matches any command in the spec. Install once with
    ``bot.use(CommandsMiddleware(Cmd))``.
    """

    def __init__(self, spec_cls) -> None:
        self.spec_cls = spec_cls

    async def on_update(self, ctx, next_handler):
        text = getattr(ctx, "text", None)
        if text:
            parsed = self.spec_cls.parse(text)
            ctx.command = parsed  # None when no match — handlers check ctx.command
            # v1.6: unrecognized ``/command`` messages go to the bot's
            # ``on_unknown_command`` handler when one is registered.
            if text.startswith("/") and parsed is None:
                bot = getattr(ctx, "bot", None)
                unknown = getattr(bot, "_unknown_command", None)
                if unknown is not None:
                    try:
                        await unknown(ctx)
                        return  # the unknown-command handler handled it
                    except Exception:
                        raise
        await next_handler()
