import asyncio
import logging
from aiogram import Bot, Dispatcher, types
from aiogram.types import CallbackQuery
from aiogram.contrib.fsm_storage.memory import MemoryStorage
from aiogram.dispatcher.filters import Command, Text

from config import load_config
from modules.register import RegisterModule
from modules.parser import ParserModule
from modules.warmup import WarmupModule
from modules.sender import MessageSender
from modules.account_manager import AccountManager
import keyboards as kb
from services import MilanunciosService

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("bot.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# Загружаем конфигурацию
config = load_config()
bot = Bot(token=config.BOT_TOKEN)
dp = Dispatcher(bot, storage=MemoryStorage())

# Инициализация сервисов
account_manager = AccountManager()
register_module = RegisterModule(bot, config.ADMIN_CHAT_ID)
parser_module = ParserModule(bot, config.ADMIN_CHAT_ID)
warmup_module = WarmupModule(bot, config.ADMIN_CHAT_ID)
message_sender = MessageSender(bot, config.ADMIN_CHAT_ID, account_manager, config.MESSAGE_LIMIT)

# Создаем сервис, объединяющий все модули
milanuncios_service = MilanunciosService(
    bot=bot,
    admin_chat_id=config.ADMIN_CHAT_ID,
    account_manager=account_manager,
    register_module=register_module,
    parser_module=parser_module,
    warmup_module=warmup_module,
    message_sender=message_sender
)

# --- ПРОВЕРКА ДОСТУПА ---
async def check_user_access(user_id):
    """Проверка прав доступа к боту"""
    if not user_id:
        return False
    try:
        chat = await bot.get_chat(user_id)
        username = chat.username
        return username in config.ALLOWED_USERS
    except Exception as e:
        logger.error(f"Ошибка проверки доступа: {e}")
        return False

# --- ГЛАВНОЕ МЕНЮ ---
@dp.message_handler(commands=['start'])
async def cmd_start(message: types.Message):
    if not await check_user_access(message.from_user.id):
        await message.answer("У вас нет доступа к этому боту.")
        return
    await message.answer("Добро пожаловать в систему управления Milanuncios!\nВыберите действие:", reply_markup=kb.main_menu())
    await milanuncios_service.log_to_admin(f"Пользователь {message.from_user.username} открыл меню.")

# Отладочный обработчик всех callback запросов
@dp.callback_query_handler(lambda call: True)
async def debug_callback(call: CallbackQuery):
    logger.debug(f"Получен callback: {call.data}")
    # Просто логируем и позволяем другим обработчикам выполнить свою работу
    return False

@dp.callback_query_handler(lambda call: call.data == "back_main")
async def back_main(call: CallbackQuery):
    if not await check_user_access(call.from_user.id):
        await call.answer("У вас нет доступа к этому боту.", show_alert=True)
        return
    await call.message.edit_text("Главное меню:", reply_markup=kb.main_menu())
    await call.answer()  # Обязательный ответ на callback

# --- РАССЫЛКА ---
@dp.callback_query_handler(lambda call: call.data == "start_mailing")
async def start_mailing(call: CallbackQuery):
    if not await check_user_access(call.from_user.id):
        await call.answer("У вас нет доступа к этому боту.", show_alert=True)
        return
    
    result = await milanuncios_service.start_mailing()
    await call.answer(result, show_alert=True)

@dp.callback_query_handler(lambda call: call.data == "stop_mailing")
async def stop_mailing(call: CallbackQuery):
    if not await check_user_access(call.from_user.id):
        await call.answer("У вас нет доступа к этому боту.", show_alert=True)
        return
    
    result = await milanuncios_service.stop_mailing()
    await call.answer(result, show_alert=True)

@dp.callback_query_handler(lambda call: call.data == "stats")
async def stats(call: CallbackQuery):
    if not await check_user_access(call.from_user.id):
        await call.answer("У вас нет доступа к этому боту.", show_alert=True)
        return
    
    stats_text = await milanuncios_service.get_stats()
    await call.answer(stats_text, show_alert=True)

# --- АККАУНТЫ ---
@dp.callback_query_handler(lambda call: call.data.startswith("accounts_menu"))
async def accounts_menu(call: CallbackQuery):
    if not await check_user_access(call.from_user.id):
        await call.answer("У вас нет доступа к этому боту.", show_alert=True)
        return
    
    page = int(call.data.split("_")[-1]) if "_" in call.data and call.data.split("_")[-1].isdigit() else 0
    email_list = milanuncios_service.get_accounts()
    await call.message.edit_text("Список аккаунтов:", reply_markup=kb.accounts_menu(page, email_list))
    await call.answer()

@dp.callback_query_handler(lambda call: call.data == "account_add")
async def account_add(call: CallbackQuery):
    if not await check_user_access(call.from_user.id):
        await call.answer("У вас нет доступа к этому боту.", show_alert=True)
        return
    
    # Запускаем регистрацию нового аккаунта
    await call.answer("Начинаю регистрацию аккаунта...", show_alert=False)
    success = await milanuncios_service.register_new_account()
    if success:
        await call.message.answer("Аккаунт успешно зарегистрирован!")
    else:
        await call.message.answer("Не удалось зарегистрировать аккаунт")

@dp.callback_query_handler(lambda call: call.data.startswith("account_del_"))
async def account_del(call: CallbackQuery):
    if not await check_user_access(call.from_user.id):
        await call.answer("У вас нет доступа к этому боту.", show_alert=True)
        return
    
    parts = call.data.split("_")
    if len(parts) >= 4 and parts[2].isdigit() and parts[3].isdigit():
        idx, page = int(parts[2]), int(parts[3])
        result = await milanuncios_service.delete_account(idx)
        await call.answer(result, show_alert=True)
        
        # Обновляем список аккаунтов
        email_list = milanuncios_service.get_accounts()
        await call.message.edit_text("Список аккаунтов:", reply_markup=kb.accounts_menu(page, email_list))
    else:
        await call.answer("Ошибка обработки команды", show_alert=True)

# --- MILANUNCIOS ---
@dp.callback_query_handler(lambda call: call.data == "milanuncios_menu")
async def milanuncios_menu(call: CallbackQuery):
    if not await check_user_access(call.from_user.id):
        await call.answer("У вас нет доступа к этому боту.", show_alert=True)
        return
    
    await call.message.edit_text("Milanuncios - управление:", reply_markup=kb.milanuncios_menu())
    await call.answer()

@dp.callback_query_handler(lambda call: call.data == "milanuncios_register")
async def milanuncios_register(call: CallbackQuery):
    if not await check_user_access(call.from_user.id):
        await call.answer("У вас нет доступа к этому боту.", show_alert=True)
        return
    
    await call.answer("Начинаю регистрацию аккаунта...", show_alert=False)
    success = await milanuncios_service.register_new_account()
    if success:
        await call.message.answer("Аккаунт успешно зарегистрирован!")
    else:
        await call.message.answer("Не удалось зарегистрировать аккаунт")

@dp.callback_query_handler(lambda call: call.data == "milanuncios_parse")
async def milanuncios_parse(call: CallbackQuery):
    if not await check_user_access(call.from_user.id):
        await call.answer("У вас нет доступа к этому боту.", show_alert=True)
        return
    
    await call.answer("Начинаю парсинг объявлений...", show_alert=False)
    ads = await milanuncios_service.parse_ads()
    
    if ads:
        text = f"Найдено {len(ads)} объявлений.\n\nПримеры:"
        for ad in ads[:3]:  # Показываем первые 3 объявления
            text += f"\n\n📌 {ad['title']}\n💰 {ad['price']}\n📍 {ad['location']}"
        
        if len(ads) > 3:
            text += f"\n\n...и еще {len(ads) - 3} объявлений"
            
        await call.message.answer(text)
    else:
        await call.message.answer("Не удалось найти объявления.")

@dp.callback_query_handler(lambda call: call.data == "milanuncios_warmup")
async def milanuncios_warmup(call: CallbackQuery):
    if not await check_user_access(call.from_user.id):
        await call.answer("У вас нет доступа к этому боту.", show_alert=True)
        return
    
    await call.answer("Начинаю прогрев аккаунта...", show_alert=False)
    result = await milanuncios_service.warmup_account()
    await call.message.answer(f"Результат прогрева: {result}")

@dp.callback_query_handler(lambda call: call.data == "milanuncios_send")
async def milanuncios_send(call: CallbackQuery):
    if not await check_user_access(call.from_user.id):
        await call.answer("У вас нет доступа к этому боту.", show_alert=True)
        return
    
    await call.answer("Начинаю отправку сообщений...", show_alert=False)
    success, limit_reached = await milanuncios_service.send_message()
    
    if success:
        await call.message.answer("Сообщения успешно отправлены!")
    else:
        if limit_reached:
            await call.message.answer("Достигнут лимит сообщений. Требуется смена аккаунта.")
        else:
            await call.message.answer("Ошибка отправки сообщений.")

@dp.callback_query_handler(lambda call: call.data == "milanuncios_switch")
async def milanuncios_switch(call: CallbackQuery):
    if not await check_user_access(call.from_user.id):
        await call.answer("У вас нет доступа к этому боту.", show_alert=True)
        return
    
    await call.answer("Переключаю аккаунт...", show_alert=False)
    account = await milanuncios_service.switch_account()
    if account:
        await call.message.answer(f"Аккаунт успешно переключён. Текущий аккаунт: {account}")
    else:
        await call.message.answer("Не удалось переключить аккаунт. Возможно, активных аккаунтов больше нет.")

@dp.callback_query_handler(lambda call: call.data == "milanuncios_list")
async def milanuncios_list(call: CallbackQuery):
    if not await check_user_access(call.from_user.id):
        await call.answer("У вас нет доступа к этому боту.", show_alert=True)
        return
    
    accounts = milanuncios_service.get_accounts()
    current = milanuncios_service.get_current_account()
    
    if not accounts:
        text = "Нет доступных аккаунтов."
    else:
        text = "Список аккаунтов Milanuncios:\n\n"
        for i, account in enumerate(accounts):
            status = "✅ АКТИВНЫЙ" if account["status"] == "active" else "❌ НЕАКТИВНЫЙ"
            current_marker = "👉 " if current and account["email"] == current else ""
            text += f"{current_marker}{i+1}. {account['email']} - {status}\n"
    
    await call.message.edit_text(text, reply_markup=kb.milanuncios_menu())
    await call.answer()

# --- ПРОКСИ ---
@dp.callback_query_handler(lambda call: call.data.startswith("proxies_menu"))
async def proxies_menu(call: CallbackQuery):
    if not await check_user_access(call.from_user.id):
        await call.answer("У вас нет доступа к этому боту.", show_alert=True)
        return
    
    page = int(call.data.split("_")[-1]) if "_" in call.data and call.data.split("_")[-1].isdigit() else 0
    proxy_list = milanuncios_service.get_proxies()
    await call.message.edit_text("Список прокси:", reply_markup=kb.proxies_menu(page, proxy_list))
    await call.answer()

@dp.callback_query_handler(lambda call: call.data == "proxy_add")
async def proxy_add(call: CallbackQuery):
    if not await check_user_access(call.from_user.id):
        await call.answer("У вас нет доступа к этому боту.", show_alert=True)
        return
    
    result = await milanuncios_service.add_proxy()
    await call.answer("Прокси добавлен", show_alert=True)
    # Обновляем список прокси
    proxy_list = milanuncios_service.get_proxies()
    await call.message.edit_text("Список прокси:", reply_markup=kb.proxies_menu(0, proxy_list))

@dp.callback_query_handler(lambda call: call.data.startswith("proxy_del_"))
async def proxy_del(call: CallbackQuery):
    if not await check_user_access(call.from_user.id):
        await call.answer("У вас нет доступа к этому боту.", show_alert=True)
        return
    
    parts = call.data.split("_")
    if len(parts) >= 4 and parts[2].isdigit() and parts[3].isdigit():
        idx, page = int(parts[2]), int(parts[3])
        result = await milanuncios_service.delete_proxy(idx)
        await call.answer(result, show_alert=True)
        
        # Обновляем список прокси
        proxy_list = milanuncios_service.get_proxies()
        await call.message.edit_text("Список прокси:", reply_markup=kb.proxies_menu(page, proxy_list))
    else:
        await call.answer("Ошибка обработки команды", show_alert=True)

# --- ШАБЛОНЫ ---
@dp.callback_query_handler(lambda call: call.data.startswith("pastes_menu"))
async def pastes_menu(call: CallbackQuery):
    if not await check_user_access(call.from_user.id):
        await call.answer("У вас нет доступа к этому боту.", show_alert=True)
        return
    
    page = int(call.data.split("_")[-1]) if "_" in call.data and call.data.split("_")[-1].isdigit() else 0
    paste_list = milanuncios_service.get_message_templates()
    await call.message.edit_text("Список шаблонов:", reply_markup=kb.pastes_menu(page, paste_list))
    await call.answer()

@dp.callback_query_handler(lambda call: call.data == "paste_add")
async def paste_add(call: CallbackQuery):
    if not await check_user_access(call.from_user.id):
        await call.answer("У вас нет доступа к этому боту.", show_alert=True)
        return
    
    result = await milanuncios_service.add_message_template()
    await call.answer("Шаблон добавлен", show_alert=True)
    # Обновляем список шаблонов
    paste_list = milanuncios_service.get_message_templates()
    await call.message.edit_text("Список шаблонов:", reply_markup=kb.pastes_menu(0, paste_list))

@dp.callback_query_handler(lambda call: call.data.startswith("paste_del_"))
async def paste_del(call: CallbackQuery):
    if not await check_user_access(call.from_user.id):
        await call.answer("У вас нет доступа к этому боту.", show_alert=True)
        return
    
    parts = call.data.split("_")
    if len(parts) >= 4 and parts[2].isdigit() and parts[3].isdigit():
        idx, page = int(parts[2]), int(parts[3])
        result = await milanuncios_service.delete_message_template(idx)
        await call.answer(result, show_alert=True)
        
        # Обновляем список шаблонов
        paste_list = milanuncios_service.get_message_templates()
        await call.message.edit_text("Список шаблонов:", reply_markup=kb.pastes_menu(page, paste_list))
    else:
        await call.answer("Ошибка обработки команды", show_alert=True)

# --- ВОРКЕРЫ ---
@dp.callback_query_handler(lambda call: call.data == "workers_menu")
async def workers_menu(call: CallbackQuery):
    if not await check_user_access(call.from_user.id):
        await call.answer("У вас нет доступа к этому боту.", show_alert=True)
        return
    
    await call.message.edit_text("Меню воркеров:", reply_markup=kb.workers_menu())
    await call.answer()

@dp.callback_query_handler(lambda call: call.data == "workers_start")
async def workers_start(call: CallbackQuery):
    if not await check_user_access(call.from_user.id):
        await call.answer("У вас нет доступа к этому боту.", show_alert=True)
        return
    
    result = await milanuncios_service.start_workers()
    await call.answer(result, show_alert=True)

@dp.callback_query_handler(lambda call: call.data == "workers_stop_all")
async def workers_stop_all(call: CallbackQuery):
    if not await check_user_access(call.from_user.id):
        await call.answer("У вас нет доступа к этому боту.", show_alert=True)
        return
    
    result = await milanuncios_service.stop_all_workers()
    await call.answer(result, show_alert=True)

@dp.callback_query_handler(lambda call: call.data == "workers_list")
async def workers_list(call: CallbackQuery):
    if not await check_user_access(call.from_user.id):
        await call.answer("У вас нет доступа к этому боту.", show_alert=True)
        return
    
    await call.message.edit_text("Список воркеров:", reply_markup=kb.workers_list_menu(milanuncios_service.get_workers()))
    await call.answer()

@dp.callback_query_handler(lambda call: call.data.endswith("_menu") and "worker_" in call.data)
async def worker_menu(call: CallbackQuery):
    if not await check_user_access(call.from_user.id):
        await call.answer("У вас нет доступа к этому боту.", show_alert=True)
        return
    
    parts = call.data.split("_")
    if len(parts) >= 3 and parts[1].isdigit():
        worker_id = int(parts[1])
        workers = milanuncios_service.get_workers()
        
        if worker_id < len(workers):
            await call.message.edit_text(f"Меню {workers[worker_id]}:", reply_markup=kb.worker_actions_menu(worker_id))
            await call.answer()
        else:
            await call.answer("Воркер не найден", show_alert=True)
    else:
        await call.answer("Ошибка обработки команды", show_alert=True)

@dp.callback_query_handler(lambda call: "_start" in call.data or "_stop" in call.data or "_status" in call.data or "_logs" in call.data or "_delete" in call.data)
async def worker_action(call: CallbackQuery):
    if not await check_user_access(call.from_user.id):
        await call.answer("У вас нет доступа к этому боту.", show_alert=True)
        return
    
    parts = call.data.split("_")
    if len(parts) >= 3 and parts[0] == "worker" and parts[1].isdigit():
        worker_id = int(parts[1])
        action = parts[2]
        result = await milanuncios_service.worker_action(worker_id, action)
        await call.answer(result, show_alert=True)
    else:
        await call.answer("Ошибка обработки команды", show_alert=True)

# --- ЛОГИ / ОШИБКИ / НАСТРОЙКИ ---
@dp.callback_query_handler(lambda call: call.data == "logs_menu")
async def logs_menu(call: CallbackQuery):
    if not await check_user_access(call.from_user.id):
        await call.answer("У вас нет доступа к этому боту.", show_alert=True)
        return
    
    logs = await milanuncios_service.get_logs()
    await call.message.edit_text(logs, reply_markup=kb.main_menu())
    await call.answer()

@dp.callback_query_handler(lambda call: call.data == "errors_menu")
async def errors_menu(call: CallbackQuery):
    if not await check_user_access(call.from_user.id):
        await call.answer("У вас нет доступа к этому боту.", show_alert=True)
        return
    
    errors = await milanuncios_service.get_errors()
    await call.message.edit_text(errors, reply_markup=kb.main_menu())
    await call.answer()

@dp.callback_query_handler(lambda call: call.data == "settings_menu")
async def settings_menu(call: CallbackQuery):
    if not await check_user_access(call.from_user.id):
        await call.answer("У вас нет доступа к этому боту.", show_alert=True)
        return
    
    settings = await milanuncios_service.get_settings()
    await call.message.edit_text(settings, reply_markup=kb.settings_menu())
    await call.answer()

@dp.callback_query_handler(lambda call: call.data.startswith("settings_"))
async def settings_action(call: CallbackQuery):
    if not await check_user_access(call.from_user.id):
        await call.answer("У вас нет доступа к этому боту.", show_alert=True)
        return
    
    setting_name = call.data.replace("settings_", "")
    result = await milanuncios_service.update_setting(setting_name)
    await call.answer(f"Настройка {setting_name} изменена", show_alert=True)

# --- Обработчик неизвестных callback запросов ---
@dp.callback_query_handler(lambda call: True)
async def unknown_callback(call: CallbackQuery):
    logger.warning(f"Неизвестный callback_data: {call.data}")
    await call.answer(f"Кнопка {call.data} еще не реализована", show_alert=True)

async def on_startup(_):
    """Действия при запуске бота"""
    logger.info("Бот запущен!")
    await milanuncios_service.log_to_admin("Бот запущен!")

async def on_shutdown(_):
    """Действия при остановке бота"""
    logger.info("Бот остановлен!")

# Функция запуска бота
async def main():
    try:
        # Запуск бота
        await on_startup(None)
        await dp.start_polling(reset_webhook=True, timeout=20)
    except Exception as e:
        logger.error(f"Ошибка при запуске бота: {e}")
    finally:
        await on_shutdown(None)

if __name__ == "__main__":
    asyncio.run(main())
