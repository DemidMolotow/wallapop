# -*- coding: utf-8 -*-
"""
main.py - Полная система управления Wallapop/Milanuncios с дашбордом
(расширено: 1 прокси = 1 bundle аккаунтов, независимые парсеры/сендеры, контроль паст, авто-подтверждение номера)
"""

import asyncio
import json
import logging
import os
import random
import re
import sqlite3
import httpx
import traceback
import uuid
from datetime import datetime
from typing import Dict, List, Tuple, Optional

from faker import Faker
from playwright.async_api import async_playwright, Page, Browser, TimeoutError as PlaywrightTimeoutError, BrowserContext, Error as PlaywrightError
from playwright_stealth import stealth_async
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application, CommandHandler, CallbackQueryHandler,
    MessageHandler, ContextTypes, filters,
    JobQueue, ConversationHandler
)

# Конфигурация
CONFIG = {
    "TELEGRAM_BOT_TOKEN": os.getenv("TELEGRAM_BOT_TOKEN", "7512529507:AAHga264aQDpBF9fsSHrvDVgInkjwfPJ96o"),
    "HEADLESS_MODE": os.getenv("HEADLESS_MODE", "False") == "True",
    "MAX_CONCURRENT_TASKS": int(os.getenv("MAX_CONCURRENT_TASKS", 5)),
    "DASHBOARD_UPDATE_INTERVAL": int(os.getenv("DASHBOARD_UPDATE_INTERVAL", 15)),
    "DB_FILE": "bot_database.db",
    "COOKIES_DIR": "cookies",
    "LOG_FILE": "bot_logs.log",
    "ACTION_DELAY_MIN": float(os.getenv("ACTION_DELAY_MIN", 2.2)),
    "ACTION_DELAY_MAX": float(os.getenv("ACTION_DELAY_MAX", 5.5)),
    "WALLAPOP_BASE_URL": "https://es.wallapop.com",
    "MILANUNCIOS_BASE_URL": "https://www.milanuncios.com",
    "DEFAULT_PROXY_PROTOCOL": "socks5",
    "MAX_RETRIES": 3
}

logger = logging.getLogger(__name__)
fake = Faker()
TASK_MANAGER: Dict[str, asyncio.Task] = {}
BOT_STATE = "stopped"
BOT_START_TIME = None
SEMAPHORE = asyncio.Semaphore(CONFIG["MAX_CONCURRENT_TASKS"])

MOBILE_USER_AGENTS = [
    "Mozilla/5.0 (Linux; Android 14; SM-S918B) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Mobile Safari/537.36",
    "Mozilla/5.0 (Linux; Android 14; Pixel 8 Pro) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Mobile Safari/537.36",
    "Mozilla/5.0 (iPhone; CPU iPhone OS 17_5_1 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0 Mobile/15E148 Safari/604.1",
    "Mozilla/5.0 (Linux; Android 14; Redmi Note 13 Pro) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Mobile Safari/537.36",
    "Mozilla/5.0 (Linux; Android 13; SM-G991B) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Mobile Safari/537.36",
    "Mozilla/5.0 (Linux; Android 13; SM-G998B) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Mobile Safari/537.36",
    "Mozilla/5.0 (Linux; Android 12; SM-G780F) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Mobile Safari/537.36",
    "Mozilla/5.0 (Linux; Android 11; M2007J20CG) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Mobile Safari/537.36",
    "Mozilla/5.0 (iPhone14,3; U; CPU iPhone OS 15_0 like Mac OS X) AppleWebKit/602.1.50 (KHTML, like Gecko) Version/15.0 Mobile/19A346 Safari/602.1",
    "Mozilla/5.0 (iPhone; CPU iPhone OS 16_5 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/16.5 Mobile/15E148 Safari/604.1",
    "Mozilla/5.0 (iPad; CPU OS 16_5 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/16.5 Mobile/15E148 Safari/604.1"
]

MOBILE_VIEWPORTS = [
    {"width": 390, "height": 844},
    {"width": 412, "height": 915},
    {"width": 393, "height": 873},
    {"width": 414, "height": 896},
    {"width": 360, "height": 800},
    {"width": 375, "height": 812},
    {"width": 428, "height": 926},
    {"width": 390, "height": 844},
    {"width": 360, "height": 780},
    {"width": 412, "height": 892}
]

(
    WAITING_PROXY, WAITING_ACCOUNT_LOGIN, WAITING_ACCOUNT_PASSWORD,
    WAITING_SETTING_VALUE, WAITING_PASTE_NAME, WAITING_PASTE_MESSAGE,
    WAITING_PARSER_QUERY, WAITING_SENDER_QUERY
) = range(8)
CANCEL = "CANCEL"

# ====================== БАЗА ДАННЫХ ======================

class Database:
    def __init__(self, db_path: str):
        self.db_path = db_path
        self._init_db()

    def _init_db(self):
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS Users (
                    user_id INTEGER PRIMARY KEY,
                    balance REAL DEFAULT 0.0,
                    subscription_end_date TIMESTAMP
                );
            ''')
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS Proxies (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    proxy_string TEXT NOT NULL UNIQUE,
                    owner_id INTEGER,
                    status TEXT DEFAULT 'good',
                    FOREIGN KEY(owner_id) REFERENCES Users(user_id)
                );
            ''')
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS Accounts (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    service TEXT NOT NULL,
                    login TEXT NOT NULL,
                    password TEXT NOT NULL,
                    proxy_id INTEGER,
                    owner_id INTEGER,
                    status TEXT DEFAULT 'active',
                    FOREIGN KEY(owner_id) REFERENCES Users(user_id),
                    FOREIGN KEY(proxy_id) REFERENCES Proxies(id),
                    UNIQUE(service, login)
                );
            ''')
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS UserSettings (
                    user_id INTEGER PRIMARY KEY,
                    slot_limit INTEGER DEFAULT 5,
                    interval_min REAL DEFAULT 2.2,
                    interval_max REAL DEFAULT 5.5,
                    FOREIGN KEY(user_id) REFERENCES Users(user_id)
                );
            ''')
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS GlobalStats (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER,
                    parsed_count INTEGER DEFAULT 0,
                    sent_count INTEGER DEFAULT 0,
                    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY(user_id) REFERENCES Users(user_id)
                );
            ''')
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS SessionStats (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    parsed_count INTEGER DEFAULT 0,
                    sent_count INTEGER DEFAULT 0,
                    start_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                );
            ''')
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS Pastes (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT NOT NULL,
                    messages TEXT NOT NULL,
                    owner_id INTEGER,
                    is_banned_wallapop INTEGER DEFAULT 0,
                    FOREIGN KEY(owner_id) REFERENCES Users(user_id),
                    UNIQUE(owner_id, name)
                );
            ''')
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS ParsedItems (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    service TEXT NOT NULL,
                    item_id TEXT NOT NULL,
                    title TEXT NOT NULL,
                    url TEXT NOT NULL,
                    owner_id INTEGER,
                    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY(owner_id) REFERENCES Users(user_id),
                    UNIQUE(service, item_id)
                );
            ''')
            conn.commit()

    def _execute(self, query: str, params: tuple = (), fetch: bool = False):
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            cursor.execute(query, params)
            if fetch:
                return cursor.fetchall()
            conn.commit()

    def add_user(self, user_id: int):
        self._execute("INSERT OR IGNORE INTO Users (user_id) VALUES (?)", (user_id,))
        self._execute("INSERT OR IGNORE INTO UserSettings (user_id) VALUES (?)", (user_id,))
        self._execute("INSERT OR IGNORE INTO SessionStats DEFAULT VALUES")

    def add_proxy(self, proxy: str, user_id: int):
        self._execute(
            "INSERT OR IGNORE INTO Proxies (proxy_string, owner_id) VALUES (?, ?)",
            (proxy, user_id)
        )

def get_proxies(self, user_id: int) -> list:
    return self._execute(
        "SELECT id, proxy_string, status FROM Proxies WHERE owner_id = ?",
        (user_id,),
        fetch=True
    )

def get_user_settings(self, user_id: int) -> dict:
    result = self._execute(
        "SELECT slot_limit, interval_min, interval_max FROM UserSettings WHERE user_id = ?",
        (user_id,),
        fetch=True
    )
    return dict(result[0]) if result else {
        "slot_limit": 5,
        "interval_min": 2.2,
        "interval_max": 5.5
    }

def get_proxy_by_id(self, proxy_id: int) -> Optional[dict]:
    result = self._execute(
        "SELECT id, proxy_string FROM Proxies WHERE id = ?",
        (proxy_id,),
        fetch=True
    )
    return dict(result[0]) if result else None

    def add_account(self, service: str, login: str, password: str, user_id: int, proxy_id: int):
        self._execute(
            "INSERT OR IGNORE INTO Accounts (service, login, password, owner_id, proxy_id) VALUES (?, ?, ?, ?, ?)",
            (service, login, password, user_id, proxy_id)
        )

    def get_accounts(self, user_id: int, service: str = None) -> list:
        query = "SELECT id, service, login, status, proxy_id FROM Accounts WHERE owner_id = ?"
        params = [user_id]
        if service:
            query += " AND service = ?"
            params.append(service)
        return self._execute(query, tuple(params), fetch=True)

    def delete_account(self, account_id: int):
        self._execute("DELETE FROM Accounts WHERE id = ?", (account_id,))

    def count_accounts(self, user_id: int, status: str = None) -> int:
        query = "SELECT COUNT(*) as count FROM Accounts WHERE owner_id = ?"
        params = [user_id]
        if status:
            query += " AND status = ?"
            params.append(status)
        result = self._execute(query, tuple(params), fetch=True)
        return result[0]["count"] if result else 0

    def update_account_status(self, account_id: int, status: str):
        self._execute(
            "UPDATE Accounts SET status = ? WHERE id = ?",
            (status, account_id)
        )

    def add_paste(self, name: str, messages: list, user_id: int):
        self._execute(
            "INSERT OR IGNORE INTO Pastes (name, messages, owner_id) VALUES (?, ?, ?)",
            (name, json.dumps(messages), user_id)
        )

    def get_pastes(self, user_id: int) -> list:
        result = self._execute(
            "SELECT id, name, messages, is_banned_wallapop FROM Pastes WHERE owner_id = ?",
            (user_id,),
            fetch=True
        )
        return [dict(row) for row in result] if result else []

    def get_active_pastes_for_wallapop(self, user_id: int) -> list:
        result = self._execute(
            "SELECT id, name, messages FROM Pastes WHERE owner_id = ? AND is_banned_wallapop = 0",
            (user_id,),
            fetch=True
        )
        return [dict(row) for row in result] if result else []

    def mark_paste_banned_on_wallapop(self, paste_id: int):
        self._execute(
            "UPDATE Pastes SET is_banned_wallapop = 1 WHERE id = ?",
            (paste_id,)
        )

    def get_random_paste(self, user_id: int, for_wallapop: bool = False) -> dict:
        if for_wallapop:
            pastes = self.get_active_pastes_for_wallapop(user_id)
        else:
            pastes = self.get_pastes(user_id)
        return random.choice(pastes) if pastes else None

    # ... (и остальные методы по твоей логике, без изменений)

db = Database(CONFIG["DB_FILE"])
# ====================== СИСТЕМА УПРАВЛЕНИЯ ======================

class DashboardManager:
    def __init__(self):
        self.user_dashboards = {}

    async def send_dashboard(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        user_id = update.effective_user.id
        db.add_user(user_id)

        if user_id in self.user_dashboards:
            try:
                await context.bot.delete_message(
                    chat_id=update.effective_chat.id,
                    message_id=self.user_dashboards[user_id]
                )
            except Exception:
                pass

        message = await update.message.reply_text(
            self.generate_dashboard(user_id),
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("Меню", callback_data="main_menu")]]),
            parse_mode="HTML"
        )

        self.user_dashboards[user_id] = message.message_id

        context.job_queue.run_repeating(
            self.update_dashboard,
            interval=CONFIG["DASHBOARD_UPDATE_INTERVAL"],
            first=0,
            chat_id=update.effective_chat.id,
            user_id=user_id,
            name=f"dashboard_{user_id}"
        )

    async def update_dashboard(self, context: ContextTypes.DEFAULT_TYPE):
        job = context.job
        user_id = job.user_id

        if user_id in self.user_dashboards:
            try:
                await context.bot.edit_message_text(
                    chat_id=job.chat_id,
                    message_id=self.user_dashboards[user_id],
                    text=self.generate_dashboard(user_id),
                    reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("Меню", callback_data="main_menu")]]),
                    parse_mode="HTML"
                )
            except Exception as e:
                logger.error(f"Dashboard update error: {e}")

   def generate_dashboard(self, user_id: int) -> str:
    global BOT_STATE, BOT_START_TIME

    settings = db.get_user_settings(user_id)
    session_stats = db.get_session_stats()
    global_stats = db.get_global_stats(user_id)
    total_accounts = db.count_accounts(user_id)
    reading_accounts = db.count_accounts(user_id, "reading")
    completed_accounts = db.count_accounts(user_id, "completed")
    proxy_count = db.count_proxies(user_id)
    wallapop_items = db.count_parsed_items(user_id, "wallapop")
    milanuncios_items = db.count_parsed_items(user_id, "milanuncios")

    uptime = "N/A"
    if BOT_STATE == "running" and BOT_START_TIME:
        uptime = str(datetime.now() - BOT_START_TIME).split('.')[0]

    return (
        "📊 <b>Боевой Дашборд</b>\n"
        "--------------------------------\n"
        f"🟢 <b>Статус:</b> {'<b>РАБОТАЕТ</b> ✅' if BOT_STATE == 'running' else '<b>ОСТАНОВЛЕН</b> ❌'}\n"
        f"⏱ <b>Время работы:</b> {uptime}\n"
        "--------------------------------\n"
        f"👤 <b>Профиль:</b> ID {user_id}\n"
        "--------------------------------\n"
        "📦 <b>Ресурсы:</b>\n"
        f"  • Протокол: SOCKS5\n"
        f"  • Прокси: {proxy_count}\n"
        f"  • Аккаунты: {total_accounts} (Чтение: {reading_accounts}, Отработано: {completed_accounts})\n"
        f"  • Найдено: Wallapop: {wallapop_items}, Milanuncios: {milanuncios_items}\n"
        "--------------------------------\n"
        "⚙️ <b>Параметры:</b>\n"
        f"  • Лимит слотов: {settings['slot_limit']}\n"
        f"  • Слотов в работе: {len(TASK_MANAGER)}\n"
        f"  • Интервал: {settings['interval_min']}-{settings['interval_max']} сек\n"
        "--------------------------------\n"
        "🚀 <b>Текущая сессия:</b>\n"
        f"  • Парсер: найдено {session_stats['parsed_count']}\n"
        f"  • Сендер: отправлено {session_stats['sent_count']}\n"
        "--------------------------------\n"
        "📈 <b>Общая статистика:</b>\n"
        f"  • Найдено: {global_stats['total_parsed']}\n"
        f"  • Отправлено: {global_stats['total_sent']}\n"
        "--------------------------------"
    )

    async def force_update(self, context: ContextTypes.DEFAULT_TYPE, user_id: int, chat_id: int):
        if user_id in self.user_dashboards:
            try:
                await context.bot.edit_message_text(
                    chat_id=chat_id,
                    message_id=self.user_dashboards[user_id],
                    text=self.generate_dashboard(user_id),
                    reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("Меню", callback_data="main_menu")]]),
                    parse_mode="HTML"
                )
            except Exception as e:
                logger.error(f"Force update error: {e}")

dashboard_manager = DashboardManager()
# ====================== МОДУЛИ WALLAPOP И MILANUNCIOS ======================

class BaseServiceModule:
    def __init__(self, context: ContextTypes.DEFAULT_TYPE, task_id: str, account: dict = None):
        self.context = context
        self.task_id = task_id
        self.user_id = context.user_data.get('user_id')
        self.chat_id = context.user_data.get('chat_id')
        self.account = account

    async def _get_page(self, service: str, proxy_string: Optional[str] = None) -> Tuple[Page, Browser, BrowserContext, Optional[str]]:
        p = await async_playwright().start()

        proxy_settings = None
        if proxy_string:
            proxy_settings = {"server": proxy_string}
            logger.info(f"Using proxy: {proxy_string}")
        else:
            logger.warning("No valid proxy found, using direct connection")

        viewport = random.choice(MOBILE_VIEWPORTS)
        user_agent = random.choice(MOBILE_USER_AGENTS)

        browser = await p.chromium.launch(
            headless=CONFIG["HEADLESS_MODE"],
            proxy=proxy_settings,
            args=[
                "--disable-blink-features=AutomationControlled",
                "--disable-web-security",
                "--disable-infobars",
                f"--window-size={viewport['width']},{viewport['height']}"
            ]
        )

        context = await browser.new_context(
            user_agent=user_agent,
            viewport=viewport,
            locale="es-ES",
            timezone_id="Europe/Madrid",
            is_mobile=True,
            device_scale_factor=2.6,
            java_script_enabled=True,
            has_touch=True,
            permissions=["geolocation"],
            color_scheme="dark" if random.random() > 0.7 else "light"
        )

        page = await context.new_page()
        await stealth_async(page)

        # Убираем webdriver флаг
        await page.add_init_script("""
            delete navigator.__proto__.webdriver;
            Object.defineProperty(navigator, 'webdriver', { get: () => false });
        """)

        logger.info(f"Task {self.task_id[:6]}: Mobile browser, proxy: {proxy_string or 'None'} UA: {user_agent}")
        return page, browser, context, proxy_string

    async def _send(self, message: str, **kwargs):
        await self.context.bot.send_message(chat_id=self.chat_id, text=f"[Task {self.task_id[:6]}] {message}", **kwargs)

    async def _delay(self, k: float = 1.0):
        await asyncio.sleep(random.uniform(CONFIG["ACTION_DELAY_MIN"], CONFIG["ACTION_DELAY_MAX"]) * k)

    async def _handle_cookies(self, page: Page, selector: str):
        try:
            await page.locator(selector).click(timeout=10000)
            await self._send("Cookies accepted.")
            await self._delay(0.6)
        except PlaywrightTimeoutError:
            pass

    async def _random_interactions(self, page: Page):
        width, height = page.viewport_size['width'], page.viewport_size['height']

        for _ in range(random.randint(2, 5)):
            await page.mouse.move(
                random.randint(0, width),
                random.randint(0, height),
                steps=random.randint(5, 15)
            )
            await self._delay(0.3)
        for _ in range(random.randint(1, 3)):
            await page.mouse.click(
                random.randint(0, width),
                random.randint(0, height),
                delay=random.randint(50, 300)
            )
            await self._delay(0.5)
        for _ in range(random.randint(1, 3)):
            await page.mouse.wheel(0, random.randint(100, 500))
            await self._delay(0.7)

    async def _bypass_antibot(self, page: Page):
        try:
            if await page.query_selector('div#cf-challenge-wrapper'):
                await self._send("⚠️ Cloudflare detected. Trying to bypass...")
                await page.wait_for_selector('div#cf-challenge-wrapper', state='hidden', timeout=30000)
                await self._delay(3)
            await page.evaluate('''() => {
                Object.defineProperty(navigator, 'webdriver', { get: () => false });
                window.navigator.chrome = { runtime: {}, };
                Object.defineProperty(navigator, 'plugins', { get: () => [1, 2, 3] });
                Object.defineProperty(navigator, 'languages', { get: () => ['es-ES', 'es'] });
            }''')
        except Exception as e:
            logger.warning(f"Antibot bypass failed: {e}")

class WallapopService(BaseServiceModule):
    SERVICE_NAME = "wallapop"
    BASE_URL = CONFIG["WALLAPOP_BASE_URL"]

    async def login(self, page: Page, account: dict):
        await self._send(f"Logging in to Wallapop: {account['login']}")
        try:
            await page.goto(f"{self.BASE_URL}/login", wait_until="networkidle", timeout=60000)
            await self._handle_cookies(page, "#onetrust-accept-btn-handler")
            await self._random_interactions(page)

            await page.fill('input[type="email"]', account['login'])
            await self._delay(1.2)
            await page.fill('input[type="password"]', account['password'])
            await self._delay(1.0)
            await page.locator('button[type="submit"]').click()
            await self._delay(3)

            await page.wait_for_selector('a[data-testid="profile-link"]', timeout=20000)
            await self._send("✅ Login successful.")
            return True
        except Exception as e:
            logger.error(f"Wallapop login error: {e}")
            await self._send("❌ Login failed.")
            return False

    async def parser(self):
        if BOT_STATE != "running":
            return

        # --- Новый цикл: каждый аккаунт со своей прокси ---
        user_accounts = db.get_accounts(self.user_id, service="wallapop")
        for acc in user_accounts:
            proxy_rec = db.get_proxy_by_id(acc["proxy_id"])
            proxy_str = proxy_rec["proxy_string"] if proxy_rec else None
            browser = None
            for attempt in range(1, CONFIG["MAX_RETRIES"] + 1):
                try:
                    page, browser, context, proxy = await self._get_page(self.SERVICE_NAME, proxy_string=proxy_str)
                    await self._send(f"Парсер Wallapop (акк: {acc['login']}, попытка {attempt}/{CONFIG['MAX_RETRIES']})")
                    await self._bypass_antibot(page)
                    await page.goto(f"{self.BASE_URL}/search", wait_until="networkidle", timeout=90000)
                    await self._delay(2)
                    await self._handle_cookies(page, "#onetrust-accept-btn-handler")
                    await self._random_interactions(page)
                    await self._apply_wallapop_filters(page)

                    items = await page.query_selector_all('div[data-testid="search-result-item"]')
                    results_count = 0
                    for i, item in enumerate(items[:10]):
                        try:
                            title_element = await item.query_selector('div[data-testid="product-info-name"]')
                            title = await title_element.inner_text() if title_element else "No title"
                            link_element = await item.query_selector('a[data-testid="product-cell-link"]')
                            href = await link_element.get_attribute("href")
                            full_url = f"{self.BASE_URL}{href}" if href else "No URL"
                            item_id = re.search(r'/item/(\d+)', href).group(1) if href else str(uuid.uuid4())
                            db.add_parsed_item(self.SERVICE_NAME, item_id, title, full_url, self.user_id)
                            results_count += 1
                            await self._delay(0.7)
                        except Exception as e:
                            logger.error(f"Error processing item {i}: {e}")
                    db.increment_stats(self.user_id, parsed=results_count)
                    await self._send(f"✅ Found {results_count} matching items on Wallapop (акк: {acc['login']})")
                    break
                except PlaywrightTimeoutError as e:
                    logger.error(f"Wallapop parser timeout (attempt {attempt}): {e}")
                    await self._send(f"⚠️ Timeout error. Retrying ({attempt}/{CONFIG['MAX_RETRIES']})...")
                    await asyncio.sleep(5)
                except PlaywrightError as e:
                    if "ERR_CONNECTION_CLOSED" in str(e) or "net::ERR" in str(e):
                        logger.error(f"Network error (attempt {attempt}): {e}")
                        await self._send(f"⚠️ Network error. Retrying with new proxy ({attempt}/{CONFIG['MAX_RETRIES']})...")
                        await asyncio.sleep(3)
                    else:
                        logger.exception(f"Wallapop parser error (attempt {attempt}): {e}")
                        await self._send(f"❌ Parser error: {str(e)}")
                        break
                except Exception as e:
                    logger.exception(f"Unexpected error (attempt {attempt}): {e}")
                    await self._send(f"❌ Unexpected error: {str(e)}")
                    break
                finally:
                    if browser:
                        await browser.close()

    async def _apply_wallapop_filters(self, page: Page):
        try:
            await page.click('button[data-testid="filters-button"]', timeout=15000)
            await self._delay(1.5)
            await page.click('div[data-testid="filter-delivery"]', timeout=10000)
            await self._delay(0.8)
            await page.click('label[for="shipping"]', timeout=10000)
            await self._delay(0.8)
            await page.click('button[data-testid="sort-button"]', timeout=10000)
            await self._delay(0.8)
            await page.click('div[role="option"]:has-text("Más recientes")', timeout=10000)
            await self._delay(0.8)
            await page.click('button[data-testid="apply-filters-button"]', timeout=10000)
            await self._delay(3)
            await self._send("Filters applied: Delivery=Yes, Sort=Newest")
        except Exception as e:
            logger.error(f"Error applying Wallapop filters: {e}")
            await self._send("⚠️ Could not apply all filters, continuing with default search")

    async def sender(self):
        user_accounts = db.get_accounts(self.user_id, service="wallapop")
        for acc in user_accounts:
            proxy_rec = db.get_proxy_by_id(acc["proxy_id"])
            proxy_str = proxy_rec["proxy_string"] if proxy_rec else None
            browser = None
            try:
                page, browser, context, proxy = await self._get_page(self.SERVICE_NAME, proxy_string=proxy_str)
                await self.login(page, acc)
                # Получить объявления для этого пользователя
                items = db.get_parsed_items(self.user_id, service="wallapop", limit=10)
                for item in items:
                    paste = db.get_random_paste(self.user_id, for_wallapop=True)
                    if not paste:
                        await self._send("Нет активных паст для Wallapop!")
                        break
                    msg = random.choice(json.loads(paste["messages"]))
                    await page.goto(item["url"], wait_until="networkidle", timeout=45000)
                    await self._delay(1.5)
                    # ... (логика поиска поля для сообщения и отправки)
                    try:
                        await page.fill('textarea', msg)
                        await self._delay(1.0)
                        await page.click('button[type="submit"]')
                        await self._delay(1.0)
                    except Exception as e:
                        logger.error(f"Ошибка отправки: {e}")
                        continue
                    # --- Антифрод: проверка на бан ---
                    banned = False
                    try:
                        # Находим текстовое предупреждение о бане или блокировке отправки (пример)
                        ban_elem = await page.query_selector("div:has-text('bloqueado')")  # примерный селектор
                        if ban_elem:
                            banned = True
                    except Exception:
                        pass
                    if banned:
                        await self.context.bot.send_message(
                            chat_id=self.chat_id,
                            text=f"⚠️ Похоже, паста вызвала бан на Wallapop!\n\nПаста:\n<code>{msg}</code>\n\nИсключить её для Wallapop?",
                            parse_mode="HTML",
                            reply_markup=InlineKeyboardMarkup([
                                [InlineKeyboardButton("Исключить", callback_data=f"ban_paste_{paste['id']}")],
                                [InlineKeyboardButton("Оставить", callback_data="ignore_ban")]
                            ])
                        )
                    db.increment_stats(self.user_id, sent=1)
                    db.delete_parsed_item(item["id"])
                    await self._delay(2.0)
            except Exception as e:
                logger.error(f"Wallapop sender error: {e}")
            finally:
                if browser:
                    await browser.close()

class MilanunciosService(BaseServiceModule):
    SERVICE_NAME = "milanuncios"
    BASE_URL = CONFIG["MILANUNCIOS_BASE_URL"]

    async def login(self, page: Page, account: dict):
        await self._send(f"Logging in to Milanuncios: {account['login']}")
        try:
            await page.goto(f"{self.BASE_URL}/login/", wait_until="networkidle", timeout=60000)
            await self._handle_cookies(page, "#onetrust-accept-btn-handler")
            await self._random_interactions(page)
            await page.fill('input[type="email"]', account['login'])
            await self._delay(1.2)
            await page.click('button:has-text("Continuar")', timeout=10000)
            await self._delay(1.5)
            await page.fill('input[type="password"]', account['password'])
            await self._delay(1.0)
            await page.click('button:has-text("Iniciar sesión")', timeout=10000)
            await self._delay(3)
            await page.wait_for_selector('div.ma-UserNav', timeout=20000)
            await self._send("✅ Login successful.")
            return True
        except Exception as e:
            logger.error(f"Milanuncios login error: {e}")
            await self._send("❌ Login failed.")
            return False

    async def parser(self):
        if BOT_STATE != "running":
            return

        user_accounts = db.get_accounts(self.user_id, service="milanuncios")
        for acc in user_accounts:
            proxy_rec = db.get_proxy_by_id(acc["proxy_id"])
            proxy_str = proxy_rec["proxy_string"] if proxy_rec else None
            browser = None
            for attempt in range(1, CONFIG["MAX_RETRIES"] + 1):
                try:
                    page, browser, context, proxy = await self._get_page(self.SERVICE_NAME, proxy_string=proxy_str)
                    await self._send(f"Парсер Milanuncios (акк: {acc['login']}, попытка {attempt}/{CONFIG['MAX_RETRIES']})")
                    await self._bypass_antibot(page)
                    await page.goto(f"{self.BASE_URL}/anuncios/", wait_until="networkidle", timeout=90000)
                    await self._delay(2)
                    await self._handle_cookies(page, "#onetrust-accept-btn-handler")
                    await self._random_interactions(page)
                    await self._apply_milanuncios_filters(page)
                    items = await page.query_selector_all('article.ma-AdCard')
                    results_count = 0
                    for i, item in enumerate(items[:10]):
                        try:
                            title_element = await item.query_selector('a.ma-AdCard-titleLink')
                            title = await title_element.inner_text() if title_element else "No title"
                            href = await title_element.get_attribute("href")
                            full_url = f"{self.BASE_URL}{href}" if href else "No URL"
                            item_id = re.search(r'/anuncio/(\d+)\.htm', href).group(1) if href else str(uuid.uuid4())
                            db.add_parsed_item(self.SERVICE_NAME, item_id, title, full_url, self.user_id)
                            results_count += 1
                            await self._delay(0.7)
                        except Exception as e:
                            logger.error(f"Error processing item {i}: {e}")
                    db.increment_stats(self.user_id, parsed=results_count)
                    await self._send(f"✅ Found {results_count} matching items on Milanuncios (акк: {acc['login']})")
                    break
                except PlaywrightTimeoutError as e:
                    logger.error(f"Milanuncios parser timeout (attempt {attempt}): {e}")
                    await self._send(f"⚠️ Timeout error. Retrying ({attempt}/{CONFIG['MAX_RETRIES']})...")
                    await asyncio.sleep(5)
                except PlaywrightError as e:
                    if "ERR_CONNECTION_CLOSED" in str(e) or "net::ERR" in str(e):
                        logger.error(f"Network error (attempt {attempt}): {e}")
                        await self._send(f"⚠️ Network error. Retrying with new proxy ({attempt}/{CONFIG['MAX_RETRIES']})...")
                        await asyncio.sleep(3)
                    else:
                        logger.exception(f"Milanuncios parser error (attempt {attempt}): {e}")
                        await self._send(f"❌ Parser error: {str(e)}")
                        break
                except Exception as e:
                    logger.exception(f"Unexpected error (attempt {attempt}): {e}")
                    await self._send(f"❌ Unexpected error: {str(e)}")
                    break
                finally:
                    if browser:
                        await browser.close()

    async def _apply_milanuncios_filters(self, page: Page):
        try:
            await page.click('button:has-text("Filtros")', timeout=15000)
            await self._delay(1.5)
            await page.click('label:has-text("Con envío")', timeout=10000)
            await self._delay(0.8)
            await page.click('button:has-text("Ordenar")', timeout=10000)
            await self._delay(0.8)
            await page.click('button:has-text("Más recientes")', timeout=10000)
            await self._delay(0.8)
            await page.click('button:has-text("Aplicar")', timeout=10000)
            await self._delay(3)
            await self._send("Filters applied: Delivery=Yes, Sort=Newest")
        except Exception as e:
            logger.error(f"Error applying Milanuncios filters: {e}")
            await self._send("⚠️ Could not apply all filters, continuing with default search")

    async def sender(self):
        user_accounts = db.get_accounts(self.user_id, service="milanuncios")
        for acc in user_accounts:
            proxy_rec = db.get_proxy_by_id(acc["proxy_id"])
            proxy_str = proxy_rec["proxy_string"] if proxy_rec else None
            browser = None
            try:
                page, browser, context, proxy = await self._get_page(self.SERVICE_NAME, proxy_string=proxy_str)
                await self.login(page, acc)
                items = db.get_parsed_items(self.user_id, service="milanuncios", limit=10)
                for item in items:
                    paste = db.get_random_paste(self.user_id, for_wallapop=False)
                    if not paste:
                        await self._send("Нет паст для Milanuncios!")
                        break
                    msg = random.choice(json.loads(paste["messages"]))
                    await page.goto(item["url"], wait_until="networkidle", timeout=45000)
                    await self._delay(1.5)
                    try:
                        await page.fill('textarea', msg)
                        await self._delay(1.0)
                        await page.click('button[type="submit"]')
                        await self._delay(1.0)
                        # --- Авто-подтверждение номера телефона ---
                        try:
                            confirm_btn = await page.query_selector("button:has-text('enviar número')") or await page.query_selector("button:has-text('Sí')")
                            if confirm_btn:
                                await confirm_btn.click()
                        except Exception:
                            pass
                    except Exception as e:
                        logger.error(f"Ошибка отправки: {e}")
                        continue
                    db.increment_stats(self.user_id, sent=1)
                    db.delete_parsed_item(item["id"])
                    await self._delay(2.0)
            except Exception as e:
                logger.error(f"Milanuncios sender error: {e}")
            finally:
                if browser:
                    await browser.close()
# ====================== TELEGRAM HANDLERS ======================

async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data['user_id'] = update.effective_user.id
    context.user_data['chat_id'] = update.effective_chat.id
    await dashboard_manager.send_dashboard(update, context)

async def main_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    keyboard = [
        [InlineKeyboardButton("▶️ Запустить" if BOT_STATE == "stopped" else "⏹️ Остановить",
                             callback_data="toggle_bot_state")],
        [InlineKeyboardButton("⚙️ Настройки", callback_data="settings_menu")],
        [InlineKeyboardButton("🗂️ Ресурсы", callback_data="resources_menu")],
        [InlineKeyboardButton("🚀 Запустить парсер", callback_data="run_parser")],
        [InlineKeyboardButton("✉️ Запустить рассылку", callback_data="run_sender")],
        [InlineKeyboardButton("📈 Статистика", callback_data="show_stats")],
        [InlineKeyboardButton("🔄 Обновить дашборд", callback_data="refresh_dashboard")],
        [InlineKeyboardButton("✖️ Закрыть", callback_data="close_menu")]
    ]

    await query.edit_message_text(
        "🔧 <b>Главное меню управления</b>",
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode="HTML"
    )

async def toggle_bot_state(update: Update, context: ContextTypes.DEFAULT_TYPE):
    global BOT_STATE, BOT_START_TIME
    query = update.callback_query
    await query.answer()
    user_id = query.from_user.id

    if BOT_STATE == "stopped":
        BOT_STATE = "running"
        BOT_START_TIME = datetime.now()
        db.reset_session_stats()
        await query.edit_message_text("✅ Бот запущен и готов к работе!")
    else:
        BOT_STATE = "stopped"
        await query.edit_message_text("🛑 Бот остановлен. Все задачи завершены.")

    await dashboard_manager.force_update(context, user_id, query.message.chat_id)

async def resources_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    keyboard = [
        [InlineKeyboardButton("➕ Добавить прокси", callback_data="add_proxy")],
        [InlineKeyboardButton("👁 Просмотреть прокси", callback_data="list_proxies")],
        [InlineKeyboardButton("➕ Добавить аккаунт Wallapop", callback_data="add_wallapop_account")],
        [InlineKeyboardButton("➕ Добавить аккаунт Milanuncios", callback_data="add_milanuncios_account")],
        [InlineKeyboardButton("👁 Просмотреть аккаунты", callback_data="list_accounts")],
        [InlineKeyboardButton("➕ Добавить пасту", callback_data="add_paste")],
        [InlineKeyboardButton("👁 Просмотреть пасты", callback_data="list_pastes")],
        [InlineKeyboardButton("⬅️ Назад", callback_data="main_menu")]
    ]

    await query.edit_message_text(
        "🗂️ <b>Управление ресурсами</b>\n\n"
        "Здесь вы можете управлять своими прокси и аккаунтами:",
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode="HTML"
    )

# Добавление прокси
async def add_proxy_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    await query.edit_message_text("Введите прокси в формате: host:port (например: 192.168.1.2:30000)\n\nОтправьте /cancel для отмены")
    return WAITING_PROXY

async def handle_proxy_input(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.message.from_user.id
    proxy = update.message.text.strip()

    if proxy == "/cancel":
        await update.message.reply_text("❌ Добавление прокси отменено")
        return ConversationHandler.END

    try:
        if not re.match(r"^\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}:\d{1,5}$", proxy):
            raise ValueError("Неправильный формат")
        formatted_proxy = f"{CONFIG['DEFAULT_PROXY_PROTOCOL']}://{proxy}"
        db.add_proxy(formatted_proxy, user_id)
        await update.message.reply_text("✅ Прокси успешно добавлен!")
        return ConversationHandler.END
    except Exception:
        await update.message.reply_text("❌ Ошибка добавления прокси. Используйте формат host:port.")
        return WAITING_PROXY

async def list_proxies(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user_id = query.from_user.id

    proxies = db.get_proxies(user_id)
    if not proxies:
        await query.edit_message_text("У вас пока нет добавленных прокси.")
        return

    text = "📡 <b>Ваши прокси:</b>\n\n"
    for i, proxy in enumerate(proxies, 1):
        display_proxy = proxy['proxy_string'].replace(f"{CONFIG['DEFAULT_PROXY_PROTOCOL']}://", "")
        status_icon = "🟢" if proxy["status"] == "good" else "🔴"
        text += f"{i}. {status_icon} {display_proxy} [ID:{proxy['id']}]\n"

    keyboard = [[InlineKeyboardButton("⬅️ Назад", callback_data="resources_menu")]]
    await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="HTML")

# Добавление аккаунта с выбором прокси
async def handle_account_service(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    service = "wallapop" if "wallapop" in query.data else "milanuncios"
    context.user_data["acc_service"] = service

    user_id = query.from_user.id
    proxies = db.get_proxies(user_id)
    if not proxies:
        await query.edit_message_text("❌ Сначала добавьте хотя бы один прокси!")
        return ConversationHandler.END

    keyboard = [
        [InlineKeyboardButton(proxy['proxy_string'].replace(f"{CONFIG['DEFAULT_PROXY_PROTOCOL']}://", ""), callback_data=f"choose_proxy_{proxy['id']}")]
        for proxy in proxies
    ]
    await query.edit_message_text(
        "Выберите прокси для этого аккаунта:",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )
    return WAITING_ACCOUNT_LOGIN

async def choose_proxy(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    proxy_id = int(query.data.replace("choose_proxy_", ""))
    context.user_data["acc_proxy_id"] = proxy_id
    await query.edit_message_text("Введите логин (email) для аккаунта:\n\nОтправьте /cancel для отмены")
    return WAITING_ACCOUNT_LOGIN

async def handle_account_login(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.message.text.strip() == "/cancel":
        await update.message.reply_text("❌ Добавление аккаунта отменено")
        return ConversationHandler.END

    context.user_data["acc_login"] = update.message.text.strip()
    await update.message.reply_text("Введите пароль для аккаунта:\n\nОтправьте /cancel для отмена")
    return WAITING_ACCOUNT_PASSWORD

async def handle_account_password(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.message.text.strip() == "/cancel":
        await update.message.reply_text("❌ Добавление аккаунта отменено")
        return ConversationHandler.END

    user_id = update.message.from_user.id
    password = update.message.text.strip()
    service = context.user_data["acc_service"]
    login = context.user_data["acc_login"]
    proxy_id = context.user_data["acc_proxy_id"]

    try:
        db.add_account(service, login, password, user_id, proxy_id)
        await update.message.reply_text("✅ Аккаунт успешно добавлен!")
        return ConversationHandler.END

    except Exception:
        await update.message.reply_text("❌ Ошибка добавления аккаунта. Попробуйте еще раз:")
        return WAITING_ACCOUNT_PASSWORD

async def list_accounts(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user_id = query.from_user.id

    accounts = db.get_accounts(user_id)
    if not accounts:
        await query.edit_message_text("У вас пока нет добавленных аккаунтов.")
        return

    text = "👤 <b>Ваши аккаунты:</b>\n\n"
    for account in accounts:
        status_icon = "🟢" if account["status"] == "active" else "🟡" if account["status"] == "reading" else "🔵"
        proxy_info = f" | Прокси: {account['proxy_id']}" if account.get("proxy_id") else ""
        text += f"{status_icon} <b>{account['service'].capitalize()}</b>: {account['login']} [ID:{account['id']}] {proxy_info}\n"

    keyboard = [[InlineKeyboardButton("⬅️ Назад", callback_data="resources_menu")]]
    await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="HTML")
# ====================== ПАСТЫ, ПАРСЕР/СЕНДЕР, СПЕЦОБРАБОТКА ======================

async def add_paste_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    await query.edit_message_text("Введите название для новой пасты:\n\nОтправьте /cancel для отмены")
    return WAITING_PASTE_NAME

async def handle_paste_name(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.message.text.strip() == "/cancel":
        await update.message.reply_text("❌ Создание пасты отменено")
        return ConversationHandler.END

    context.user_data["paste_name"] = update.message.text.strip()
    await update.message.reply_text("Введите сообщения пасты по одному. Когда закончите, отправьте /done\n\nОтправьте /cancel для отмены")
    context.user_data["paste_messages"] = []
    return WAITING_PASTE_MESSAGE

async def handle_paste_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    message = update.message.text.strip()

    if message == "/cancel":
        await update.message.reply_text("❌ Создание пасты отменено")
        return ConversationHandler.END

    context.user_data["paste_messages"].append(message)
    await update.message.reply_text("Сообщение добавлено. Отправьте следующее, /done или /cancel")
    return WAITING_PASTE_MESSAGE

async def handle_paste_done(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.message.from_user.id
    name = context.user_data["paste_name"]
    messages = context.user_data["paste_messages"]

    if not messages:
        await update.message.reply_text("❌ Паста не может быть пустой. Попробуйте снова.")
        return WAITING_PASTE_MESSAGE

    try:
        db.add_paste(name, messages, user_id)
        await update.message.reply_text(f"✅ Паста '{name}' успешно создана!")
        return ConversationHandler.END
    except Exception:
        await update.message.reply_text("❌ Ошибка создания пасты. Попробуйте снова:")
        return WAITING_PASTE_NAME

async def list_pastes(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user_id = query.from_user.id

    pastes = db.get_pastes(user_id)
    if not pastes:
        await query.edit_message_text("У вас пока нет добавленных паст.")
        return

    text = "📝 <b>Ваши пасты:</b>\n\n"
    for paste in pastes:
        messages = json.loads(paste["messages"])
        banned = "🚫 (Wallapop ban)" if paste.get("is_banned_wallapop") else ""
        text += f"• <b>{paste['name']}</b> - {len(messages)} сообщений {banned} [ID:{paste['id']}]\n"

    keyboard = [[InlineKeyboardButton("⬅️ Назад", callback_data="resources_menu")]]
    await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="HTML")

# ====================== ВСПОМОГАТЕЛЬНЫЕ ======================

async def run_parser(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user_id = query.from_user.id

    if BOT_STATE != "running":
        await query.edit_message_text("❌ Бот остановлен. Запустите его через меню.")
        return

    keyboard = [
        [InlineKeyboardButton("Wallapop", callback_data="parser_wallapop")],
        [InlineKeyboardButton("Milanuncios", callback_data="parser_milanuncios")],
        [InlineKeyboardButton("⬅️ Назад", callback_data="main_menu")]
    ]

    await query.edit_message_text(
        "Выберите площадку для парсинга:",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

async def run_sender(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user_id = query.from_user.id

    if BOT_STATE != "running":
        await query.edit_message_text("❌ Бот остановлен. Запустите его через меню.")
        return

    keyboard = [
        [InlineKeyboardButton("Wallapop", callback_data="sender_wallapop")],
        [InlineKeyboardButton("Milanuncios", callback_data="sender_milanuncios")],
        [InlineKeyboardButton("⬅️ Назад", callback_data="main_menu")]
    ]

    await query.edit_message_text(
        "Выберите площадку для рассылки:",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

async def start_parser(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    service = "wallapop" if "wallapop" in query.data else "milanuncios"

    task_id = f"parser_{uuid.uuid4().hex[:6]}"
    context.user_data['task_id'] = task_id

    if service == "wallapop":
        service_module = WallapopService(context, task_id)
    else:
        service_module = MilanunciosService(context, task_id)

    TASK_MANAGER[task_id] = asyncio.create_task(service_module.parser())

    await query.edit_message_text(f"✅ Парсер {service.capitalize()} запущен с жесткими критериями!")
    return ConversationHandler.END

async def start_sender(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    service = "wallapop" if "wallapop" in query.data else "milanuncios"

    task_id = f"sender_{uuid.uuid4().hex[:6]}"
    context.user_data['task_id'] = task_id

    if service == "wallapop":
        service_module = WallapopService(context, task_id)
    else:
        service_module = MilanunciosService(context, task_id)

    TASK_MANAGER[task_id] = asyncio.create_task(service_module.sender())

    await query.edit_message_text(f"✅ Рассылка на {service.capitalize()} запущена!")
    return ConversationHandler.END

# --- Бан пасты на Wallapop по callback ---
async def ban_paste_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    paste_id = int(query.data.replace("ban_paste_", ""))
    db.mark_paste_banned_on_wallapop(paste_id)
    await query.edit_message_text("✅ Паста исключена из рассылки по Wallapop.")

async def ignore_ban_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    await query.edit_message_text("Паста осталась в рассылке.")

# --- Остальные стандартные хендлеры, cancel, settings, show_stats и т.д. идут как в твоём оригинале ---

# ====================== ЗАПУСК БОТА ======================

def main():
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler(CONFIG["LOG_FILE"], encoding='utf-8'),
            logging.StreamHandler()
        ]
    )

    app = Application.builder().token(CONFIG["TELEGRAM_BOT_TOKEN"]).build()
    app.add_handler(CommandHandler("start", start_command))

    app.add_handler(CallbackQueryHandler(main_menu, pattern="^main_menu$"))
    app.add_handler(CallbackQueryHandler(toggle_bot_state, pattern="^toggle_bot_state$"))
    app.add_handler(CallbackQueryHandler(resources_menu, pattern="^resources_menu$"))
    app.add_handler(CallbackQueryHandler(run_parser, pattern="^run_parser$"))
    app.add_handler(CallbackQueryHandler(run_sender, pattern="^run_sender$"))
    app.add_handler(CallbackQueryHandler(list_proxies, pattern="^list_proxies$"))
    app.add_handler(CallbackQueryHandler(list_accounts, pattern="^list_accounts$"))
    app.add_handler(CallbackQueryHandler(list_pastes, pattern="^list_pastes$"))
    app.add_handler(CallbackQueryHandler(start_parser, pattern="^parser_(wallapop|milanuncios)$"))
    app.add_handler(CallbackQueryHandler(start_sender, pattern="^sender_(wallapop|milanuncios)$"))
    app.add_handler(CallbackQueryHandler(ban_paste_callback, pattern="^ban_paste_\\d+$"))
    app.add_handler(CallbackQueryHandler(ignore_ban_callback, pattern="^ignore_ban$"))

    # --- Хендлер для добавления прокси
    proxy_handler = ConversationHandler(
        entry_points=[CallbackQueryHandler(add_proxy_handler, pattern="^add_proxy$")],
        states={
            WAITING_PROXY: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, handle_proxy_input)
            ]
        },
        fallbacks=[],
        per_message=True
    )
    app.add_handler(proxy_handler)

    # --- Хендлер для добавления аккаунта с выбором прокси
    account_handler = ConversationHandler(
        entry_points=[
            CallbackQueryHandler(handle_account_service, pattern="^add_wallapop_account$"),
            CallbackQueryHandler(handle_account_service, pattern="^add_milanuncios_account$")
        ],
        states={
            WAITING_ACCOUNT_LOGIN: [
                CallbackQueryHandler(choose_proxy, pattern="^choose_proxy_\\d+$"),
                MessageHandler(filters.TEXT & ~filters.COMMAND, handle_account_login)
            ],
            WAITING_ACCOUNT_PASSWORD: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, handle_account_password)
            ]
        },
        fallbacks=[],
        per_message=True
    )
    app.add_handler(account_handler)

    # --- Хендлер для паст
    paste_handler = ConversationHandler(
        entry_points=[CallbackQueryHandler(add_paste_handler, pattern="^add_paste$")],
        states={
            WAITING_PASTE_NAME: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, handle_paste_name)
            ],
            WAITING_PASTE_MESSAGE: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, handle_paste_message),
                CommandHandler("done", handle_paste_done)
            ]
        },
        fallbacks=[],
        per_message=True
    )
    app.add_handler(paste_handler)

    # --- Остальные стандартные хендлеры (отмена, настройки и т.д.) подключай как в исходнике ---

    logger.info("==============================================")
    logger.info("     СИСТЕМА УПРАВЛЕНИЯ ЗАПУЩЕНА УСПЕШНО!     ")
    logger.info("==============================================")
    app.run_polling()

if __name__ == "__main__":
    main()
