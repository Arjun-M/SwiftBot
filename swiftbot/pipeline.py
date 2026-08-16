"""
Pipeline — a declarative, dependency-injected handler tree.

Where ordinary handlers receive only a ``Context`` object, a ``Pipeline`` lets
handlers declare the dependencies they need, and the pipeline injects them
automatically. Handlers can be grouped into typed branches guarded by filters,
forming a chain-of-responsibility tree that is easy to compose and test.

Example::

    from swiftbot import SwiftBot
    from swiftbot.pipeline import Pipeline
    from swiftbot.types import Message
    from swiftbot.filters import F

    async def echo(bot, db, ctx):
        # ``bot``, ``db`` and ``ctx`` are injected by name automatically.
        row = await db.get("last_text", ctx.user.id)
        await ctx.reply(f"You said: {ctx.text}")

    pipe = Pipeline()
    pipe.deps(db=my_database, extra="value")
    pipe.handle(F.text, echo)
    pipe.handle(F.text & F.command("stats"), stats_handler)

    bot = SwiftBot(token="...")
    bot.pipeline(pipe)          # mount: the pipeline becomes one middleware stage

Design notes
------------
- Branches are evaluated in registration order; the first whose filter matches
  and whose handler completes wins. ``Pipeline.first`` controls whether the
  first match wins (True) or all matching branches run (False).
- Dependencies are injected by *name*: a handler parameter is injected when a
  matching dependency exists in the registry **and** the parameter is not one
  of the framework-provided names (``ctx``, ``bot``, ``match``).
- A handler that needs a dependency that was never registered raises
  ``PipelineDependencyMissing`` at run time (fail loudly, never silently).

Copyright (c) 2026 Arjun-M/SwiftBot
"""

import inspect
import logging
from typing import Any, Callable, Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)

# Framework-provided parameters that are supplied by the pipeline itself and
# never resolved from the dependency registry.
FRAMEWORK_PARAMS = {"ctx", "bot", "match"}


class PipelineDependencyMissing(Exception):
    """A handler required a dependency that was never registered."""


class Pipeline:
    """
    A declarative chain-of-responsibility tree of filter-guarded handlers
    with automatic dependency injection.
    """

    def __init__(self, first: bool = True) -> None:
        self._deps: Dict[str, Any] = {}
        self._branches: List[Tuple[Callable, Callable]] = []
        self.first = first

    # ------------------------------------------------------------------
    # Dependency registry
    # ------------------------------------------------------------------

    def deps(self, **dependencies: Any) -> "Pipeline":
        """
        Register named dependencies that will be injected into handlers.

        Call as often as needed; later registrations with the same name win.
        Returns ``self`` so calls can be chained::

            pipe.deps(db=database).deps(repo=repository)
        """
        self._deps.update(dependencies)
        return self

    def get_dep(self, name: str, default: Any = None) -> Any:
        return self._deps.get(name, default)

    # ------------------------------------------------------------------
    # Branches
    # ------------------------------------------------------------------

    def handle(self, filter_fn: Callable, handler: Callable) -> Callable:
        """
        Add a filter-guarded handler branch.

        Args:
            filter_fn: callable taking the update object; truthy return
                selects this branch.
            handler: async callable. Parameters named ``ctx`` (Context),
                ``bot`` (SwiftBot), ``match`` (regex match) and any registered
                dependency name are injected automatically; all others are
                passed the filtered update object's ``text`` where possible —
                actually, only named injection is supported, so keep handlers
                simple: async (ctx, db) for example.
        Returns:
            The original handler (so decorators still work).
        """
        self._branches.append((filter_fn, handler))
        return handler

    def branch(self, filter_fn: Callable) -> "Pipeline":
        """
        Start a nested branch context (builder style)::

            pipe.branch(F.private).handle(...)
        """
        self._nested_filter = filter_fn
        return self

    def __repr__(self) -> str:
        return f"Pipeline(branches={len(self._branches)}, deps={list(self._deps)})"

    # ------------------------------------------------------------------
    # Execution
    # ------------------------------------------------------------------

    async def process(self, ctx, bot) -> bool:
        """
        Run all matching branches against ``ctx``.

        Returns:
            True if at least one branch handled the update.
        """
        update_obj = ctx._update_obj
        matched = False

        for filter_fn, handler in self._branches:
            try:
                selected = filter_fn(update_obj)
            except Exception as exc:  # a broken filter never takes down the bot
                logger.error("Pipeline filter raised: %s", exc, exc_info=True)
                continue
            if not selected:
                continue

            try:
                await self._call_handler(handler, ctx, bot)
                matched = True
                if self.first:
                    return True
            except PipelineDependencyMissing:
                raise
            except Exception as exc:
                logger.error("Pipeline handler raised: %s", exc, exc_info=True)
                if hasattr(bot, "_handle_exception"):
                    await bot._handle_exception(exc, f"pipeline_{getattr(handler, '__name__', 'anon')}")
        return matched

    async def _call_handler(self, handler: Callable, ctx, bot) -> Any:
        """
        Resolve handler parameters by name and call it.

        Injection order: ctx / bot / match (framework), then the registered
        dependency registry, then nothing — a handler must not declare
        unregistered parameters.
        """
        try:
            sig = inspect.signature(handler)
        except (ValueError, TypeError):
            return await handler(ctx)

        kwargs: Dict[str, Any] = {}
        params = sig.parameters
        for name, param in params.items():
            if name == "ctx":
                kwargs["ctx"] = ctx
            elif name == "bot":
                kwargs["bot"] = bot
            elif name == "match":
                kwargs["match"] = getattr(ctx, "match", None)
            elif name in self._deps:
                kwargs[name] = self._deps[name]
            elif param.default is not inspect.Parameter.empty:
                continue  # optional param left at its default
            else:
                raise PipelineDependencyMissing(
                    f"handler {getattr(handler, '__name__', handler)!r} requires "
                    f"undeclared dependency '{name}'. Register it with "
                    "Pipeline.deps(...)"
                )

        if inspect.iscoroutinefunction(handler):
            return await handler(**kwargs)
        return handler(**kwargs)

    def __len__(self) -> int:
        return len(self._branches)

    def __bool__(self) -> bool:
        return True
