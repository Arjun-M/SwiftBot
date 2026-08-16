# SwiftBot Environment Verification Tests

Two pytest suites that verify the `swiftbot` package is fully functional, undamaged, and correctly installed. Both files stay local — nothing is pushed to the repository.

## Files

| File | Purpose | Requires network? |
|---|---|---|
| `test_swiftbot_integrity.py` | Full offline verification: 52 tests covering package imports (SwiftBot, types, middleware, filters, storage, testing harness), bot initialization and config validation, mocked async message routing with `unittest.mock.AsyncMock`, command execution, middleware chains, callback queries, FSM storage with TTL, dialogues, pipelines, exception hierarchy | No |
| `test_swiftbot_live.py` | Live smoke tests against Telegram's real API using your token (passed via env var): getMe, getUpdates, error handling, run loop start/stop, state manager, dialogue registration, and an optional live message send | Yes |

## Run

```bash
# Offline suite (no token needed)
python3 -m pytest test_swiftbot_integrity.py -v

# Live suite (token via environment variable, never written to disk)
SWIFTBOT_TOKEN="1234567890:ABC..." python3 -m pytest test_swiftbot_live.py -v

# Optional: enable the single live message send
SWIFTBOT_TOKEN="..." SWIFTBOT_SEND_CHAT_ID="7548573092" python3 -m pytest test_swiftbot_live.py -v
```

## Design notes

The offline suite uses SwiftBot's built-in `FakePool`/`TestClient` harness plus `AsyncMock` so every Telegram API call is recorded, scripted, or mocked — handlers run through the real worker pool, router (including the trie-based command router), filters, middleware, and FSM storage exactly as in production. The live suite asserts observable behavior: API responses, clean run-loop start/stop, and storage round trips.

The live message send to a specific chat ID is disabled by default (set `SWIFTBOT_SEND_CHAT_ID` to enable) to avoid messaging chats without consent.
