import json
from swiftbot import SwiftBot

bot = SwiftBot(token='0000000000:TEST')
result = {
    'worker_pool': {
        'num_workers': bot.worker_pool.num_workers,
        'max_queue_size': bot.worker_pool.max_queue_size,
        'enable_dead_letter': bot.worker_pool.enable_dead_letter,
        'backpressure_timeout': bot.worker_pool.backpressure_timeout,
    },
    'connection_pool': {
        'max_connections': getattr(bot.connection_pool, 'max_connections', None),
        'max_keepalive': getattr(bot.connection_pool, 'max_keepalive', None),
        'enable_http2': getattr(bot.connection_pool, 'enable_http2', None),
        'timeout': str(getattr(bot.connection_pool, 'timeout', None)),
    },
}
print(json.dumps(result, indent=2))
