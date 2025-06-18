import asyncio

# Импортируй объект bot из tg_bot, чтобы можно было отправлять сообщения
from monitoring.tg_bot import bot, ADMIN_IDS

# Глобальная переменная для этапа рассылки
CURRENT_STAGE = "Ожидание запуска"
CURRENT_PROGRESS = ""

# Примерная функция запуска рассылки
async def start_mailing():
    global CURRENT_STAGE, CURRENT_PROGRESS
    CURRENT_STAGE = "Авторизация аккаунтов"
    CURRENT_PROGRESS = ""
    for admin_id in ADMIN_IDS:
        await bot.send_message(admin_id, "Рассылка запущена!\nЭтап: Авторизация аккаунтов")
    await asyncio.sleep(2)  # тут должна быть авторизация аккаунтов

    CURRENT_STAGE = "Парсинг пользователей"
    for admin_id in ADMIN_IDS:
        await bot.send_message(admin_id, "Этап: Парсинг пользователей")
    await asyncio.sleep(2)  # тут должен быть парсер

    CURRENT_STAGE = "Рассылка сообщений"
    total_msgs = 100  # пример
    for i in range(1, total_msgs + 1):
        # тут твоя логика отправки сообщений
        CURRENT_PROGRESS = f"{i}/{total_msgs} сообщений отправлено"
        if i % 10 == 0 or i == total_msgs:
            for admin_id in ADMIN_IDS:
                await bot.send_message(
                    admin_id,
                    f"Этап: Рассылка сообщений\n{CURRENT_PROGRESS}"
                )
        await asyncio.sleep(0.1)  # эмулирует задержку между сообщениями

    CURRENT_STAGE = "Рассылка завершена"
    CURRENT_PROGRESS = ""
    for admin_id in ADMIN_IDS:
        await bot.send_message(admin_id, "Рассылка завершена!")

    return "Рассылка завершена!"

# Остановка рассылки — для примера
async def stop_mailing():
    global CURRENT_STAGE, CURRENT_PROGRESS
    CURRENT_STAGE = "Остановлено"
    CURRENT_PROGRESS = ""
    for admin_id in ADMIN_IDS:
        await bot.send_message(admin_id, "Рассылка остановлена!")
    return "Рассылка остановлена!"

# Получить текущий статус
def get_stats():
    global CURRENT_STAGE, CURRENT_PROGRESS
    return f"Статус рассылки:\nЭтап: {CURRENT_STAGE}\n{CURRENT_PROGRESS if CURRENT_PROGRESS else ''}"