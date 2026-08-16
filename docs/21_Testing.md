# 21. Testing Without a Network

SwiftBot's test harness lets you verify your bot completely offline — no Telegram token, no internet. Messages are routed through your real handlers and every API call is captured instead of sent. The whole test suite for this library does exactly this.

## The pieces

| Fixture | Job |
|---|---|
| `FakePool` | replaces the network pool; records every `(method, payload)` call and hands out scripted responses |
| `TestClient` | builds a real `SwiftBot` wired to a `FakePool` with the worker pool started |
| `record()` | a transformer (see [Transformers](16_Transformers.md#record-testing-without-a-network)) that captures calls on a live bot |

```python
from swiftbot import SwiftBot
from swiftbot.testing import FakePool, TestClient

pool = FakePool()
bot = TestClient(bot=SwiftBot(token="test"), pool=pool)
```

`pool.outgoing` holds every call made during the test as a list of `(method, payload)` tuples — including calls made deep inside handlers, which is the point: you assert against real handler behaviour, not mocks of your own code.

## Sending updates

`bot.send_update()` delivers a raw update dictionary (the shape Telegram sends) and waits for the worker pool to process it. For the common case, `bot.send_message()` and `bot.send_callback()` build the update for you:

```python
await bot.send_message(text="/start", chat_id=42, from_user=123)
await bot.send_callback(data="buy:7", chat_id=42, from_user=123)
```

The second form produces the `callback_query` update that `CallbackQuery` handlers expect, so both handler kinds exercise the same routing as in production.

## Scripting responses

`FakePool` answers API calls with scripted responses in order, with a default for anything unscripted:

```python
pool.script("sendMessage", result={"message_id": 1})
pool.script("sendMessage", result={"message_id": 2})
```

`_FakeResponse(ok=False, code=400, description="Bad Request")` scripts failures, letting you test error paths — your handler's exception handling, recovery replies, and the exception hierarchy of [Exceptions](18_Exceptions.md#the-hierarchy) all behave identically to production:

```python
pool.script("sendMessage", _FakeResponse(ok=False, code=400,
                                         description="Chat not found"))
```

`pool.hook()` intercepts calls by method name with a custom async function, useful for dynamic behaviour that a fixed script cannot express. The pool also exposes `error_count` and diagnostic helpers for asserting on failures the handlers themselves did not swallow.

## Testing state machines

Dialogues and Wizards (see [Dialogues and Wizards](10_Dialogues.md)) need a storage that survives between `send_update()` calls — the `TestClient`'s in-memory storage does, so end-to-end conversation tests are a plain sequence:

```python
await bot.send_message(text="/onboard")        # enters dialogue
assert ("sendMessage", {"text": "Your name?"}) in pool.outgoing
await bot.send_message(text="Alice")           # advances the dialogue
assert ("sendMessage", {"text": "Thanks Alice"}) in pool.outgoing
```

## Testing without `TestClient`

The `record()` transformer works on a regular bot, which makes it convenient for testing production-flavoured code without rewriting it for the harness (see [Transformers](16_Transformers.md#record-testing-without-a-network)). Standard `unittest.mock.AsyncMock` composes naturally with both approaches for stubbing external services inside handlers.

## What testing cannot fake

`TestClient` exercises routing, handlers, storage, and outbound calls faithfully, but Telegram's actual delivery semantics — retries, webhook redeliveries, message ordering across chats — are a property of Telegram's servers. The `idempotency` plugin (see [Plugins](12_Plugins.md#the-four-plugins)) is the defence for the parts of that the harness cannot reproduce.
