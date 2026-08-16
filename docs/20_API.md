# 20. The Telegram API Layer

SwiftBot covers the full Telegram Bot API (7.0+). Every method is available in two equivalent forms — as a convenience method on the bot, and on the API object — and both authenticate automatically:

```python
await bot.send_message(chat_id=42, text="Hi")
await bot.api.send_message(chat_id=42, text="Hi")   # identical
```

Every method takes the same keyword arguments as the [official API reference](https://core.telegram.org/bots/api). The tables below group them by topic.

## Getting updates and webhook control <a id="endpoints"></a>

| Method | Purpose |
|---|---|
| `get_updates` | pull updates manually (polling mode, see [Bot Core](02_BotCore.md#polling-vs-webhook)) |
| `set_webhook`, `delete_webhook`, `get_webhook_info` | manage webhook registration |

## Bot profile <a id="bot-profile"></a>

`get_me` (cached), `set_my_commands`, `get_my_commands`, `delete_my_commands`, `set_my_name`, `get_my_name`, `set_my_description`, `set_my_short_description`, `set_chat_menu_button`, `set_my_default_administrator_rights`.

## Messages <a id="messages"></a>

`send_message`, `forward_message`, `copy_message`, `edit_message_text`, `edit_message_caption`, `edit_message_media`, `edit_message_reply_markup`, `delete_message`, `delete_messages`, `send_chat_action`.

## Media <a id="media"></a>

`send_photo`, `send_audio`, `send_document`, `send_video`, `send_animation`, `send_voice`, `send_video_note`, `send_media_group`, `get_file`, `download_file`. Local uploads and downloads are handled by the library — `download_file(file_id)` returns the bytes, convenient for media processing.

## Chats and members <a id="chats"></a>

`get_chat`, `get_chat_administrators`, `get_chat_member_count`, `get_chat_member`, `leave_chat`, `ban_chat_member`, `unban_chat_member`, `restrict_chat_member`, `promote_chat_member`, `set_chat_administrator_custom_title`, `ban_chat_sender_chat`, `unban_chat_sender_chat`.

## Stickers <a id="stickers"></a>

`send_sticker`, `get_sticker_set`, `upload_sticker_file`, `create_new_sticker_set`, `add_sticker_to_set`, `set_sticker_position_in_set`, `delete_sticker_from_set`, `set_sticker_emoji_list`, `set_sticker_keywords`, `set_sticker_mask_position`, `set_sticker_set_title`, `set_sticker_set_thumbnail`, `set_custom_emoji_sticker_set_thumbnail`, `delete_sticker_set`, `get_custom_emoji_stickers`.

## Inline mode, payments, games, and misc <a id="inline-payments"></a>

| Group | Methods |
|---|---|
| Inline | `answer_inline_query`, `answer_web_app_query` |
| Payments | `send_invoice`, `create_invoice_link`, `answer_shipping_query`, `answer_pre_checkout_query` |
| Games | `send_game`, `set_game_score`, `get_game_high_scores` |
| Misc | `send_poll`, `stop_poll`, `send_location`, `send_venue`, `send_contact`, `send_dice`, `answer_callback_query` |

## How calls flow <a id="how-calls-flow"></a>

Every method ends up in the API object's `_request`, which runs the registered transformers (see [Transformers](16_Transformers.md#writing-your-own)), applies throttling, and issues the HTTP call through the connection pool (see [Bot Core](02_BotCore.md)) and [Troubleshooting and Pitfalls](23_Troubleshooting.md#telegram-limits-that-bite)). That is why everything in this document — reply helpers, keyboards, testing recorders, transformers — shares one consistent path with identical error handling.
