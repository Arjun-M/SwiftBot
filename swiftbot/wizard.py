"""
Wizard — typed multi-step conversation dialogs.

teloxide (Rust) models conversations as an enum of states, each carrying its
accumulated data, and dispatches to a handler per state. The Python world
approximates this with ad-hoc FSM flags and state data dicts. This module
gives SwiftBot a proper wizard abstraction: steps are declared functions,
collected answers accumulate into a typed result dict, and the whole thing is
storage-agnostic (any ``BaseStorage`` — memory, JSON file, Redis).

Example::

    from swiftbot import SwiftBot
    from swiftbot.wizard import Wizard, wizard_step
    from swiftbot.types import Message
    from swiftbot.filters import F

    bot = SwiftBot(token="...", storage=JSONFileStorage("state.json"))

    wiz = Wizard("survey", storage=bot.storage)

    @wiz.step("name")
    async def ask_name(ctx):
        await ctx.reply("What's your name?")

    @wiz.step("age")
    async def ask_age(ctx):
        await ctx.reply("How old are you?")

    @wiz.finish
    async def done(ctx, data):
        await ctx.reply(f"Got it, {data['name']}, age {data['age']}")

    # Entry point — starts the wizard on /survey
    @bot.on(Message(filters=F.command("survey")))
    async def start_survey(ctx):
        await wiz.enter(ctx)

    # Every message advances the current step
    @bot.on(Message(filters=F.text & ~F.command("survey")))
    async def advance(ctx):
        if await wiz.step_forward(ctx, ctx.text):
            return
        await ctx.reply("Send /survey to begin")

The wizard keeps per-conversation state under a key like
``"wizard:survey:chat:{chat_id}"``: ``{"step": "name", "data": {...}}``.

Copyright (c) 2026 Arjun-M/SwiftBot
"""

import asyncio
import logging
from typing import Any, Callable, Dict, Optional

logger = logging.getLogger(__name__)


class Wizard:
    """
    A multi-step conversation wizard bound to a ``BaseStorage`` backend.
    """

    def __init__(self, name: str, storage: Any) -> None:
        """
        Args:
            name: unique wizard identifier (used in storage keys).
            storage: any ``BaseStorage`` instance — ``MemoryStorage``,
                ``JSONFileStorage``, ``RedisStorage`` ...
        """
        self.name = name
        self._storage = storage
        self._steps: Dict[str, Callable] = {}
        self._step_order: list = []
        self._finish: Optional[Callable] = None
        self._enter: Optional[Callable] = None
        self._leave: Optional[Callable] = None

    # ------------------------------------------------------------------
    # Declaration
    # ------------------------------------------------------------------

    def step(self, name: str) -> Callable:
        """Decorator registering a step by name. Step order = registration order."""
        def deco(fn: Callable) -> Callable:
            self._steps[name] = fn
            if name not in self._step_order:
                self._step_order.append(name)
            return fn
        return deco

    def finish(self, fn: Callable) -> Callable:
        """Decorator for the completion handler ``async def done(ctx, data)``."""
        self._finish = fn
        return fn

    def on_enter(self, fn: Callable) -> Callable:
        """Optional hook ``async def entering(ctx)`` called when a wizard starts."""
        self._enter = fn
        return fn

    def on_leave(self, fn: Callable) -> Callable:
        """Optional hook ``async def leaving(ctx, data)`` called when finished."""
        self._leave = fn
        return fn

    # ------------------------------------------------------------------
    # Runtime
    # ------------------------------------------------------------------

    def _key(self, ctx) -> str:
        chat_id = getattr(ctx.chat, "id", None) if ctx.chat else None
        user_id = getattr(ctx.user, "id", None) if ctx.user else None
        return f"wizard:{self.name}:chat:{chat_id}:user:{user_id}"

    async def enter(self, ctx) -> bool:
        """Start the wizard at its first step."""
        if not self._step_order:
            logger.warning("Wizard %r has no steps — enter() is a no-op", self.name)
            return False
        first = self._step_order[0]
        await self._save(ctx, {"step": first, "data": {}})
        if self._enter is not None:
            await self._enter(ctx)
        return await self._run_step(ctx, first)

    async def step_forward(self, ctx, answer: Any) -> bool:
        """
        Pass the user's answer to the current step, advance, and run the next
        step (or ``finish`` when all steps are complete).

        Returns:
            True if the wizard processed the message (was active), False
            otherwise (caller should treat the message as normal).
        """
        state = await self._load(ctx)
        if state is None:
            return False
        current = state.get("step")
        if current is None or current not in self._steps:
            return False

        data = dict(state.get("data", {}))
        idx = self._step_order.index(current)
        # Save the answer under the step's name so data is typed by position.
        data[current] = answer

        if idx + 1 < len(self._step_order):
            nxt = self._step_order[idx + 1]
            await self._save(ctx, {"step": nxt, "data": data})
            return await self._run_step(ctx, nxt)

        # All steps complete → finish.
        await self._save(ctx, {"step": None, "data": data})
        if self._finish is not None:
            try:
                result = self._finish(ctx, data)
                if asyncio.iscoroutine(result):
                    await result
            except Exception as exc:
                logger.error("Wizard finish handler raised: %s", exc, exc_info=True)
        if self._leave is not None:
            try:
                result = self._leave(ctx, data)
                if asyncio.iscoroutine(result):
                    await result
            except Exception as exc:
                logger.error("Wizard leave hook raised: %s", exc, exc_info=True)
        return True

    async def exit(self, ctx) -> bool:
        """Cancel the wizard and clear its state."""
        state = await self._load(ctx)
        await self._storage.delete("wizard", self._key(ctx))
        return state is not None

    async def current_step(self, ctx) -> Optional[str]:
        state = await self._load(ctx)
        if state is None:
            return None
        return state.get("step")

    async def current_data(self, ctx) -> Dict[str, Any]:
        state = await self._load(ctx)
        return dict(state.get("data", {})) if state else {}

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    async def _load(self, ctx) -> Optional[Dict[str, Any]]:
        try:
            return await self._storage.get("wizard", self._key(ctx))
        except Exception as exc:
            logger.error("Wizard load failed: %s", exc, exc_info=True)
            return None

    async def _save(self, ctx, state: Dict[str, Any]) -> None:
        try:
            await self._storage.set("wizard", self._key(ctx), state)
        except Exception as exc:
            logger.error("Wizard save failed: %s", exc, exc_info=True)

    async def _run_step(self, ctx, step_name: str) -> bool:
        fn = self._steps.get(step_name)
        if fn is None:
            return False
        try:
            result = fn(ctx)
            if asyncio.iscoroutine(result):
                await result
        except Exception as exc:
            logger.error("Wizard step %r raised: %s", step_name, exc, exc_info=True)
        return True


class WizardAccessor:
    """
    Convenience accessor placed on ``Context`` as ``ctx.wizard`` — shortcuts
    for the bot-level wizard registry::

        await ctx.wizard.step("survey")       # jump to a step
        await ctx.wizard.exit("survey")       # cancel
        print(ctx.wizard.current("survey"))   # current step name
    """

    def __init__(self, bot) -> None:
        self._bot = bot

    @property
    def _registry(self) -> Dict[str, Wizard]:
        return getattr(self._bot, "_wizards", {})

    async def step(self, wizard_name: str, step_name: Optional[str] = None) -> Optional[str]:
        """Return (or set when ``step_name`` given) the current step of a wizard."""
        wiz = self._registry.get(wizard_name)
        if wiz is None:
            return None
        if step_name is not None:
            state = await wiz._load(self._bot._last_ctx if hasattr(self._bot, "_last_ctx") else None)
        return await wiz.current_step(self._bot._last_ctx if hasattr(self._bot, "_last_ctx") else None)

    async def exit(self, wizard_name: str) -> bool:
        wiz = self._registry.get(wizard_name)
        if wiz is None:
            return False
        return await wiz.exit(self._bot._last_ctx if hasattr(self._bot, "_last_ctx") else None)

    async def current(self, wizard_name: str) -> Optional[str]:
        wiz = self._registry.get(wizard_name)
        if wiz is None:
            return None
        return await wiz.current_step(self._bot._last_ctx if hasattr(self._bot, "_last_ctx") else None)
