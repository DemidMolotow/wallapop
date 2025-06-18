import asyncio
import os

from aiogram import Bot, Dispatcher, types, F
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, ReplyKeyboardRemove
from aiogram.client.default import DefaultBotProperties
from config import TELEGRAM_TOKEN, ADMIN_IDS, PROXY_LIST_PATH, EMAIL_LIST_PATH, PASTES_PATH

bot = Bot(token=TELEGRAM_TOKEN, default=DefaultBotProperties(parse_mode="HTML"))
dp = Dispatcher()
user_add_mode = {}  # user_id: "account"|"cookie"

EMAILS_PER_PAGE = 10
PROXIES_PER_PAGE = 10
PASTES_PER_PAGE = 5

LOG_PATH = "logs.txt"
ERRORS_PATH = "errors.txt"
WALLA_READY_PATH = "wallapop_ready.txt"  # Новый файл для готовых аккаунтов

def file_lines(path):
    try:
        with open(path, encoding="utf-8") as f:
            return [l.strip() for l in f if l.strip()]
    except Exception:
        return []

def save_lines(path, lines):
    with open(path, "w", encoding="utf-8") as f:
        for l in lines:
            f.write(l + "\n")

def append_lines(path, lines):
    with open(path, "a", encoding="utf-8") as f:
        for l in lines:
            f.write(l + "\n")

# Главное меню:
def get_main_menu():
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="▶️ Запуск рассылки", callback_data="start_mailing")],
            [InlineKeyboardButton(text="⏹ Стоп рассылки", callback_data="stop_mailing")],
            [InlineKeyboardButton(text="📊 Статистика", callback_data="stats")],
            [InlineKeyboardButton(text="📋 Аккаунты (регистрация)", callback_data="accounts_menu_0")],
            [InlineKeyboardButton(text="💼 Wallapop-аккаунты (готовые)", callback_data="wallapop_menu")],
            [InlineKeyboardButton(text="🌐 Прокси", callback_data="proxies_menu_0")],
            [InlineKeyboardButton(text="💬 Шаблоны", callback_data="pastes_menu_0")],
            [InlineKeyboardButton(text="📝 Логи", callback_data="logs_menu")],
            [InlineKeyboardButton(text="🚨 Ошибки", callback_data="errors_menu")],
            [InlineKeyboardButton(text="⚙️ Настройки", callback_data="settings_menu")],
        ]
    )

# --- Wallapop аккаунты ---
def get_wallapop_menu():
    rows = [
        [InlineKeyboardButton(text="➕ Добавить готовый аккаунт", callback_data="wallapop_add")],
        [InlineKeyboardButton(text="📃 Посмотреть список", callback_data="wallapop_list")],
        [InlineKeyboardButton(text="⬅️ В меню", callback_data="back_main")]
    ]
    return InlineKeyboardMarkup(inline_keyboard=rows)

@dp.callback_query()
async def universal_callback(call: types.CallbackQuery):
    data = call.data

    # ...Старые пункты меню

    if data == "wallapop_menu":
        await call.message.edit_text("Wallapop-аккаунты (уже зарегистрированные):", reply_markup=get_wallapop_menu())
    elif data == "wallapop_add":
        user_add_mode[call.from_user.id] = "wallapop"
        await call.message.edit_text("Пришлите данные готового аккаунта Wallapop (например, email:пароль:токен или в вашем формате):", reply_markup=get_wallapop_menu())
    elif data == "wallapop_list":
        accounts = file_lines(WALLA_READY_PATH)
        if accounts:
            text = "\n".join(accounts)
        else:
            text = "Нет добавленных аккаунтов."
        await call.message.edit_text(text, reply_markup=get_wallapop_menu())
    # ...Далее остальные обработчики меню

# --- Добавление аккаунта (универсально для email и wallapop) ---
@dp.message()
async def handle_account_add(msg: types.Message):
    uid = msg.from_user.id
    if uid in user_add_mode:
        mode = user_add_mode[uid]
        lines = [l.strip() for l in msg.text.splitlines() if l.strip()]
        if mode == "account":
            append_lines(EMAIL_LIST_PATH, lines)
            await msg.answer(f"Добавлено {len(lines)} аккаунтов.", reply_markup=get_accounts_menu(0))
        elif mode == "wallapop":
            append_lines(WALLA_READY_PATH, lines)
            await msg.answer(f"Добавлено {len(lines)} готовых аккаунтов Wallapop.", reply_markup=get_wallapop_menu())
        user_add_mode.pop(uid)
    else:
        await msg.answer("Используйте только меню под сообщением.", reply_markup=ReplyKeyboardRemove())

# --- Вызов добавления аккаунта (регистрация) ---
@dp.callback_query(lambda c: c.data == "account_add")
async def account_add(call: types.CallbackQuery):
    user_add_mode[call.from_user.id] = "account"
    await call.message.edit_text(
        "Пришлите одним сообщением email:password (или несколько, каждый на новой строке):",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="⬅️ В аккаунты", callback_data="accounts_menu_0")]])
    )

# ...Остальной код не меняется