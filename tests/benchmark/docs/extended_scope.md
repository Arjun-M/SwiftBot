# Extended SwiftBot assessment scope

The existing benchmark already verifies offline exact-text routing for SwiftBot, aiogram, python-telegram-bot, and pyTelegramBotAPI on Python 3.12.3. All four frameworks successfully routed the synthetic messages and matched the expected handler count. The extended assessment will preserve that workload and add independent tests for memory/RSS, startup/build time, disk footprint, worker-pool throughput, concurrency scaling, queue backpressure, and graceful drain behavior.

## Metrics

| Area | Measurement | Interpretation |
|---|---|---|
| Speed | Median and p95 dispatch time over repeated synthetic updates | Core routing efficiency, excluding network latency |
| Latency | Microseconds per update | Per-update overhead under a no-I/O handler |
| Startup | Import plus framework construction time in a fresh process | Cold setup cost for a bot worker |
| Memory | Peak resident set size and RSS delta during a streaming workload | Process RAM cost under load; includes interpreter and installed dependencies |
| Disk | Installed framework distribution bytes, file count, and site-packages size | Deployment footprint; framework-only size is separated from environment size |
| Pool | Updates completed per second at worker counts 1, 2, 4, 8 | Whether configured concurrency helps CPU-light async dispatch |
| Backpressure | Submission blocking and queue drain under slow handlers and bounded queues | Whether overload is bounded and observable rather than silently lost |
| Correctness | Expected versus observed handler invocations and queue completion | Prevents performance numbers from representing dropped work |

## Fairness rules

All tests use the same synthetic Telegram message shape and avoid Telegram network calls, API tokens, external databases, and outbound replies. The benchmark measures framework dispatch and local scheduling, not Telegram service latency or end-to-end production throughput. Results are run in separate Python 3.12 virtual environments on the same sandbox host. Each result records the exact installed distribution version.

The direct routing benchmark uses each framework's normal offline dispatch entry point. SwiftBot's direct core benchmark calls its internal `_process_update` path; a separate documented `TestClient` test measures the public in-memory harness, including its worker-pool queue. The distinction is reported explicitly rather than mixing the two numbers.

Memory results include the Python interpreter and dependency graph because that is the RAM a deployed worker actually consumes. Framework-only package bytes and complete site-packages bytes are reported separately. Pool comparisons are only interpreted within SwiftBot unless a competitor exposes an equivalent configurable local worker pool; framework architecture differences make cross-library pool numbers non-equivalent.
