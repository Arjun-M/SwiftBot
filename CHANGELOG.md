# Changelog

## [Unreleased]

No unreleased changes are recorded.

## [1.6.4] - 2026-08-18

### Added

- Add current **Telegram Bot API 10.2** support, including modern Rich Message, Live Photo, reaction, paid-media, checklist, suggested-post, business, subscription, managed-bot, draft, and ephemeral-message operations.
- Add current typed fields and update routing for modern Telegram payloads.

### Changed

- Improve low-level request serialization, multipart uploads, file downloads, and high-level client forwarding.
- Bump the package version to 1.6.4 and document the Telegram Bot API 10.2 compatibility target.

### Fixed

- Correct structured multipart field handling and typed Rich Message serialization.

## [1.6.0] - 2026-08-16

### Added

- Add dialogues, scoped middleware, outbound throttling, the fluent `Reply` builder, fallback handlers, and graceful shutdown support.

## [1.5.0] - 2026-08-16

### Added

- Add dependency-injected pipelines, declarative bot commands, middleware composition, dispatch routing, typed wizards, plugins, and expanded filter utilities.

## [1.4.0] - 2026-08-15

### Added

- Add the testing harness, callback-data helpers, deep linking, typed models, Redis storage, proxy support, and expanded Telegram API coverage.

## [1.1.0] - 2026-08-15

### Added

- Add persistent storage, retry handling, typed Telegram errors, file transfers, webhook hardening, worker-pool safeguards, and the initial automated test and CI foundation.

### Fixed

- Fix webhook forwarding, recursive message parsing, handler registration edge cases, and worker-pool shutdown behavior.

