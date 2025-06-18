import asyncio
import os

from aiogram import Bot, Dispatcher, types, F
from aiogram.types import (
    InlineKeyboardMarkup, InlineKeyboardButton, ReplyKeyboardRemove, KeyboardButton, ReplyKeyboardMarkup
)
from aiogram.client.default import DefaultBotProperties
from config import TELEGRAM_TOKEN, ADMIN_IDS, PROXY_LIST_PATH, EMAIL_LIST_PATH, PASTES_PATH

bot = Bot(token=TELEGRAM_TOKEN, default=DefaultBotProperties(parse_mode="HTML"))
dp = Dispatcher()

EMAILS_PER_PAGE = 10
PROXIES_PER_PAGE = 10
PASTES_PER_PAGE = 5

LOG_PATH = "logs.txt"
ERRORS_PATH = "errors.txt"

# ----------------- УТИЛИТЫ -----------------
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

def get_pastes():
    text = ""
    try:
        with open(PASTES_PATH, "r", encoding="utf-8") as f:
            text = f.read()
    except Exception:
        pass
    return [p.strip() for p in text.split("---") if p.strip()]

def save_pastes(pastes):
    with open(PASTES_PATH, "w", encoding="utf-8") as f:
        for idx, p in enumerate(pastes):
            f.write(p.strip())
            if idx != len(pastes) - 1:
                f.write("\n---\n")

# ----------------- ГЛАВНОЕ МЕНЮ -----------------
def get_main_menu():
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="▶️ Запуск рассылки", callback_data="start_mailing")],
            [InlineKeyboardButton(text="⏹ Стоп рассылки", callback_data="stop_mailing")],
            [InlineKeyboardButton(text="📊 Статистика", callback_data="stats")],
            [InlineKeyboardButton(text="📋 Аккаунты", callback_data="accounts_menu_0")],
            [InlineKeyboardButton(text="🌐 Прокси", callback_data="proxies_menu_0")],
            [InlineKeyboardButton(text="💬 Шаблоны", callback_data="pastes_menu_0")],
            [InlineKeyboardButton(text="📝 Логи", callback_data="logs_menu")],
            [InlineKeyboardButton(text="🚨 Ошибки", callback_data="errors_menu")],
            [InlineKeyboardButton(text="⚙️ Настройки", callback_data="settings_menu")],
        ]
    )

# ----------------- АККАУНТЫ -----------------
def get_accounts_menu(page=0):
    accounts = file_lines(EMAIL_LIST_PATH)
    total = len(accounts)
    start = page * EMAILS_PER_PAGE
    end = start + EMAILS_PER_PAGE
    rows = []
    for idx, acc in enumerate(accounts[start:end], start=start):
        rows.append([InlineKeyboardButton(text=f"❌ {acc}", callback_data=f"account_del_{idx}_{page}")])
    nav = []
    if start > 0:
        nav.append(InlineKeyboardButton(text="⬅️", callback_data=f"accounts_menu_{page-1}"))
    if end < total:
        nav.append(InlineKeyboardButton(text="➡️", callback_data=f"accounts_menu_{page+1}"))
    if nav:
        rows.append(nav)
    rows.append([InlineKeyboardButton(text="➕ Добавить", callback_data="account_add")])
    rows.append([InlineKeyboardButton(text="⬅️ В меню", callback_data="back_main")])
    return InlineKeyboardMarkup(inline_keyboard=rows)

@dp.callback_query()
async def universal_callback(call: types.CallbackQuery):
    # Универсальный обработчик, чтобы не было ошибок с фильтрами
    data = call.data

    if data.startswith("accounts_menu_"):
        page = int(data.split("_")[-1])
        await call.message.edit_text("Список аккаунтов:", reply_markup=get_accounts_menu(page))

    elif data.startswith("account_del_"):
        _, _, idx, page = data.split("_")
        idx, page = int(idx), int(page)
        accounts = file_lines(EMAIL_LIST_PATH)
        if idx < len(accounts):
            acc = accounts.pop(idx)
            save_lines(EMAIL_LIST_PATH, accounts)
            await call.answer(f"Удалён: {acc}")
        await call.message.edit_text("Список аккаунтов:", reply_markup=get_accounts_menu(page))

    elif data == "account_add":
        await call.message.edit_text(
            "Пришлите одним сообщением email:password (или несколько, каждый на новой строке):",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="⬅️ В аккаунты", callback_data="accounts_menu_0")]])
        )

    elif data.startswith("proxies_menu_"):
        page = int(data.split("_")[-1])
        await call.message.edit_text("Список прокси:", reply_markup=get_proxies_menu(page))

    elif data.startswith("proxy_del_"):
        _, _, idx, page = data.split("_")
        idx, page = int(idx), int(page)
        proxies = file_lines(PROXY_LIST_PATH)
        if idx < len(proxies):
            pr = proxies.pop(idx)
            save_lines(PROXY_LIST_PATH, proxies)
            await call.answer(f"Удалён: {pr}")
        await call.message.edit_text("Список прокси:", reply_markup=get_proxies_menu(page))

    elif data == "proxy_add":
        await call.message.edit_text(
            "Пришлите список прокси (ip:port), каждый на новой строке:",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="⬅️ В прокси", callback_data="proxies_menu_0")]])
        )

    elif data.startswith("pastes_menu_"):
        page = int(data.split("_")[-1])
        await call.message.edit_text("Список шаблонов:", reply_markup=get_pastes_menu(page))

    elif data.startswith("paste_view_"):
        _, _, idx, page = data.split("_")
        idx, page = int(idx), int(page)
        pastes = get_pastes()
        if idx < len(pastes):
            await call.message.edit_text(
                f"Текст шаблона:\n\n{pastes[idx]}",
                reply_markup=InlineKeyboardMarkup(
                    inline_keyboard=[
                        [InlineKeyboardButton(text="⬅️ Назад", callback_data=f"pastes_menu_{page}")]
                    ]
                )
            )

    elif data.startswith("paste_del_"):
        _, _, idx, page = data.split("_")
        idx, page = int(idx), int(page)
        pastes = get_pastes()
        if idx < len(pastes):
            p = pastes.pop(idx)
            save_pastes(pastes)
            await call.answer("Шаблон удалён")
        await call.message.edit_text("Список шаблонов:", reply_markup=get_pastes_menu(page))

    elif data == "paste_add":
        await call.message.edit_text(
            "Пришлите текст нового шаблона:",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="⬅️ В шаблоны", callback_data="pastes_menu_0")]])
        )

    elif data == "logs_menu":
        lines = file_lines(LOG_PATH)[-10:]
        text = "Последние 10 строк лога:" if lines else "Лог пуст."
        text += "\n\n" + "\n".join(lines)
        await call.message.edit_text(text, reply_markup=get_logs_menu())

    elif data == "logs_clear":
        save_lines(LOG_PATH, [])
        await call.answer("Логи очищены.")
        await call.message.edit_text("Лог пуст.", reply_markup=get_logs_menu())

    elif data == "errors_menu":
        lines = file_lines(ERRORS_PATH)[-10:]
        text = "Последние 10 ошибок:" if lines else "Ошибок нет."
        text += "\n\n" + "\n".join(lines)
        await call.message.edit_text(text, reply_markup=get_errors_menu())

    elif data == "errors_clear":
        save_lines(ERRORS_PATH, [])
        await call.answer("Ошибки очищены.")
        await call.message.edit_text("Ошибок нет.", reply_markup=get_errors_menu())

    elif data == "settings_menu":
        await call.message.edit_text("Настройки (функции в разработке):", reply_markup=get_settings_menu())

    elif data == "dummy":
        await call.answer("Пункт в разработке.")

    elif data == "back_main":
        await call.message.edit_text("Главное меню:", reply_markup=get_main_menu())

    elif data == "start_mailing":
        from monitoring.mailing_control import start_mailing
        status = await start_mailing()
        await call.message.edit_text(status, reply_markup=get_main_menu())

    elif data == "stop_mailing":
        from monitoring.mailing_control import stop_mailing
        status = await stop_mailing()
        await call.message.edit_text(status, reply_markup=get_main_menu())

    elif data == "stats":
        from monitoring.mailing_control import get_stats
        stats = get_stats()
        await call.message.edit_text(stats, reply_markup=get_main_menu())

# ----------- Меню для разделов -----------
def get_proxies_menu(page=0):
    proxies = file_lines(PROXY_LIST_PATH)
    total = len(proxies)
    start = page * PROXIES_PER_PAGE
    end = start + PROXIES_PER_PAGE
    rows = []
    for idx, pr in enumerate(proxies[start:end], start=start):
        rows.append([InlineKeyboardButton(text=f"❌ {pr}", callback_data=f"proxy_del_{idx}_{page}")])
    nav = []
    if start > 0:
        nav.append(InlineKeyboardButton(text="⬅️", callback_data=f"proxies_menu_{page-1}"))
    if end < total:
        nav.append(InlineKeyboardButton(text="➡️", callback_data=f"proxies_menu_{page+1}"))
    if nav:
        rows.append(nav)
    rows.append([InlineKeyboardButton(text="➕ Добавить", callback_data="proxy_add")])
    rows.append([InlineKeyboardButton(text="⬅️ В меню", callback_data="back_main")])
    return InlineKeyboardMarkup(inline_keyboard=rows)

def get_pastes_menu(page=0):
    pastes = get_pastes()
    total = len(pastes)
    start = page * PASTES_PER_PAGE
    end = start + PASTES_PER_PAGE
    rows = []
    for idx, p in enumerate(pastes[start:end], start=start):
        rows.append([
            InlineKeyboardButton(text=f"📄 {p[:25]}...", callback_data=f"paste_view_{idx}_{page}"),
            InlineKeyboardButton(text="❌", callback_data=f"paste_del_{idx}_{page}")
        ])
    nav = []
    if start > 0:
        nav.append(InlineKeyboardButton(text="⬅️", callback_data=f"pastes_menu_{page-1}"))
    if end < total:
        nav.append(InlineKeyboardButton(text="➡️", callback_data=f"pastes_menu_{page+1}"))
    if nav:
        rows.append(nav)
    rows.append([InlineKeyboardButton(text="➕ Добавить", callback_data="paste_add")])
    rows.append([InlineKeyboardButton(text="⬅️ В меню", callback_data="back_main")])
    return InlineKeyboardMarkup(inline_keyboard=rows)

def get_logs_menu():
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="🗑 Очистить логи", callback_data="logs_clear")],
            [InlineKeyboardButton(text="⬅️ В меню", callback_data="back_main")]
        ]
    )

def get_errors_menu():
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="🗑 Очистить ошибки", callback_data="errors_clear")],
            [InlineKeyboardButton(text="⬅️ В меню", callback_data="back_main")]
        ]
    )

def get_settings_menu():
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="⚡️ Лимиты (в разработке)", callback_data="dummy")],
            [InlineKeyboardButton(text="⏱ Задержки (в разработке)", callback_data="dummy")],
            [InlineKeyboardButton(text="⬅️ В меню", callback_data="back_main")]
        ]
    )

# ----------------- СООБЩЕНИЯ ДЛЯ ДОБАВЛЕНИЯ -----------------
@dp.message(F.reply_to_message, F.reply_to_message.text.startswith("Пришлите одним сообщением email:password"))
async def account_save(msg: types.Message):
    lines = [l.strip() for l in msg.text.splitlines() if l.strip()]
    append_lines(EMAIL_LIST_PATH, lines)
    await msg.answer(
        f"Добавлено {len(lines)} аккаунтов.",
        reply_markup=get_accounts_menu(0),
        reply_markup_message_id=None
    )

@dp.message(F.reply_to_message, F.reply_to_message.text.startswith("Пришлите список прокси"))
async def proxy_save(msg: types.Message):
    lines = [l.strip() for l in msg.text.splitlines() if l.strip()]
    append_lines(PROXY_LIST_PATH, lines)
    await msg.answer(
        f"Добавлено {len(lines)} прокси.",
        reply_markup=get_proxies_menu(0),
        reply_markup_message_id=None
    )

@dp.message(F.reply_to_message, F.reply_to_message.text.startswith("Пришлите текст нового шаблона"))
async def paste_save(msg: types.Message):
    text = msg.text.strip()
    if text:
        pastes = get_pastes()
        pastes.append(text)
        save_pastes(pastes)
        await msg.answer(
            "Шаблон добавлен.",
            reply_markup=get_pastes_menu(0),
            reply_markup_message_id=None
        )

# ----------------- /start и очистка клавиатуры -----------------
@dp.message(F.text == "/start")
async def start_cmd(msg: types.Message):
    if msg.from_user.id not in ADMIN_IDS:
        return await msg.answer("Нет доступа", reply_markup=ReplyKeyboardRemove())
    # Удаляем все старые клавиатуры и предлагаем только инлайн-меню
    await msg.answer(
        "Добро пожаловать! Выберите действие:",
        reply_markup=get_main_menu()
    )
    # Удаляем любые старые клавиатуры у пользователя
    await msg.answer(".", reply_markup=ReplyKeyboardRemove())
    await msg.delete()

# ----------------- Удаление /любых/ команд и ReplyKeyboard -----------------
@dp.message(F.text.regexp(r"^/"))
async def block_commands(msg: types.Message):
    try:
        await msg.delete()
    except Exception:
        pass

# ----------------- Очищаем любые старые клавиатуры -----------------
@dp.message()
async def fallback(msg: types.Message):
    await msg.answer(
        "Используйте только меню под сообщением.",
        reply_markup=ReplyKeyboardRemove()
    )

async def start_bot():
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(start_bot())