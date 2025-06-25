import asyncio
from aiogram import Bot, Dispatcher, types
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton
from config import API_TOKEN, ALLOWED_USERS, ADMIN_CHAT_ID
from modules.register import register_account
from modules.parser import parse_ads
from modules.warmup import warmup_account
from modules.sender import send_message
from modules.account_manager import switch_account, current_account_info

bot = Bot(token=API_TOKEN)
dp = Dispatcher(bot)

# Отправка логов в административный чат
async def log_to_admin(message: str):
    await bot.send_message(ADMIN_CHAT_ID, message)

# Проверка пользователя
async def check_user(message: types.Message):
    if message.from_user.username not in ALLOWED_USERS:
        await message.reply("У вас нет доступа к этому боту.")
        await log_to_admin(f"Попытка доступа от пользователя: {message.from_user.username}")
        return False
    return True

# Главное меню с кнопками
@dp.message_handler(commands=['start'])
async def start_handler(message: types.Message):
    if not await check_user(message):
        return
    
    keyboard = ReplyKeyboardMarkup(resize_keyboard=True)
    keyboard.add(KeyboardButton("Регистрация"))
    keyboard.add(KeyboardButton("Парсинг"))
    keyboard.add(KeyboardButton("Прогрев аккаунта"))
    keyboard.add(KeyboardButton("Отправка сообщений"))
    keyboard.add(KeyboardButton("Сменить аккаунт"))
    
    await message.reply("Выберите действие:", reply_markup=keyboard)
    await log_to_admin(f"Пользователь {message.from_user.username} открыл меню.")

# Обработчик кнопки регистрации
@dp.message_handler(lambda message: message.text == "Регистрация")
async def register_handler(message: types.Message):
    if not await check_user(message):
        return
    
    await message.reply("Начинаю регистрацию...")
    await log_to_admin("Запущена регистрация аккаунта.")
    success = register_account()
    
    if success:
        await message.reply("Аккаунт успешно зарегистрирован!")
        await log_to_admin("Аккаунт успешно зарегистрирован.")
    else:
        await message.reply("Не удалось зарегистрировать аккаунт.")
        await log_to_admin("Ошибка регистрации аккаунта.")

# Обработчик кнопки парсинга
@dp.message_handler(lambda message: message.text == "Парсинг")
async def parse_handler(message: types.Message):
    if not await check_user(message):
        return
    
    await message.reply("Парсинг объявлений...")
    await log_to_admin("Запущен парсинг объявлений.")
    ads = parse_ads()
    
    for ad in ads:
        await message.reply(str(ad))
    await log_to_admin(f"Парсинг завершён. Найдено {len(ads)} объявлений.")

# Обработчик кнопки прогрева аккаунта
@dp.message_handler(lambda message: message.text == "Прогрев аккаунта")
async def warmup_handler(message: types.Message):
    if not await check_user(message):
        return
    
    await message.reply("Прогреваю аккаунт...")
    await log_to_admin("Запущен прогрев аккаунта.")
    result = warmup_account()
    
    await message.reply(f"Прогрев завершён: {result}")
    await log_to_admin("Прогрев завершён.")

# Обработчик кнопки отправки сообщений
@dp.message_handler(lambda message: message.text == "Отправка сообщений")
async def send_handler(message: types.Message):
    if not await check_user(message):
        return
    
    await message.reply("Отправляю сообщения...")
    await log_to_admin("Запущена отправка сообщений.")
    success, limit_reached = send_message()
    
    if success:
        await message.reply("Сообщения успешно отправлены!")
        await log_to_admin("Сообщения успешно отправлены.")
    else:
        if limit_reached:
            await message.reply("Достигнут лимит сообщений. Смена аккаунта...")
            await log_to_admin("Достигнут лимит сообщений. Аккаунт переключён.")
            switch_account()
        else:
            await message.reply("Ошибка отправки сообщений.")
            await log_to_admin("Ошибка отправки сообщений.")

# Обработчик кнопки смены аккаунта
@dp.message_handler(lambda message: message.text == "Сменить аккаунт")
async def switch_account_handler(message: types.Message):
    if not await check_user(message):
        return
    
    switch_account()
    account_info = current_account_info()
    await message.reply(f"Аккаунт успешно переключён. Текущий аккаунт: {account_info}")
    await log_to_admin(f"Аккаунт переключён. Текущий аккаунт: {account_info}")

# Запуск бота
async def main():
    await log_to_admin("Бот запущен.")
    await dp.start_polling()

if __name__ == '__main__':
    asyncio.run(main())
