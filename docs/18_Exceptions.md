# 18. Exception Handling

When Telegram rejects an API call it returns an error code and description. SwiftBot converts those into a **typed hierarchy** of exceptions, so you catch exactly what you mean instead of catching everything and guessing.

## The hierarchy <a id="the-hierarchy"></a>

```
TelegramError
├── BadRequest
│   ├── UserNotFound, ChatNotFound, MessageNotModified,
│   │   MessageToDeleteNotFound, MessageToEditNotFound,
│   │   MessageIdInvalid, ChatWriteForbidden,
│   │   ButtonDataInvalid, MessageCaptionTooLong, MessageTextIsEmpty
├── Unauthorized            # invalid token
├── Forbidden               # bot blocked or kicked from the chat
├── TooManyRequests         # carries Retry-After information
└── MigrateToChat           # group migrated to supergroup; new chat id in parameters
```

Import from `swiftbot.exceptions.telegram`:

```python
from swiftbot.exceptions.telegram import (
    TelegramError, BadRequest, Unauthorized, Forbidden,
    TooManyRequests, ChatNotFound, MessageNotModified,
)
```

## The "send safely" pattern <a id="the-send-safely-pattern"></a>

Different Telegram errors mean different, actionable things — and that is the whole point of typing them:

```python
from swiftbot.exceptions.telegram import ChatNotFound, Forbidden, TooManyRequests

try:
    await bot.send_message(chat_id, "Hello")
except ChatNotFound:
    db_remove_user(chat_id)              # user deleted their account
except Forbidden:
    db_block_user(chat_id)               # user blocked the bot
except TooManyRequests as e:
    await asyncio.sleep(e.retry_after or 5)   # honour Telegram's backoff
except TelegramError as e:
    logger.error(f"telegram error {e.code}: {e.description}")
```

`TooManyRequests` deserves special mention: SwiftBot's connection pool already honours Telegram's `Retry-After` header automatically (see the connection pool in [Bot Core](02_BotCore.md#the-constructor)), so most rate-limit delays happen transparently. The exception surfaces when the wait is longer than your timeout or when you want explicit control.

## The centralized handler <a id="the-centralized-handler"></a>

Handler errors — exceptions raised inside your `async` handlers — route through a `CentralizedExceptionHandler` by default (`enable_centralized_exceptions=True`, see [Bot Core](02_BotCore.md). Register global handlers for your own exception types:

```python
bot.exception_handler.handle(MyAppError, lambda e, ctx: ctx.reply("Oops, try again"))
```

Unknown errors log with full tracebacks. The guarantee that matters: one crashed handler never brings down the bot.
