# Changelog

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
