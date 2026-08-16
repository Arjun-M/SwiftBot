# 22. Webhooks

Webhook mode makes Telegram push updates to a URL you host, instead of your bot polling for them. It is the production mode: instant delivery, no wasted requests, and it scales. Two halves must agree — a server accepting the updates, and a webhook registered with Telegram pointing at it.

## The built-in server <a id="the-built-in-server"></a>

SwiftBot ships a small webhook server built on `aiohttp`:

```python
from swiftbot.webhook.server import WebhookServer
from swiftbot.connection import ConnectionConfig

app = WebhookServer(bot=bot, connection=ConnectionConfig())
await app.run(
    host="0.0.0.0",
    port=8443,
    webhook_path="/webhook",
    secret_token="long-random-string",
    health_path="/health",
    metrics_path="/metrics",
    max_payload_size=2**20,   # 1 MB limit on incoming JSON
    ssl_context=ctx,          # optional TLS
)
```

The essentials: **`webhook_path`** is where Telegram delivers updates — it must match exactly what you register. **`secret_token`** is verified against the `X-Telegram-Bot-Api-Secret-Token` header on every request; a mismatch rejects the call before anything touches your handlers. This is what lets your URL be secret-proof: even if someone discovers it, they cannot post fake updates. **`health_path`** and **`metrics_path`** give monitoring endpoints for load balancers and dashboards.

The shortcut on the bot itself (see [Bot Core](02_BotCore.md#run-stop-and-stats)) runs the same machinery with sensible defaults:

```python
await bot.run_webhook(host="0.0.0.0", port=8443, path="/webhook",
                      secret_token=SECRET)
```

## Registering the webhook <a id="registering-the-webhook"></a>

Before the server starts receiving anything, tell Telegram where it is:

```python
await bot.set_webhook(url="https://your.server:8443/webhook",
                      secret_token=SECRET,
                      max_connections=100,
                      allowed_updates=["message", "callback_query"])
```

`allowed_updates` is worth attention: Telegram only forwards the update types listed, so leaving `message` off means your bot never sees private chats. On shutdown, unregister:

```python
await bot.delete_webhook(drop_pending_updates=True)
```

`drop_pending_updates=True` discards any backlog — without it, your bot receives updates that piled up while the server was down, which a short outage makes annoying but a long outage makes disastrous.

## Webhooks vs polling <a id="webhooks-vs-polling"></a>

| | Polling | Webhook |
|---|---|---|
| Setup | one line | server + registered URL + TLS certificate |
| Delivery | delayed by poll interval | instant |
| Cost | constant requests | none between updates |
| Scale | fine for small bots | better for anything public |

A small personal bot is comfortable on polling forever. Anything receiving steady traffic should use webhooks.

## Production notes

Telegram requires HTTPS with a valid certificate for webhook URLs — a reverse proxy (nginx, Caddy) or a cloud endpoint with TLS is the usual setup, and the `ssl_context` parameter covers self-hosted TLS. The server deliberately validates the content type, enforces the payload limit, and logs rejected requests, so untrusted traffic dies at the door. Finally, one rule the [Troubleshooting](23_Troubleshooting.md#i-ran-webhook-and-polling-at-once) page repeats: never run polling and a webhook simultaneously — Telegram complains, and updates get delivered twice.
