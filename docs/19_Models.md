# 19. Models and Types

SwiftBot parses Telegram's raw JSON into typed model objects, so handlers work with attributes instead of nested dictionaries. Two layers exist: the **filterable types** in `swiftbot.types` (used with `@bot.on(...)`, see [Handlers and the Context](03_HandlersAndContext.md) and the full parsed **model layer** underneath.

## The models you will touch

| Model | Meaning | Common attributes |
|---|---|---|
| `User` | a Telegram user | `id`, `is_bot`, `first_name`, `last_name`, `username`, `language_code` |
| `Chat` | any chat | `id` (negative for groups), `type` (`private`/`group`/`supergroup`/`channel`), `title`, `username` |
| `Message` | one message | `message_id`, `date`, `chat`, `from_user`, `text`, `photo`, `document`, `reply_to_message`, `entities` |
| `CallbackQuery` | an inline button click | `id`, `from_user`, `message`, `data` |
| `InlineQuery`, `ChosenInlineResult`, `ShippingQuery`, `PreCheckoutQuery`, `Poll`, `PollAnswer`, `ChatMemberUpdated`, `ChatJoinRequest` | the remaining update types | per-type fields |
| `Update` | the wrapper Telegram sends | `update_id`, `get_update_type()`, `get_update_object()` |

These models are also what the filters inspect: `F.private` and friends read `chat.type` off the `Message` object, and `F.photo` checks for the `photo` attribute — which is why the filter algebra of [Filters](04_Filters.md) composes so naturally with the types.

## The filterable `types` layer

The classes in `swiftbot.types` — `Message`, `CallbackQuery`, `InlineQuery`, `EditedMessage`, `ChatMemberUpdated` — double as event descriptors for the router. Constructed with keyword arguments they act as filters (`Message(text="/start")`); the same classes model parsed updates inside the `Context`. This dual role is why the router, the filters, and the handler code all speak the same names.

## The `Update` wrapper

Telegram delivers updates as a JSON object containing exactly one of the update-type fields. `Update` parses that and offers `get_update_type()` and `get_update_object()`, which the routing internals use to dispatch to the right event type. Most handlers never touch `Update` directly — `ctx.update` carries it when you need the raw picture.

## Conventions

Model attributes follow the Bot API naming converted to Python style: `from` becomes `from_user` (since `from` is a reserved word), and everything else stays as documented by Telegram. When in doubt about a field, the Bot API reference at [core.telegram.org/bots/api](https://core.telegram.org/bots/api) is the authoritative list — every field Telegram documents exists as an attribute, and missing fields are simply `None`.
