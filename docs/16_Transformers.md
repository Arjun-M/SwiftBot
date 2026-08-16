# 16. Transformers

Middleware sees *inbound* updates. **Transformers** sit on the other side of the story: they intercept **every outbound API call** before it hits the network. Register one on the bot's API configuration:

```python
bot.api.config.use(my_transformer)
```

A transformer is any async callable `(method, payload) -> payload`. It receives the API method name and the request payload, and may return the payload unchanged, mutate it, or return a brand-new dict. Transformers run in registration order inside the request path, before the HTTP call goes out.

## Built-in transformers <a id="built-in-transformers"></a>

```python
from swiftbot.transformer import auto_typing, call_logger, payload_patch, record

bot.api.config.use(auto_typing())                     # "typing..." while handlers run
bot.api.config.use(call_logger())                     # log every outbound call
bot.api.config.use(payload_patch(parse_mode="HTML"))  # inject defaults into every payload
```

`auto_typing` is a small but delightful touch: it sends a typing indicator when a handler starts working and clears it when the handler replies, so users see the bot is busy during long operations. `payload_patch` is how you set a default for every call — global parse mode, for instance, without touching the bot constructor.

## `throttle` — outbound rate limiting

Telegram throttles bots (roughly 30 messages per second globally, and much stricter per chat). The `throttle` transformer keeps you under a limit with a token bucket. It never drops calls — it smooths them:

```python
from swiftbot.throttle import throttle

bot.api.config.use(throttle(max_per_second=25.0))                   # global cap
bot.api.config.use(throttle(max_per_second=15.0, per_chat=1.0))     # plus 1 msg per chat per second
```

Throttling belongs in the transformer layer rather than middleware because it must act *before* the HTTP request is sent. Note the distinction from `RateLimiter` in [Middleware](11_Middleware.md): that one limits *inbound* traffic per user; `throttle` paces *outbound* API calls. Busy bots use both.

## `record` — testing without a network <a id="record-testing-without-a-network"></a>

`record()` returns a recorder transformer that captures every `(method, payload)` call and accepts scripted responses — the backbone of offline testing (see [21_Testing.md](21_Testing.md)) for the full treatment):

```python
from swiftbot.transformer import record

rec = record()
rec.script("sendMessage", result={"message_id": 1})
bot.api.config.use(rec)
```

## Writing your own <a id="writing-your-own"></a>

A transformer is short by design:

```python
async def add_signature(method, payload):
    payload["reply_markup"] = add_tracking(payload.get("reply_markup"))
    return payload
```

Any async callable with that shape works. Because transformers run for every call, keep them cheap — a slow transformer delays every message the bot sends.
