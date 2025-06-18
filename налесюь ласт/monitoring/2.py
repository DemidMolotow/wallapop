import asyncio
from aiogram import Bot, Dispatcher, types, F
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton
from config import TELEGRAM_TOKEN, ADMIN_IDS, PROXY_LIST_PATH, EMAIL_LIST_PATH, PASTES_PATH
from proxy_manager.manager import add_proxy
from mail_manager.manager import load_email_accounts
from utils import save_lines, load_lines
from monitoring.mailing_control import start_mailing, stop_mailing, get_stats

bot = Bot(token=TELEGRAM_TOKEN)
dp = Dispatcher()

def get_main_menu():
    kb = ReplyKeyboardMarkup(resize_keyboard=True)
    kb.add(KeyboardButton("Запуск рассылки"))
    kb.add(KeyboardButton("Стоп рассылки"))
    kb.add(KeyboardButton("Загрузить прокси"))
    kb.add(KeyboardButton("Загрузить почты"))
    kb.add(KeyboardButton("Загрузить пасты"))
    kb.add(KeyboardButton("Статистика"))
    return kb

@dp.message(F.text == "/start")
async def start_cmd(msg: types.Message):
    await msg.answer("Добро пожаловать! Выберите действие:", reply_markup=get_main_menu())

@dp.message(F.text == "Загрузить прокси")
async def upload_proxies(msg: types.Message):
    await msg.answer("Пришлите список прокси (одна строка — один прокси):")

@dp.message(F.text == "Загрузить почты")
async def upload_emails(msg: types.Message):
    await msg.answer("Пришлите список email:password (одна строка — одна почта):")

@dp.message(F.text == "Загрузить пасты")
async def upload_pastes(msg: types.Message):
    await msg.answer("Пришлите список паст (одна строка — один текст):")

@dp.message(F.text == "Статистика")
async def stats(msg: types.Message):
    await msg.answer(get_stats())

@dp.message(F.text == "Запуск рассылки")
async def start_mailing_cmd(msg: types.Message):
    status = await start_mailing()
    await msg.answer(status)

@dp.message(F.text == "Стоп рассылки")
async def stop_mailing_cmd(msg: types.Message):
    status = await stop_mailing()
    await msg.answer(status)

@dp.message(F.reply_to_message, F.reply_to_message.text == "Пришлите список прокси (одна строка — один прокси):")
async def save_proxies(msg: types.Message):
    lines = [l.strip() for l in msg.text.splitlines() if l.strip()]
    save_lines(PROXY_LIST_PATH, lines)
    await msg.answer(f"Загружено {len(lines)} прокси.")

@dp.message(F.reply_to_message, F.reply_to_message.text == "Пришлите список email:password (одна строка — одна почта):")
async def save_emails(msg: types.Message):
    lines = [l.strip() for l in msg.text.splitlines() if l.strip()]
    save_lines(EMAIL_LIST_PATH, lines)
    await msg.answer(f"Загружено {len(lines)} почт.")

@dp.message(F.reply_to_message, F.reply_to_message.text == "Пришлите список паст (одна строка — один текст):")
async def save_pastes(msg: types.Message):
    lines = [l.strip() for l in msg.text.splitlines() if l.strip()]
    save_lines(PASTES_PATH, lines)
    await msg.answer(f"Загружено {len(lines)} паст.")

@dp.message()
async def fallback(msg: types.Message):
    await msg.answer("Используйте кнопки меню.")

def start_bot():
    import asyncio
    from aiogram import executor
    executor.start_polling(dp, skip_updates=True)