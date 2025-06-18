import asyncio
from messaging.mailing_worker import main_worker
from db.stats import load_stats

running = False
main_task = None

async def start_mailing():
    global running, main_task
    if running:
        return "Рассылка уже запущена!"
    running = True
    main_task = asyncio.create_task(main_worker())
    return "Рассылка запущена!"

async def stop_mailing():
    global running, main_task
    running = False
    if main_task:
        main_task.cancel()
        main_task = None
    return "Рассылка остановлена!"

def get_stats():
    stats = load_stats()
    return f"Зарегистрировано: {stats.get('registered', 0)}\n"\
           f"Сообщений отправлено: {stats.get('messages_sent', 0)}\n"\
           f"SMS-запросов: {stats.get('sms_requests', 0)}\n"\
           f"Ошибок: {stats.get('errors', 0)}"