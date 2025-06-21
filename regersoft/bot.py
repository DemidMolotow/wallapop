import asyncio
from aiogram import Bot, Dispatcher, types, F
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from config import TG_TOKEN, OWNER_ID
from automation import run_full_registration
from device_spoof_http import get_device_info

user_states = {}

bot = Bot(token=TG_TOKEN)
dp = Dispatcher()

def main_menu():
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="➕ Новая регистрация", callback_data="new_reg")],
        [InlineKeyboardButton(text="🧬 Проверить профиль эмулятора", callback_data="check_device")]
    ])
    return kb

async def ask_proxy(message: types.Message):
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="Назад", callback_data="cancel")]
    ])
    await message.answer(
        "Отправь прокси (host:port или host:port:логин:пароль):",
        reply_markup=kb
    )

async def ask_google(message: types.Message):
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="Назад", callback_data="cancel")]
    ])
    await message.answer("Введи email:пароль Google-аккаунта:", reply_markup=kb)

@dp.message(F.from_user.id == OWNER_ID, F.text == "/start")
async def cmd_start(message: types.Message):
    await message.answer("Добро пожаловать! Выбери действие:", reply_markup=main_menu())

@dp.callback_query(F.data == "new_reg")
async def new_registration(callback: types.CallbackQuery):
    user_states[callback.from_user.id] = {}
    await ask_proxy(callback.message)

@dp.callback_query(F.data == "check_device")
async def check_device(callback: types.CallbackQuery):
    info = get_device_info()
    text = "\n".join([f"{k}: `{v}`" for k, v in info.items()])
    await callback.message.answer(f"Текущий профиль эмулятора:\n{text}", parse_mode="Markdown", reply_markup=main_menu())

@dp.message(F.from_user.id == OWNER_ID)
async def process_step(message: types.Message):
    if not message.text:
        await message.answer("Пожалуйста, отправь текстовое сообщение.")
        return

    state = user_states.get(message.from_user.id, {})
    if 'proxy' not in state:
        state['proxy'] = message.text.strip()
        user_states[message.from_user.id] = state
        await ask_google(message)
    elif 'google' not in state:
        state['google'] = message.text.strip()
        user_states[message.from_user.id] = state
        await message.answer("⏳ Запускаю автоматизацию...")
        result = await run_full_registration(state['proxy'], state['google'])
        if result['success']:
            spoof = result['spoof_info']
            text = (
                f"✅ Аккаунт зарегистрирован!\n"
                f"Логин: `{result['wallapop_login']}`\n"
                f"Пароль: `{result['wallapop_password']}`\n"
                f"Прокси: `{result['proxy']}`\n"
                f"UserAgent: `{result['useragent']}`\n"
                f"🧬 Device spoof-параметры:\n" +
                "\n".join([f"{k}: `{v}`" for k, v in spoof.items()])
            )
        else:
            text = f"❌ Ошибка: {result['error']}"
        await message.answer(text, reply_markup=main_menu(), parse_mode="Markdown")
        user_states.pop(message.from_user.id, None)

@dp.callback_query(F.data == "cancel")
async def cancel_process(callback: types.CallbackQuery):
    user_states.pop(callback.from_user.id, None)
    await callback.message.answer("Действие отменено.", reply_markup=main_menu())

if __name__ == "__main__":
    asyncio.run(dp.start_polling(bot))
