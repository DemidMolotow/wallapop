import asyncio
from aiogram import Bot, Dispatcher, types, F
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from config import TELEGRAM_TOKEN, ADMIN_IDS
from monitoring.mailing_control import start_mailing, stop_mailing, get_stats

bot = Bot(token=TELEGRAM_TOKEN)
dp = Dispatcher()

def get_main_menu():
    kb = InlineKeyboardMarkup(row_width=2)
    kb.add(
        InlineKeyboardButton("▶️ Запуск рассылки", callback_data="start_mailing"),
        InlineKeyboardButton("⏹ Стоп рассылки", callback_data="stop_mailing"),
        InlineKeyboardButton("📊 Статистика", callback_data="stats"),
        InlineKeyboardButton("📋 Аккаунты", callback_data="accounts_menu"),
        InlineKeyboardButton("🌐 Прокси", callback_data="proxies_menu"),
        InlineKeyboardButton("💬 Шаблоны", callback_data="templates_menu"),
        InlineKeyboardButton("📝 Логи", callback_data="logs"),
        InlineKeyboardButton("🚨 Ошибки", callback_data="errors"),
        InlineKeyboardButton("⚙️ Настройки", callback_data="settings"),
    )
    return kb

@dp.message(F.text == "/start")
async def start_cmd(msg: types.Message):
    if msg.from_user.id not in ADMIN_IDS:
        return await msg.answer("Нет доступа")
    await msg.answer("Добро пожаловать! Выберите действие:", reply_markup=get_main_menu())

@dp.callback_query(lambda call: call.data in [
    "start_mailing", "stop_mailing", "stats", "logs", "errors", "settings"
])
async def main_menu_handler(call: types.CallbackQuery):
    if call.from_user.id not in ADMIN_IDS:
        return await call.answer("Нет доступа")
    if call.data == "start_mailing":
        status = await start_mailing()
        await call.message.edit_text(status, reply_markup=get_main_menu())
    elif call.data == "stop_mailing":
        status = await stop_mailing()
        await call.message.edit_text(status, reply_markup=get_main_menu())
    elif call.data == "stats":
        await call.message.edit_text(get_stats(), reply_markup=get_main_menu())
    elif call.data == "logs":
        await call.message.edit_text("Логи пока не реализованы", reply_markup=get_main_menu())
    elif call.data == "errors":
        await call.message.edit_text("Ошибки пока не реализованы", reply_markup=get_main_menu())
    elif call.data == "settings":
        await call.message.edit_text("Настройки пока не реализованы", reply_markup=get_main_menu())

@dp.callback_query(lambda call: call.data.endswith("_menu"))
async def menu_router(call: types.CallbackQuery):
    await call.message.edit_text(f"Раздел {call.data.replace('_menu','').title()} (в разработке)", reply_markup=get_main_menu())

@dp.message()
async def fallback(msg: types.Message):
    await msg.answer("Используйте меню для управления ботом.", reply_markup=get_main_menu())

async def start_bot():
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(start_bot())