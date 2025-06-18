import asyncio

from monitoring.tg_bot import bot, ADMIN_IDS
from messaging.mailing_worker import main_worker, get_current_status, stop_worker

MAILING_RUNNING = False

async def edit_status_msg(chat_id, msg_id, text):
    try:
        await bot.edit_message_text(text, chat_id, msg_id)
    except Exception:
        pass

async def start_mailing():
    global MAILING_RUNNING
    if MAILING_RUNNING:
        return "Рассылка уже идёт!"
    MAILING_RUNNING = True
    status_msg_id = None

    async def status_update_cb():
        status = get_current_status()
        text = f"Статус рассылки:\nЭтап: {status['stage']}\n{status['progress']}"
        nonlocal status_msg_id
        for admin_id in ADMIN_IDS:
            if status_msg_id:
                await edit_status_msg(admin_id, status_msg_id, text)
            else:
                msg = await bot.send_message(admin_id, text)
                status_msg_id = msg.message_id

    await status_update_cb()
    try:
        await main_worker(status_update_cb=status_update_cb)
        await status_update_cb()
    except Exception as ex:
        status = get_current_status()
        text = f"Ошибка рассылки: {ex}\nПоследний статус: {status['stage']}\n{status['progress']}"
        for admin_id in ADMIN_IDS:
            await bot.send_message(admin_id, text)
    finally:
        MAILING_RUNNING = False

    return "Рассылка завершена!"

async def stop_mailing():
    global MAILING_RUNNING
    if MAILING_RUNNING:
        stop_worker()
        return "Останавливаем рассылку..."
    else:
        return "Рассылка не запущена."

def get_stats():
    status = get_current_status()
    return f"Статус рассылки:\nЭтап: {status['stage']}\n{status['progress']}"