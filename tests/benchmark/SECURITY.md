# Security policy

This benchmark repository must never contain a Telegram bot token, private chat identifier, private username, or raw real-environment response. The real benchmark is read-only, but its credential still grants access to the bot API and must be handled as a secret.

Run the real test with a token stored outside the repository, for example in a temporary file with restrictive permissions or in a secret environment variable. Never put the token in a command-line argument, source file, README, issue, pull request, terminal transcript, or Git history. If a token is exposed, revoke it immediately through Telegram’s @BotFather and generate a replacement.

The committed sanitized real result intentionally omits identifying bot and chat fields. Keep `results/real_telegram_swiftbot.json` and any local raw output untracked; the repository `.gitignore` excludes them.

The real test calls only `getMe`, `getChat`, and `getUpdates`. It does not call message-sending, webhook-modifying, deletion, administrative, or state-changing methods.
