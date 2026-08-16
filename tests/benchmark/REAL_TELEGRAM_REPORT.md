# Real Telegram Environment Benchmark

**Framework:** SwiftBot 1.6.3
**Test type:** Read-only real Telegram Bot API benchmark
**Date:** 2026-08-16
**Network:** Telegram Bot API over SwiftBot’s HTTP/2-enabled connection pool

## Scope and safety

The test used a temporary credential supplied outside the repository. It called only `getMe`, `getChat`, and `getUpdates`. No message was sent, no webhook was changed, no update was acknowledged or deleted, and no administrative or state-changing method was called. The credential file was deleted after the run and the published result was sanitized to remove bot and chat identifiers.

## Verification result

The bot identity call succeeded and confirmed that the credential belongs to a Telegram bot. The chat lookup succeeded and confirmed the requested chat ID. The returned chat username matched the expected username case-insensitively, which is appropriate because Telegram usernames are case-insensitive for comparison. The published sanitized JSON preserves only the verification status and match booleans.

| Check | Result |
|---|---|
| `getMe` | Successful |
| Bot identity | Confirmed as a bot |
| `getChat` | Successful |
| Chat ID match | True |
| Username match | True, case-insensitive |
| Write methods called | None |
| Token printed or included in result | No |

## Real API latency

The measurements below include the real network path from the sandbox to Telegram and therefore should not be compared directly with the offline framework-routing benchmark. They are useful for verifying real operation, connection behavior, and order-of-magnitude latency.

| Method | Calls | Successful | Median | P95 | Minimum | Maximum |
|---|---:|---:|---:|---:|---:|---:|
| `getMe` | 20 | 20 | **641.4 ms** | 676.6 ms | 638.8 ms | 678.1 ms |
| `getChat` | 5 | 5 | **641.1 ms** | 659.9 ms | 638.9 ms | 652.7 ms |
| `getUpdates` with `timeout=0` | 5 | 5 | **639.3 ms typical** | Not summarized | 414.6 ms | 642.1 ms |

The approximately 640 ms round-trip dominates framework overhead in a real API call. This is why the offline dispatch benchmark is still useful: once network I/O is involved, local routing differences become a small part of end-to-end latency.

## Connection-pool concurrency

The real test used an eight-worker SwiftBot configuration, 16 maximum HTTP connections, and HTTP/2 enabled. Concurrent `getMe` calls completed successfully at every tested level.

| Concurrent calls | Completed | Failed | Wall time |
|---:|---:|---:|---:|
| 1 | 1 | 0 | 640.0 ms |
| 2 | 2 | 0 | 640.7 ms |
| 4 | 4 | 0 | 645.7 ms |
| 8 | 8 | 0 | 1,017.9 ms |

The results show useful overlap for two and four concurrent calls. At eight concurrent calls, total wall time increased to approximately 1.0 seconds, indicating that concurrency is bounded by the remote API path, connection scheduling, and server/network behavior rather than scaling linearly without limit. No HTTP errors or Telegram rate-limit errors occurred in this small read-only sample.

## Real-process resource measurement

The SwiftBot process RSS increased from 27.6 MiB before framework construction to 33.2 MiB after construction, a build-time increase of approximately **5.6 MiB** in this real-test process. Connection-pool initialization itself completed in approximately **0.20 ms** after object construction. This is a process-level observation, not a complete production memory profile.

## Reproduce safely

Store a replacement token outside the repository. Do not pass it as a command-line argument, commit it, or include it in logs.

```bash
export TELEGRAM_TOKEN_FILE=/secure/location/Env.txt

python3 -m venv venv-swiftbot
venv-swiftbot/bin/python -m pip install swiftbot==1.6.3

venv-swiftbot/bin/python scripts/real_telegram_benchmark.py \
  --token-file "$TELEGRAM_TOKEN_FILE" \
  --chat-id "$TELEGRAM_CHAT_ID" \
  --expected-username "$TELEGRAM_EXPECTED_USERNAME" \
  --output results/real_telegram_swiftbot_local.json

python3 scripts/sanitize_real_result.py \
  results/real_telegram_swiftbot_local.json \
  results/real_telegram_swiftbot_sanitized.json
```

The checked-in `results/real_telegram_swiftbot_sanitized.json` is the publishable result. It intentionally excludes the bot ID, bot username, chat ID, chat username, and display name.
