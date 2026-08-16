# 17. Storage and State

SwiftBot's storage is a simple key-value layer — `storage.set(namespace, key, value)`, `get(...)`, `delete(...)` — with namespaces keeping different kinds of data apart: FSM conversation state lives in `"user"`, dialogues in `"dialogue/<name>"`. Three backends ship with the library.

| Backend | Use when |
|---|---|
| `MemoryStorage()` | Development, tests, and single short-lived processes. Data dies with the process. |
| `JSONFileStorage("state.json")` | Small bots. Survives restarts; writes are debounced so bursts never flood the disk. |
| `RedisStorage()` | Multi-process or multi-container production. Requires `pip install redis[hiredis]`. |

```python
from swiftbot.storage import JSONFileStorage

bot = SwiftBot(token="YOUR_TOKEN", storage=JSONFileStorage("bot_state.json"),
               state_ttl=3600)   # idle state expires after 1 hour
```

`state_ttl` is the option that makes abandoned conversations clean themselves up: a user who walks away from a dialogue has their state expire after this many seconds.

## The `StateManager` <a id="the-statemanager"></a>

The high-level FSM API wraps storage with conversation-shaped methods:

```python
from swiftbot.storage import StateManager

manager = StateManager(bot.storage, ttl=300)

await manager.set_state(user_id=123, state={"step": "ask_name"})
state = await manager.get_state(user_id=123)     # {"step": "ask_name"} or None
await manager.clear_state(user_id=123)
```

On the context these become one-liners used throughout this documentation: `ctx.set_state(...)`, `ctx.get_state()`, `ctx.clear_state()` [Handlers and the Context](03_HandlersAndContext.md) and [Dialogues and Wizards](10_Dialogues.md).

## Choosing a backend <a id="choosing-a-backend"></a>

`MemoryStorage` is the right default for learning and testing — it is fast and needs no setup, but everything vanishes on restart, which is rarely what users expect. `JSONFileStorage` adds durability with zero infrastructure and is ideal until your bot outgrows a single process. `RedisStorage` maps each `(namespace, key)` pair to a field of the Redis key `swiftbot:<namespace>`; pass `ttl=...` on the constructor or per call for key expiry, which is convenient for session cleanup at scale.

One practical note for Redis: it is the only backend that meaningfully supports running several bot processes at once, because memory and file storage are local to a process.
