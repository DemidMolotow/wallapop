import asyncio
from messaging.mailing_worker import register_and_send
from mail_manager.manager import load_email_accounts
from proxy_manager.manager import get_random_proxy
from utils import load_lines
from config import PASTES_PATH, EMAIL_LIST_PATH, MAX_WORKERS
from logs.logger import setup_logger

logger = setup_logger("async_worker")

async def worker(email, password, proxy, pastes, queries):
    try:
        await register_and_send(email, password, proxy, pastes, queries)
        logger.info(f"Worker finished for {email}")
    except Exception as ex:
        logger.error(f"Worker error for {email}: {ex}")

async def main_async_worker():
    emails = load_email_accounts(EMAIL_LIST_PATH)
    pastes = load_lines(PASTES_PATH)
    queries = ["iPhone", "Nike", "Xiaomi"]
    tasks = []
    for acc in emails:
        proxy = get_random_proxy()
        tasks.append(worker(acc["email"], acc["password"], proxy, pastes, queries))
        if len(tasks) >= MAX_WORKERS:
            await asyncio.gather(*tasks)
            tasks = []
    if tasks:
        await asyncio.gather(*tasks)