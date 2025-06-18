import asyncio
from messaging.mailing_worker import authorize_account
from mail_manager.manager import load_email_accounts
from proxy_manager.manager import get_random_proxy
from utils import load_lines
from config import PASTES_PATH, EMAIL_LIST_PATH, MAX_WORKERS
from logs.logger import setup_logger
from playwright.async_api import async_playwright

logger = setup_logger("async_worker")

async def worker(email, password, proxy, pastes, queries):
    try:
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True, proxy={"server": proxy} if proxy else None)
            context = await browser.new_context()
            page = await context.new_page()
            ok = await authorize_account(page, email, password)
            # Здесь можешь добавить рассылку сообщений и парсинг, используя page, pastes, queries
            await browser.close()
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
