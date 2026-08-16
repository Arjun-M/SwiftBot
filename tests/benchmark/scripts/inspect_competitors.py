import inspect

try:
    import aiogram
    from aiogram import Bot, Dispatcher, Router
    from aiogram.types import Update
    print('=== aiogram ===')
    print('version', aiogram.__version__)
    print('Dispatcher.feed_update', inspect.signature(Dispatcher.feed_update))
    if hasattr(Dispatcher, 'feed_raw_update'):
        print('Dispatcher.feed_raw_update', inspect.signature(Dispatcher.feed_raw_update))
    print('Update.model_validate', inspect.signature(Update.model_validate))
except ModuleNotFoundError:
    pass

try:
    import telegram
    from telegram.ext import Application, MessageHandler, filters
    print('=== python-telegram-bot ===')
    print('version', telegram.__version__)
    print('Application.builder', inspect.signature(Application.builder))
    print('Application.process_update', inspect.signature(Application.process_update))
    print('Application.initialize', inspect.signature(Application.initialize))
    print('MessageHandler', inspect.signature(MessageHandler))
except ModuleNotFoundError:
    pass

try:
    import telebot
    from importlib import metadata
    print('=== pyTelegramBotAPI ===')
    print('version', metadata.version('pyTelegramBotAPI'))
    print('TeleBot', inspect.signature(telebot.TeleBot))
    print('TeleBot.process_new_updates', inspect.signature(telebot.TeleBot.process_new_updates))
    try:
        from telebot.async_telebot import AsyncTeleBot
        print('AsyncTeleBot', inspect.signature(AsyncTeleBot))
        print('AsyncTeleBot.process_new_updates', inspect.signature(AsyncTeleBot.process_new_updates))
    except ImportError:
        print('AsyncTeleBot unavailable')
except ModuleNotFoundError:
    pass
