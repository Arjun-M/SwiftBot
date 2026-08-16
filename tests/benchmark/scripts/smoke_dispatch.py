import asyncio
import json
import sys

RAW = {
    'update_id': 1,
    'message': {
        'message_id': 1,
        'date': 1000,
        'chat': {'id': 42, 'type': 'private'},
        'from': {'id': 7, 'is_bot': False, 'first_name': 'Tester'},
        'text': 'hello',
    },
}

async def run_swiftbot():
    from swiftbot import SwiftBot
    from swiftbot.types import Message
    calls = []
    bot = SwiftBot(token='0000000000:TEST', worker_pool_size=1)

    @bot.on(Message(text='hello'))
    async def handler(ctx):
        calls.append(ctx.text)

    await bot._process_update(RAW)
    print(json.dumps({'framework': 'swiftbot', 'calls': calls}))

async def run_aiogram():
    from aiogram import Bot, Dispatcher, Router, F
    from aiogram.types import Update
    calls = []
    bot = Bot(token='0000000000:TEST')
    dp = Dispatcher()
    router = Router()

    async def handler(message):
        calls.append(message.text)

    router.message.register(handler, F.text == 'hello')
    dp.include_router(router)
    await dp.feed_raw_update(bot, RAW)
    await bot.session.close()
    print(json.dumps({'framework': 'aiogram', 'calls': calls}))

async def run_ptb():
    from telegram import Bot, Update
    from telegram.ext import Application, MessageHandler, filters
    calls = []
    app = Application.builder().token('0000000000:TEST').updater(None).build()

    async def handler(update, context):
        calls.append(update.message.text)

    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handler))
    update = Update.de_json(RAW, app.bot)
    app._initialized = True
    await app.process_update(update)
    print(json.dumps({'framework': 'python-telegram-bot', 'calls': calls}))

async def run_telebot():
    from telebot.async_telebot import AsyncTeleBot
    from telebot import types
    calls = []
    bot = AsyncTeleBot('0000000000:TEST', validate_token=False)

    @bot.message_handler(func=lambda message: message.text == 'hello')
    async def handler(message):
        calls.append(message.text)

    update = types.Update.de_json(json.dumps(RAW))
    await bot.process_new_updates([update])
    print(json.dumps({'framework': 'pyTelegramBotAPI', 'calls': calls}))

async def main():
    framework = sys.argv[1]
    await {'swiftbot': run_swiftbot, 'aiogram': run_aiogram, 'ptb': run_ptb, 'telebot': run_telebot}[framework]()

asyncio.run(main())
