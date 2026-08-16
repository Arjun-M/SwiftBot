# Fair benchmark methodology

## Purpose

The benchmark measures **public offline raw-update processing** rather than claiming end-to-end Telegram performance. It is intended to compare the cost of taking a Telegram-shaped dictionary through each framework’s public update-processing surface, route selection, and a no-I/O async handler.

## Normalized workload

Every framework receives the same synthetic Telegram-shaped update structure, the same number of registered exact-text routes, the same cyclic route distribution, the same no-I/O handler body, one logical worker, enabled Python garbage collection, identical warm-up and repeat counts, and a correctness assertion that the expected handler count was reached.

## Public adapter paths

| Framework | Public path used | Matching rule |
|---|---|---|
| SwiftBot | `TestClient.send_updates` | Exact `Message(text=...)` |
| aiogram | `Dispatcher.feed_raw_update` | Exact `F.text == value` |
| python-telegram-bot | `Application.process_update` after `Update.de_json` | Exact custom `MessageFilter` |
| pyTelegramBotAPI | `AsyncTeleBot.process_new_updates` after `Update.de_json` | Exact predicate |

The paths are public and representative, but they are not implementation-identical. Some frameworks construct typed update objects or perform additional validation and middleware work. The results therefore describe **public raw-update processing in these versions**, not an intrinsic ranking of framework quality or end-to-end bot speed.

## What is excluded

The benchmark does not call Telegram, send network requests, use a database or Redis, execute application business logic, measure webhook servers, or model production middleware and logging. The real Telegram smoke test is reported separately and is not combined with local dispatch throughput.

## Resource benchmark

The memory test uses a fresh process, the same public adapter paths, normal garbage collection, ten routes, 10,000 updates, and 100-update batches. It records build RSS, workload RSS delta, peak sampled RSS, and correctness. RSS includes the Python interpreter and dependencies.

## Interpretation rule

The results must be reported as **measured public-path observations**, with adapter paths and versions shown next to the numbers. Avoid claims such as “SwiftBot is universally X times faster.” A real application’s network, handler I/O, persistence, serialization, and Telegram rate limits can dominate local dispatch cost.

## Verified corrected snapshot

The corrected ten-route public-path snapshot measured SwiftBot at 19,803 updates/s and 33.2 MiB peak RSS; pyTelegramBotAPI at 10,358 updates/s and 46.8 MiB; python-telegram-bot at 9,432 updates/s and 39.9 MiB; and aiogram at 1,219 updates/s and 154.4 MiB. The throughput and RSS charts were visually checked for readable labels and appropriate scaling.
