# Changelog

## [1.5.0] — 2026-08-16

The "standout" release. v1.5 closes the capability gaps that developers
consistently hit in Python Telegram SDKs — dependency-injected handler
pipelines, an outbound API-call layer, composable middleware bundles with error
boundaries, declarative typed command specs, and typed wizards. Every feature is
idiomatic Python and none exists in the rest of the Python ecosystem. Full
documentation site: `docs/index.html`.

### Added
- **`swiftbot.pipeline` — dependency-injected handler pipelines**: handlers declare the dependencies they need by parameter name
  and the `Pipeline` injects them; undeclared dependencies raise
  `PipelineDependencyMissing` loudly. `bot.pipeline(pipe)` mounts a pipeline as
  a middleware stage.
- **`swiftbot.commands` — declarative `BotCommands` specs**: typed arg
  placeholders (`<name:type>`), aliases, `Cmd.parse()`, auto-generated
  `help_text`, and `CommandsMiddleware` answering `/help` from the spec.
- **`swiftbot.transformer` — outbound API call layer**: a first for Python Telegram SDKs —
  `bot.api.config.use(...)` intercepts every API call. Built-ins: `auto_typing`,
  `idempotency_guard`, `call_logger`, `payload_patch`, and `Recorder` for
  scripting results/errors per method (network-free API-level testing).
- **`swiftbot.composer` — middleware bundles with `.catch()` error boundaries**:
  nestable bundles; raw middleware callables are invoked with `(ctx,
  next_handler)`; `.on_exception()` alias provided.
- **`bot.route()` — pre-handler dispatch table** mapping update kinds (or raw
  predicates) to middleware.
- **`swiftbot.wizard` — typed conversation wizards**: `@step`, `@finish`,
  `on_enter`/`on_leave` hooks, storage-agnostic state, accumulated answers,
  `ctx.wizard` accessor; registered via `bot.wizard(name)`.
- **`bot.run_shutdown()` — graceful shutdown**: SIGINT/SIGTERM handlers plus
  worker-pool drain.
- **`swiftbot.plugins` — official plugin registry**: `SpamDeflector`,
  `SessionLimiter`, `Idempotency`, `Whitelist` classes with factory helpers
  (`spam_deflector`, `session_limiter`, `idempotency`, `whitelist`).
- **`F` filter algebra** in `swiftbot.filters`: preset factory with combinators
  (`F.text & F.private & ~F.forwarded`), `supergroup` preset, and
  `F.command()`/`F.regex()` shortcuts.
- **`ctx.command`** populated by `CommandsMiddleware` with the parsed command.
- **50 new tests** covering every v1.5 feature; the full suite is 133 tests, all green.

### Fixed
- **Transformer short-circuit**: scripted `Recorder` results/errors now flow
  through `TelegramAPI._request` as control-flow exceptions instead of being
  logged and hidden by the misbehaving-transformer catch-all.
- **Composer boundary**: raw middleware callables without `on_update` are now
  invoked with `(ctx, next_handler)` instead of being silently skipped, and a
  boundary correctly consumes and stops propagation.

### Changed
- Version bumped to **1.5.0**; new modules exported from `swiftbot`.

## [1.6.0] — 2026-08-16

The "state machine and safety net" release. v1.6 adds a state machine where
states carry their own typed data (dialogues), predicate-guarded middleware
scopes, outbound rate limiting, a fluent reply builder, and fallback handlers —
a feature set no other Python Telegram framework offers in a single package.

### Added
- **`swiftbot.dialogue` — state-carrying dialogues**: `@dlg.state(name,
  next=[...], timeout=...)` steps with a declared transition graph, typed carry
  data passed between states, `Dialogue.next()` / `Dialogue.end`, `@dlg.finish`,
  optional `@dlg.on_timeout` hooks, persistent state through the bot's storage,
  and `DialogueTransitionError` for illegal moves. Active sessions intercept the
  user's updates before any handler runs; `await dlg.exit(ctx)` releases them.
- **`swiftbot.scopes` — scoped middleware chains**: `bot.scope(predicate)`
  installs a middleware chain that runs only when a predicate over the raw
  update matches — per chat type, per user, or per business rule. Scopes nest
  Composer bundles and their error boundaries.
- **`swiftbot.throttle` — outbound rate-limit transformer**: token-bucket
  throttling as a `bot.api.config.use()` stage, with an optional per-chat rate
  that keeps noisy chats from consuming the global budget.
- **`swiftbot.reply` — fluent `Reply` builder**: chain `.text()`,
  `.caption()`, `.markup()`, `.silent()`, `.protect()`, `.reply_to()`,
  `.parse_mode()` and `.option()`, then `await .send()`.
- **`bot.fallback(handler)` and `bot.on_unknown_command(handler)`**: safety-net
  handlers for unmatched updates and `/command` messages not covered by a
  `BotCommands` spec (the latter works through `CommandsMiddleware`, which now
  forwards unknown commands and lets the middleware chain run even on
  no-match updates).

### Changed
- Version bumped to **1.6.0**; new modules exported from `swiftbot`.

## [1.4.0] — 2026-08-15

### Added
- **Testing harness (`swiftbot.testing`)**: `FakePool` records every outgoing API call (method + params), can be scripted with success payloads or Telegram errors, and supports a global hook; `TestClient` is an async context manager that runs a bot against the fake — handlers execute through the real worker pool, router, filters, middleware and FSM storage, minus the network. See `docs` / the module docstring for usage.
- **CallbackData (`swiftbot.callback_data`)**: type-safe callback payload factory (`CallbackData("nav", str, int)`) with `pack`/`unpack`, an optional `filter()` for registering handlers, `CallbackDataInvalid` for malformed payloads, and automatic 64-byte guard enforcement.
- **Deep linking (`swiftbot.deep_linking`)**: `create_start_link()`, `encode_payload()` (str / bytes / dict), `decode_payload()`, and `parse_start_param()` covering the full `?start=...` deep-linking flow.
- **Typed Bot API models (`swiftbot.models`)**: `User`, `Chat`, `Message`, `CallbackQuery`, `InlineKeyboardMarkup`, `Document`, `MessageEntity`, `PhotoSize` with tolerant `from_dict()`/`to_dict()` and `raw` passthrough — unknown future fields never break parsing.
- **RedisStorage (`swiftbot.storage`)**: drop-in `RedisStorage` (lazy `redis` import with a clear error if uninstalled) alongside `MemoryStorage` and `JSONFileStorage`; `StateManager` supports per-key TTL.
- **Proxy support**: `SwiftBot(proxy="...")` wires a proxy URL (http/https/socks5) through the HTTP connection pool.
- **Bot API 2026 (9.6–10.2)**: 11 new API methods (`getManagedBotToken`, `replaceManagedBotToken`, `answerGuestQuery`, `sendLivePhoto`, `deleteAllMessageReactions`, `sendRichMessage`, `sendRichMessageDraft`, `editMessageText` rich variant, `deleteEphemeralMessage`, `answerChatJoinRequestQuery`, `sendChatJoinRequestWebApp`) and 9 new update kinds (`managed_bot_created/updated`, `bot_subscription_updated`, `guest_message`, `business_message`, `edited_business_message`, `deleted_business_messages`, `purchase`).
- **50 new tests** covering every v1.2–v1.4 feature; the full suite is 83 tests, all green.

### Fixed
- **Duplicate API internals**: the API module had a second `__init__`/`_request` pair that shadowed the multipart-upload-capable original — every request that used `InputFile` silently lost its file payload, and errors were raised as bare `Exception` instead of typed `TelegramError` subclasses. The duplicate was removed; all requests now go through the single correct implementation.
- **`filters=` alias**: `Message(filters=CommandFilter(...))` now works as the conventional alias for `filter_func=`.
- **Collection noise**: pytest collection configuration now excludes the public `TestClient` class from being mistaken for a test suite.

### Changed
- Version bumped to **1.4.0**.

## [1.1.0] — 2026-08-15

### Fixed
- **Webhook mode**: updates no longer crash with `AttributeError` — the webhook server now forwards the raw update dict to the client (the previous `UpdateObj` wrapper was incompatible with `Update.from_dict`).
- **Import path**: the package now installs as lowercase `swiftbot`, so `from swiftbot import SwiftBot` works out of the box.
- **Recursive payload DoS**: `Message.from_dict` now truncates deeply nested `reply_to_message` chains instead of raising `RecursionError`. `Update.from_dict` accepts `None` safely.
- **Duplicate code removed**: the double `get_me` definition in `client.py` and the duplicated `CommandFilter` in `filters.py` were consolidated.
- **Dead regex cache**: the advertised "pre-compiled regex cache" (an `lru_cache` on an uncalled helper) was removed; compiled patterns are now actually used during matching.
- **Invalid regex patterns** no longer crash handler registration — they are dropped with a warning at compile time.
- **Worker pool**: `stop()` now drains pending updates before cancelling workers (previously the stop flag made workers abandon the queue); the queue is correctly sized so advertised capacity isn't silently halved; `submit()` now applies real backpressure with a bounded timeout instead of waiting forever; failed tasks are captured in the dead-letter queue with their exceptions preserved.
- **Invalid escape sequences** (`\d` in docstrings) removed — the package now imports with zero warnings.

### Added
- **Persistent FSM storage**: `BaseStorage`, `MemoryStorage`, and `JSONFileStorage` (atomic, debounced writes), wired through `SwiftBot(storage=..., state_ttl=...)`. Conversation state now survives restarts; the per-context `user_data`/`chat_data` proxies fall back to in-memory storage when none is configured.
- **Retry-After compliance**: HTTP 429 responses are retried honoring Telegram's `retry_after` parameter, with exponential backoff and the circuit breaker untouched.
- **Typed error hierarchy**: `TelegramError.from_response()` maps Telegram error codes to `BadRequest`, `Unauthorized`, `Forbidden`, `UserNotFound`, `ChatNotFound`, `TooManyRequests` (carrying `retry_after`), `MigrateToChat`, and `InvalidToken`.
- **File uploads and downloads**: `InputFile` for local file uploads via multipart form-data; `get_file()` and `download_file()` helpers on the client and API module.
- **Webhook hardening**: request size limits, secret-token verification, and logged error handling in the webhook server.
- **Tests and CI**: a 33-test suite (parsing, routing, filters, FSM storage round-trips, worker pool backpressure and dead letters, webhook server, typed errors) plus a GitHub Actions workflow running on Python 3.10–3.13.
- **Example bot**: `examples/basic_bot.py` demonstrating commands, a multi-step FSM conversation, and typed error handling.

### Changed
- Documentation and packaging now make honest, verifiable claims — the unsubstantiated performance-comparison table ("30× faster routing", "20–30% less memory", "Based on analysis by an external ai model") was removed.
- Version bumped to **1.1.0**.
