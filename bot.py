import logging
import json
import os
import asyncio
from telegram import Update
from telegram.ext import (
    ApplicationBuilder, CommandHandler, CallbackQueryHandler,
    ContextTypes, MessageHandler, filters, ConversationHandler
)
from filters import FilterSettings, get_filter_keyboard, filter_to_text
from parser import WallapopParser

TELEGRAM_TOKEN = "7512529507:AAHga264aQDpBF9fsSHrvDVgInkjwfPJ96o"
USER_ID = 7541702112  # Ваш Telegram user_id

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

CHOOSE_FILTER, SET_FILTER_VALUE = range(2)
user_filters = {}
SEEN_FILE = "seen.json"

def load_seen():
    if not os.path.exists(SEEN_FILE):
        return set()
    try:
        with open(SEEN_FILE, "r", encoding="utf-8") as f:
            data = f.read().strip()
            if not data:
                return set()
            return set(json.loads(data))
    except Exception:
        return set()

def save_seen(seen):
    with open(SEEN_FILE, "w", encoding="utf-8") as f:
        json.dump(list(seen), f)

seen_ads = load_seen()

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != USER_ID:
        await update.message.reply_text("Нет доступа.")
        return
    await update.message.reply_text(
        "Привет! Я бот для поиска новых объявлений Wallapop.\n"
        "Используй /filters для выбора фильтров.\n"
        "После выбора фильтров отправь /go для поиска новых объявлений."
    )

async def filters_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != USER_ID:
        await update.message.reply_text("Нет доступа.")
        return ConversationHandler.END
    user_id = update.effective_user.id
    user_filters[user_id] = FilterSettings()
    await update.message.reply_text(
        "🔎 Доступные фильтры:\nВыберите фильтр для установки значения:",
        reply_markup=get_filter_keyboard()
    )
    return CHOOSE_FILTER

async def choose_filter(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    key = query.data
    context.user_data["selected_filter"] = key
    await query.edit_message_text(
        text=f"Введите значение для фильтра: {filter_to_text(key)}"
    )
    return SET_FILTER_VALUE

async def set_filter_value(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    key = context.user_data["selected_filter"]
    val = update.message.text.strip()
    fs = user_filters.get(user_id)
    if not fs:
        await update.message.reply_text("Ошибка: фильтры не найдены. Используйте /filters.")
        return ConversationHandler.END
    try:
        ok = fs.set(key, val)
    except Exception as ex:
        await update.message.reply_text(f"Некорректное значение! Ошибка: {ex}")
        return SET_FILTER_VALUE
    if not ok:
        await update.message.reply_text("Некорректное значение! Повторите ввод.")
        return SET_FILTER_VALUE
    await update.message.reply_text(
        f"Фильтр \"{filter_to_text(key)}\" установлен на: {val}\n"
        "Можешь выбрать ещё фильтр (/filters) или отправить /go для поиска."
    )
    return ConversationHandler.END

async def go_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != USER_ID:
        await update.message.reply_text("Нет доступа.")
        return
    user_id = update.effective_user.id
    fs = user_filters.get(user_id)
    if not fs:
        await update.message.reply_text("Сначала выберите фильтры командой /filters.")
        return
    await update.message.reply_text("🔄 Ищу новые объявления, подождите...")

    parser = WallapopParser(domain=fs.domain)
    new_count = 0
    async for ad in parser.parse_stream(max_pages=2):
        passed = fs.apply([ad])
        if passed and ad.get('url') not in seen_ads:
            msg = (
                f"🔹 <b>{ad.get('title')}</b>\n"
                f"💸 Цена: {ad.get('price')}\n"
                f"📍 Локация: {ad.get('location','?')}\n"
                f"🚚 Доставка: {'вкл.' if ad.get('delivery') else 'нет'}\n"
                f"📝 Описание: {ad.get('desc','-')}\n\n"
                f"👤 Продавец: {ad.get('seller_name','?')}\n"
                f"⭐️ Оценок: {ad.get('seller_rating','?')}\n"
                f"📥 Покупок: {ad.get('seller_purchases','?')}\n"
                f"📤 Продаж: {ad.get('seller_sales','?')}\n"
                f"🔗 <a href='{ad.get('chat_url','')}'>Перейти в чат</a>\n\n"
                f"📅 Опубликовано: {ad.get('post_date','?')}\n"
                f"👀 Просмотров: {ad.get('views','?')}\n"
                f"📑 Объявлений: {ad.get('seller_ads_count','?')}\n"
                f"🗓 Зарегистрирован: {ad.get('seller_reg_date','?')}\n\n"
                f"🔗 <a href='{ad.get('url','')}'>Перейти к объявлению</a>\n"
                f"🔗 <a href='{ad.get('photo','')}'>Перейти к фото</a>"
            )
            try:
                await update.message.reply_html(msg, disable_web_page_preview=True)
            except Exception as ex:
                print(f"Ошибка отправки сообщения: {ex}")
            seen_ads.add(ad.get('url'))
            new_count += 1
            save_seen(seen_ads)
    if new_count == 0:
        await update.message.reply_text("Новых объявлений по фильтрам не найдено.")
    else:
        await update.message.reply_text(f"Показано новых объявлений: {new_count}")

def main():
    app = ApplicationBuilder().token(TELEGRAM_TOKEN).build()
    conv_handler = ConversationHandler(
        entry_points=[CommandHandler("filters", filters_command)],
        states={
            CHOOSE_FILTER: [CallbackQueryHandler(choose_filter)],
            SET_FILTER_VALUE: [MessageHandler(filters.TEXT & ~filters.COMMAND, set_filter_value)],
        },
        fallbacks=[],
    )
    app.add_handler(CommandHandler("start", start))
    app.add_handler(conv_handler)
    app.add_handler(CommandHandler("go", go_command))
    app.run_polling()

if __name__ == "__main__":
    main()
