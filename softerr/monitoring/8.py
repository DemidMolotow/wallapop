import asyncio
import os

from aiogram import Bot, Dispatcher, types, F
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from config import TELEGRAM_TOKEN, ADMIN_IDS, PROXY_LIST_PATH, EMAIL_LIST_PATH, PASTES_PATH

bot = Bot(token=TELEGRAM_TOKEN)
dp = Dispatcher()

EMAILS_PER_PAGE = 10
PROXIES_PER_PAGE = 10
PASTES_PER_PAGE = 5

LOG_PATH = "logs.txt"      # Пропиши путь к логам, если нужен другой
ERRORS_PATH = "errors.txt" # Пропиши путь к ошибкам, если нужен другой

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
    # Пасты храним с разделителем "---"
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
            [InlineKeyboardButton("▶️ Запуск рассылки", callback_data="start_mailing")],
            [InlineKeyboardButton("⏹ Стоп рассылки", callback_data="stop_mailing")],
            [InlineKeyboardButton("📊 Статистика", callback_data="stats")],
            [InlineKeyboardButton("📋 Аккаунты", callback_data="accounts_menu_0")],
            [InlineKeyboardButton("🌐 Прокси", callback_data="proxies_menu_0")],
            [InlineKeyboardButton("💬 Шаблоны", callback_data="pastes_menu_0")],
            [InlineKeyboardButton("📝 Логи", callback_data="logs_menu")],
            [InlineKeyboardButton("🚨 Ошибки", callback_data="errors_menu")],
            [InlineKeyboardButton("⚙️ Настройки", callback_data="settings_menu")],
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
        rows.append([InlineKeyboardButton(f"❌ {acc}", callback_data=f"account_del_{idx}_{page}")])
    nav = []
    if start > 0:
        nav.append(InlineKeyboardButton("⬅️", callback_data=f"accounts_menu_{page-1}"))
    if end < total:
        nav.append(InlineKeyboardButton("➡️", callback_data=f"accounts_menu_{page+1}"))
    if nav:
        rows.append(nav)
    rows.append([InlineKeyboardButton("➕ Добавить", callback_data="account_add")])
    rows.append([InlineKeyboardButton("⬅️ В меню", callback_data="back_main")])
    return InlineKeyboardMarkup(inline_keyboard=rows)

@dp.callback_query(lambda c: c.data.startswith("accounts_menu_"))
async def accounts_menu(call: types.CallbackQuery):
    page = int(call.data.split("_")[-1])
    await call.message.edit_text("Список аккаунтов:", reply_markup=get_accounts_menu(page))

@dp.callback_query(lambda c: c.data.startswith("account_del_"))
async def account_del(call: types.CallbackQuery):
    _, _, idx, page = call.data.split("_")
    idx, page = int(idx), int(page)
    accounts = file_lines(EMAIL_LIST_PATH)
    if idx < len(accounts):
        acc = accounts.pop(idx)
        save_lines(EMAIL_LIST_PATH, accounts)
        await call.answer(f"Удалён: {acc}")
    await call.message.edit_text("Список аккаунтов:", reply_markup=get_accounts_menu(page))

@dp.callback_query(lambda c: c.data == "account_add")
async def account_add(call: types.CallbackQuery):
    await call.message.edit_text(
        "Пришлите одним сообщением email:password (или несколько, каждый на новой строке):",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton("⬅️ В аккаунты", callback_data="accounts_menu_0")]])
    )

@dp.message(F.reply_to_message, F.reply_to_message.text.startswith("Пришлите одним сообщением email:password"))
async def account_save(msg: types.Message):
    lines = [l.strip() for l in msg.text.splitlines() if l.strip()]
    append_lines(EMAIL_LIST_PATH, lines)
    await msg.answer(f"Добавлено {len(lines)} аккаунтов.", reply_markup=get_accounts_menu(0))

# ----------------- ПРОКСИ -----------------
def get_proxies_menu(page=0):
    proxies = file_lines(PROXY_LIST_PATH)
    total = len(proxies)
    start = page * PROXIES_PER_PAGE
    end = start + PROXIES_PER_PAGE
    rows = []
    for idx, pr in enumerate(proxies[start:end], start=start):
        rows.append([InlineKeyboardButton(f"❌ {pr}", callback_data=f"proxy_del_{idx}_{page}")])
    nav = []
    if start > 0:
        nav.append(InlineKeyboardButton("⬅️", callback_data=f"proxies_menu_{page-1}"))
    if end < total:
        nav.append(InlineKeyboardButton("➡️", callback_data=f"proxies_menu_{page+1}"))
    if nav:
        rows.append(nav)
    rows.append([InlineKeyboardButton("➕ Добавить", callback_data="proxy_add")])
    rows.append([InlineKeyboardButton("⬅️ В меню", callback_data="back_main")])
    return InlineKeyboardMarkup(inline_keyboard=rows)

@dp.callback_query(lambda c: c.data.startswith("proxies_menu_"))
async def proxies_menu(call: types.CallbackQuery):
    page = int(call.data.split("_")[-1])
    await call.message.edit_text("Список прокси:", reply_markup=get_proxies_menu(page))

@dp.callback_query(lambda c: c.data.startswith("proxy_del_"))
async def proxy_del(call: types.CallbackQuery):
    _, _, idx, page = call.data.split("_")
    idx, page = int(idx), int(page)
    proxies = file_lines(PROXY_LIST_PATH)
    if idx < len(proxies):
        pr = proxies.pop(idx)
        save_lines(PROXY_LIST_PATH, proxies)
        await call.answer(f"Удалён: {pr}")
    await call.message.edit_text("Список прокси:", reply_markup=get_proxies_menu(page))

@dp.callback_query(lambda c: c.data == "proxy_add")
async def proxy_add(call: types.CallbackQuery):
    await call.message.edit_text(
        "Пришлите список прокси (ip:port), каждый на новой строке:",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton("⬅️ В прокси", callback_data="proxies_menu_0")]])
    )

@dp.message(F.reply_to_message, F.reply_to_message.text.startswith("Пришлите список прокси"))
async def proxy_save(msg: types.Message):
    lines = [l.strip() for l in msg.text.splitlines() if l.strip()]
    append_lines(PROXY_LIST_PATH, lines)
    await msg.answer(f"Добавлено {len(lines)} прокси.", reply_markup=get_proxies_menu(0))

# ----------------- ПАСТЫ (ШАБЛОНЫ) -----------------
def get_pastes_menu(page=0):
    pastes = get_pastes()
    total = len(pastes)
    start = page * PASTES_PER_PAGE
    end = start + PASTES_PER_PAGE
    rows = []
    for idx, p in enumerate(pastes[start:end], start=start):
        rows.append([
            InlineKeyboardButton(f"📄 {p[:25]}...", callback_data=f"paste_view_{idx}_{page}"),
            InlineKeyboardButton("❌", callback_data=f"paste_del_{idx}_{page}")
        ])
    nav = []
    if start > 0:
        nav.append(InlineKeyboardButton("⬅️", callback_data=f"pastes_menu_{page-1}"))
    if end < total:
        nav.append(InlineKeyboardButton("➡️", callback_data=f"pastes_menu_{page+1}"))
    if nav:
        rows.append(nav)
    rows.append([InlineKeyboardButton("➕ Добавить", callback_data="paste_add")])
    rows.append([InlineKeyboardButton("⬅️ В меню", callback_data="back_main")])
    return InlineKeyboardMarkup(inline_keyboard=rows)

@dp.callback_query(lambda c: c.data.startswith("pastes_menu_"))
async def pastes_menu(call: types.CallbackQuery):
    page = int(call.data.split("_")[-1])
    await call.message.edit_text("Список шаблонов:", reply_markup=get_pastes_menu(page))

@dp.callback_query(lambda c: c.data.startswith("paste_view_"))
async def paste_view(call: types.CallbackQuery):
    _, _, idx, page = call.data.split("_")
    idx, page = int(idx), int(page)
    pastes = get_pastes()
    if idx < len(pastes):
        await call.message.edit_text(
            f"Текст шаблона:\n\n{pastes[idx]}",
            reply_markup=InlineKeyboardMarkup(
                inline_keyboard=[
                    [InlineKeyboardButton("⬅️ Назад", callback_data=f"pastes_menu_{page}")]
                ]
            )
        )

@dp.callback_query(lambda c: c.data.startswith("paste_del_"))
async def paste_del(call: types.CallbackQuery):
    _, _, idx, page = call.data.split("_")
    idx, page = int(idx), int(page)
    pastes = get_pastes()
    if idx < len(pastes):
        p = pastes.pop(idx)
        save_pastes(pastes)
        await call.answer("Шаблон удалён")
    await call.message.edit_text("Список шаблонов:", reply_markup=get_pastes_menu(page))

@dp.callback_query(lambda c: c.data == "paste_add")
async def paste_add(call: types.CallbackQuery):
    await call.message.edit_text(
        "Пришлите текст нового шаблона:",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton("⬅️ В шаблоны", callback_data="pastes_menu_0")]])
    )

@dp.message(F.reply_to_message, F.reply_to_message.text.startswith("Пришлите текст нового шаблона"))
async def paste_save(msg: types.Message):
    text = msg.text.strip()
    if text:
        pastes = get_pastes()
        pastes.append(text)
        save_pastes(pastes)
        await msg.answer("Шаблон добавлен.", reply_markup=get_pastes_menu(0))

# ----------------- ЛОГИ -----------------
def get_logs_menu():
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton("🗑 Очистить логи", callback_data="logs_clear")],
            [InlineKeyboardButton("⬅️ В меню", callback_data="back_main")]
        ]
    )

@dp.callback_query(lambda c: c.data == "logs_menu")
async def logs_menu(call: types.CallbackQuery):
    lines = file_lines(LOG_PATH)[-10:]
    text = "Последние 10 строк лога:" if lines else "Лог пуст."
    text += "\n\n" + "\n".join(lines)
    await call.message.edit_text(text, reply_markup=get_logs_menu())

@dp.callback_query(lambda c: c.data == "logs_clear")
async def logs_clear(call: types.CallbackQuery):
    save_lines(LOG_PATH, [])
    await call.answer("Логи очищены.")
    await call.message.edit_text("Лог пуст.", reply_markup=get_logs_menu())

# ----------------- ОШИБКИ -----------------
def get_errors_menu():
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton("🗑 Очистить ошибки", callback_data="errors_clear")],
            [InlineKeyboardButton("⬅️ В меню", callback_data="back_main")]
        ]
    )

@dp.callback_query(lambda c: c.data == "errors_menu")
async def errors_menu(call: types.CallbackQuery):
    lines = file_lines(ERRORS_PATH)[-10:]
    text = "Последние 10 ошибок:" if lines else "Ошибок нет."
    text += "\n\n" + "\n".join(lines)
    await call.message.edit_text(text, reply_markup=get_errors_menu())

@dp.callback_query(lambda c: c.data == "errors_clear")
async def errors_clear(call: types.CallbackQuery):
    save_lines(ERRORS_PATH, [])
    await call.answer("Ошибки очищены.")
    await call.message.edit_text("Ошибок нет.", reply_markup=get_errors_menu())

# ----------------- НАСТРОЙКИ -----------------
def get_settings_menu():
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton("⚡️ Лимиты (в разработке)", callback_data="dummy")],
            [InlineKeyboardButton("⏱ Задержки (в разработке)", callback_data="dummy")],
            [InlineKeyboardButton("⬅️ В меню", callback_data="back_main")]
        ]
    )

@dp.callback_query(lambda c: c.data == "settings_menu")
async def settings_menu(call: types.CallbackQuery):
    await call.message.edit_text("Настройки (функции в разработке):", reply_markup=get_settings_menu())

@dp.callback_query(lambda c: c.data == "dummy")
async def dummy(call: types.CallbackQuery):
    await call.answer("Пункт в разработке.")

# ----------------- СПЕЦИАЛЬНЫЕ -----------------
@dp.callback_query(lambda c: c.data == "back_main")
async def back_main(call: types.CallbackQuery):
    await call.message.edit_text("Главное меню:", reply_markup=get_main_menu())

# Старт/стоп/стата — интеграция с твоими функциями (оставь как есть)
from monitoring.mailing_control import start_mailing, stop_mailing, get_stats

@dp.callback_query(lambda call: call.data == "start_mailing")
async def handle_start_mailing(call: types.CallbackQuery):
    status = await start_mailing()
    await call.message.edit_text(status, reply_markup=get_main_menu())

@dp.callback_query(lambda call: call.data == "stop_mailing")
async def handle_stop_mailing(call: types.CallbackQuery):
    status = await stop_mailing()
    await call.message.edit_text(status, reply_markup=get_main_menu())

@dp.callback_query(lambda call: call.data == "stats")
async def handle_stats(call: types.CallbackQuery):
    stats = get_stats()
    await call.message.edit_text(stats, reply_markup=get_main_menu())

# Удаляем любые старые команды, кнопки, ReplyKeyboard
@dp.message(F.text.regexp(r"^/"))
async def block_commands(msg: types.Message):
    await msg.delete()

@dp.message()
async def fallback(msg: types.Message):
    await msg.answer("Используйте только меню под сообщением.", reply_markup=get_main_menu())

@dp.message(F.text == "/start")
async def start_cmd(msg: types.Message):
    if msg.from_user.id not in ADMIN_IDS:
        return await msg.answer("Нет доступа")
    await msg.answer("Добро пожаловать! Выберите действие:", reply_markup=get_main_menu())

async def start_bot():
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(start_bot())