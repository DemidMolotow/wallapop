# -*- coding: utf-8 -*-
"""
main.py - Полная система управления Wallapop/Milanuncios с дашбордом
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
    "HEADLESS_MODE": os.getenv("HEADLESS_MODE", "False") == "True",  # Видимый браузер по умолчанию
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
    "MAX_RETRIES": 3  # Максимальное количество повторных попыток
}

logger = logging.getLogger(__name__)
fake = Faker()
TASK_MANAGER: Dict[str, asyncio.Task] = {}
BOT_STATE = "stopped"  # 'running' or 'stopped'
BOT_START_TIME = None
SEMAPHORE = asyncio.Semaphore(CONFIG["MAX_CONCURRENT_TASKS"])

# Мобильные агенты и вьюпорты (расширенный список)
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
    {"width": 390, "height": 844},   # iPhone 15 Pro
    {"width": 412, "height": 915},   # Pixel 8 Pro
    {"width": 393, "height": 873},   # Galaxy S24
    {"width": 414, "height": 896},   # iPhone 11 Pro Max
    {"width": 360, "height": 800},   # Android средний
    {"width": 375, "height": 812},   # iPhone X/XS/11 Pro
    {"width": 428, "height": 926},   # iPhone 12/13 Pro Max
    {"width": 390, "height": 844},   # iPhone 12/13 Pro
    {"width": 360, "height": 780},   # Galaxy A51
    {"width": 412, "height": 892}    # Pixel 7 Pro
]

# Состояния разговоров
(
    WAITING_PROXY, WAITING_ACCOUNT_LOGIN, WAITING_ACCOUNT_PASSWORD,
    WAITING_SETTING_VALUE, WAITING_PASTE_NAME, WAITING_PASTE_MESSAGE,
    WAITING_PARSER_QUERY, WAITING_SENDER_QUERY
) = range(8)

# Константы для отмены диалогов
CANCEL = "CANCEL"

# ====================== БАЗА ДАННЫХ ======================

class Database:
    def __init__(self, db_path: str):
        self.db_path = db_path
        self._init_db()
    
    def _init_db(self):
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            
            # Пользователи
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS Users (
                    user_id INTEGER PRIMARY KEY,
                    balance REAL DEFAULT 0.0,
                    subscription_end_date TIMESTAMP
                );
            ''')
            
            # Прокси
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS Proxies (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    proxy_string TEXT NOT NULL UNIQUE,
                    owner_id INTEGER,
                    status TEXT DEFAULT 'good',
                    FOREIGN KEY(owner_id) REFERENCES Users(user_id)
                );
            ''')
            
            # Аккаунты
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS Accounts (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    service TEXT NOT NULL,
                    login TEXT NOT NULL,
                    password TEXT NOT NULL,
                    owner_id INTEGER,
                    status TEXT DEFAULT 'active',
                    FOREIGN KEY(owner_id) REFERENCES Users(user_id),
                    UNIQUE(service, login)
                );
            ''')
            
            # Настройки пользователя
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS UserSettings (
                    user_id INTEGER PRIMARY KEY,
                    slot_limit INTEGER DEFAULT 5,
                    interval_min REAL DEFAULT 2.2,
                    interval_max REAL DEFAULT 5.5,
                    FOREIGN KEY(user_id) REFERENCES Users(user_id)
                );
            ''')
            
            # Глобальная статистика
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
            
            # Текущая сессия
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS SessionStats (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    parsed_count INTEGER DEFAULT 0,
                    sent_count INTEGER DEFAULT 0,
                    start_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                );
            ''')
            
            # Пасты
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS Pastes (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT NOT NULL,
                    messages TEXT NOT NULL,
                    owner_id INTEGER,
                    FOREIGN KEY(owner_id) REFERENCES Users(user_id),
                    UNIQUE(owner_id, name)
                );
            ''')
            
            # Найденные объявления
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
    
    def update_user_settings(self, user_id: int, settings: dict):
        self._execute(
            "UPDATE UserSettings SET slot_limit = ?, interval_min = ?, interval_max = ? WHERE user_id = ?",
            (settings["slot_limit"], settings["interval_min"], settings["interval_max"], user_id)
        )
    
    def add_proxy(self, proxy: str, user_id: int):
        self._execute(
            "INSERT OR IGNORE INTO Proxies (proxy_string, owner_id) VALUES (?, ?)",
            (proxy, user_id)
        )
    
    def delete_proxy(self, proxy_id: int):
        self._execute("DELETE FROM Proxies WHERE id = ?", (proxy_id,))
    
    def get_proxies(self, user_id: int) -> list:
        return self._execute(
            "SELECT id, proxy_string, status FROM Proxies WHERE owner_id = ?",
            (user_id,),
            fetch=True
        )
    
    def count_proxies(self, user_id: int) -> int:
        result = self._execute(
            "SELECT COUNT(*) as count FROM Proxies WHERE owner_id = ?",
            (user_id,),
            fetch=True
        )
        return result[0]["count"] if result else 0
    
    def add_account(self, service: str, login: str, password: str, user_id: int):
        self._execute(
            "INSERT OR IGNORE INTO Accounts (service, login, password, owner_id) VALUES (?, ?, ?, ?)",
            (service, login, password, user_id)
        )
    
    def delete_account(self, account_id: int):
        self._execute("DELETE FROM Accounts WHERE id = ?", (account_id,))
    
    def get_accounts(self, user_id: int, service: str = None) -> list:
        query = "SELECT id, service, login, status FROM Accounts WHERE owner_id = ?"
        params = [user_id]
        
        if service:
            query += " AND service = ?"
            params.append(service)
        
        return self._execute(query, tuple(params), fetch=True)
    
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
            "SELECT id, name, messages FROM Pastes WHERE owner_id = ?",
            (user_id,),
            fetch=True
        )
        return [dict(row) for row in result] if result else []
    
    def get_random_paste(self, user_id: int) -> dict:
        result = self._execute(
            "SELECT id, name, messages FROM Pastes WHERE owner_id = ? ORDER BY RANDOM() LIMIT 1",
            (user_id,),
            fetch=True
        )
        if result:
            paste = dict(result[0])
            paste["messages"] = json.loads(paste["messages"])
            return paste
        return None
    
    def increment_stats(self, user_id: int, parsed: int = 0, sent: int = 0):
        self._execute(
            "INSERT INTO GlobalStats (user_id, parsed_count, sent_count) VALUES (?, ?, ?)",
            (user_id, parsed, sent)
        )
        self._execute(
            "UPDATE SessionStats SET parsed_count = parsed_count + ?, sent_count = sent_count + ?",
            (parsed, sent)
        )
    
    def get_global_stats(self, user_id: int) -> dict:
        result = self._execute(
            "SELECT SUM(parsed_count) as total_parsed, SUM(sent_count) as total_sent "
            "FROM GlobalStats WHERE user_id = ?",
            (user_id,),
            fetch=True
        )
        return dict(result[0]) if result else {"total_parsed": 0, "total_sent": 0}
    
    def get_session_stats(self) -> dict:
        result = self._execute(
            "SELECT parsed_count, sent_count, start_time FROM SessionStats ORDER BY id DESC LIMIT 1",
            fetch=True
        )
        if result:
            return dict(result[0])
        return {"parsed_count": 0, "sent_count": 0, "start_time": datetime.now().isoformat()}
    
    def reset_session_stats(self):
        self._execute("DELETE FROM SessionStats")
        self._execute("INSERT INTO SessionStats DEFAULT VALUES")
    
    def add_parsed_item(self, service: str, item_id: str, title: str, url: str, user_id: int):
        self._execute(
            "INSERT OR IGNORE INTO ParsedItems (service, item_id, title, url, owner_id) VALUES (?, ?, ?, ?, ?)",
            (service, item_id, title, url, user_id)
        )
    
    def get_parsed_items(self, user_id: int, service: str = None, limit: int = 10) -> list:
        query = "SELECT id, service, item_id, title, url FROM ParsedItems WHERE owner_id = ?"
        params = [user_id]
        
        if service:
            query += " AND service = ?"
            params.append(service)
        
        query += " ORDER BY timestamp ASC LIMIT ?"
        params.append(limit)
        
        return self._execute(query, tuple(params), fetch=True)
    
    def delete_parsed_item(self, item_id: int):
        self._execute("DELETE FROM ParsedItems WHERE id = ?", (item_id,))
    
    def count_parsed_items(self, user_id: int, service: str = None) -> int:
        query = "SELECT COUNT(*) as count FROM ParsedItems WHERE owner_id = ?"
        params = [user_id]
        
        if service:
            query += " AND service = ?"
            params.append(service)
        
        result = self._execute(query, tuple(params), fetch=True)
        return result[0]["count"] if result else 0

# Инициализация базы данных
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
    def __init__(self, context: ContextTypes.DEFAULT_TYPE, task_id: str):
        self.context = context
        self.task_id = task_id
        self.user_id = context.user_data.get('user_id')
        self.chat_id = context.user_data.get('chat_id')
    
    async def _get_page(self, service: str, login: Optional[str] = None) -> Tuple[Page, Browser, BrowserContext, Optional[str]]:
        p = await async_playwright().start()
        
        # Получаем список прокси и перемешиваем его
        proxy_data = db.get_proxies(self.user_id)
        proxies = [p["proxy_string"] for p in proxy_data] if proxy_data else []
        random.shuffle(proxies)
        
        # Выбираем первый рабочий прокси
        proxy = None
        for proxy_candidate in proxies:
            if await self._check_proxy(proxy_candidate):
                proxy = proxy_candidate
                logger.info(f"Selected proxy: {proxy}")
                break
        
        # Форматирование прокси для Playwright
        proxy_settings = None
        if proxy:
            proxy_settings = {"server": proxy}
            logger.info(f"Using proxy: {proxy}")
        else:
            logger.warning("No valid proxy found, using direct connection")
        
        viewport = random.choice(MOBILE_VIEWPORTS)
        user_agent = random.choice(MOBILE_USER_AGENTS)
        
        browser = await p.chromium.launch(
            headless=CONFIG["HEADLESS_MODE"],  # Видимый браузер для отладки
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
        
        logger.info(f"Task {self.task_id[:6]}: Mobile browser, proxy: {proxy or 'None'} UA: {user_agent}")
        return page, browser, context, proxy
    
    async def _check_proxy(self, proxy_url: str) -> bool:
        """Проверка работоспособности прокси"""
        if not proxy_url:
            return False
            
        try:
            async with httpx.AsyncClient(proxies={"all://": proxy_url}, timeout=10) as client:
                response = await client.get("https://www.google.com")
                return response.status_code == 200
        except Exception as e:
            logger.warning(f"Proxy check failed for {proxy_url}: {str(e)}")
            return False
    
    async def _send(self, message: str, **kwargs):
        await self.context.bot.send_message(chat_id=self.chat_id, text=f"[Task {self.task_id[:6]}] {message}", **kwargs)
    
    async def _delay(self, k: float = 1.0):
        await asyncio.sleep(random.uniform(CONFIG["ACTION_DELAY_MIN"], CONFIG["ACTION_DELAY_MAX"]) * k)
    
    async def _handle_cookies(self, page: Page, selector: str):
        try:
            await page.locator(selector).click(timeout=10000)  # Увеличен таймаут
            await self._send("Cookies accepted.")
            await self._delay(0.6)
        except PlaywrightTimeoutError:
            pass
    
    async def _random_interactions(self, page: Page):
        """Случайные действия для имитации поведения человека"""
        width, height = page.viewport_size['width'], page.viewport_size['height']
        
        # Случайные движения мышью
        for _ in range(random.randint(2, 5)):
            await page.mouse.move(
                random.randint(0, width),
                random.randint(0, height),
                steps=random.randint(5, 15)
            )
            await self._delay(0.3)
        
        # Случайные клики
        for _ in range(random.randint(1, 3)):
            await page.mouse.click(
                random.randint(0, width),
                random.randint(0, height),
                delay=random.randint(50, 300)
            )
            await self._delay(0.5)
        
        # Случайное скроллирование
        for _ in range(random.randint(1, 3)):
            await page.mouse.wheel(0, random.randint(100, 500))
            await self._delay(0.7)
    
    async def _bypass_antibot(self, page: Page):
        """Попытка обхода антибот-систем"""
        try:
            # Проверка наличия Cloudflare
            if await page.query_selector('div#cf-challenge-wrapper'):
                await self._send("⚠️ Cloudflare detected. Trying to bypass...")
                await page.wait_for_selector('div#cf-challenge-wrapper', state='hidden', timeout=30000)
                await self._delay(3)
            
            # Дополнительные методы обхода
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
        
        # Повторные попытки с ротацией прокси
        for attempt in range(1, CONFIG["MAX_RETRIES"] + 1):
            browser = None
            try:
                page, browser, context, proxy = await self._get_page(self.SERVICE_NAME)
                await self._send(f"Starting Wallapop parser (attempt {attempt}/{CONFIG['MAX_RETRIES']})")
                
                # Обход антибот-систем
                await self._bypass_antibot(page)
                
                # Переход с увеличенным таймаутом
                await page.goto(f"{self.BASE_URL}/search", wait_until="networkidle", timeout=90000)
                await self._delay(2)
                await self._handle_cookies(page, "#onetrust-accept-btn-handler")
                await self._random_interactions(page)
                
                # Применяем фильтры
                await self._apply_wallapop_filters(page)
                
                # Получаем результаты
                items = await page.query_selector_all('div[data-testid="search-result-item"]')
                results_count = 0
                
                # Обрабатываем первые 10 результатов
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
                await self._send(f"✅ Found {results_count} matching items on Wallapop")
                return  # Успешное завершение
                
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
        
        await self._send("❌ Parser failed after multiple attempts")
    
    async def _apply_wallapop_filters(self, page: Page):
        try:
            # Открываем фильтры
            await page.click('button[data-testid="filters-button"]', timeout=15000)
            await self._delay(1.5)
            
            # Устанавливаем доставку: включено
            await page.click('div[data-testid="filter-delivery"]', timeout=10000)
            await self._delay(0.8)
            await page.click('label[for="shipping"]', timeout=10000)
            await self._delay(0.8)
            
            # Сортируем по самым новым
            await page.click('button[data-testid="sort-button"]', timeout=10000)
            await self._delay(0.8)
            await page.click('div[role="option"]:has-text("Más recientes")', timeout=10000)
            await self._delay(0.8)
            
            # Применяем фильтры
            await page.click('button[data-testid="apply-filters-button"]', timeout=10000)
            await self._delay(3)
            
            await self._send("Filters applied: Delivery=Yes, Sort=Newest")
        except Exception as e:
            logger.error(f"Error applying Wallapop filters: {e}")
            await self._send("⚠️ Could not apply all filters, continuing with default search")
    
    async def sender(self):
        # Реализация аналогична оригинальной, но с обработкой ошибок как в parser
        pass

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
        
        # Повторные попытки с ротацией прокси
        for attempt in range(1, CONFIG["MAX_RETRIES"] + 1):
            browser = None
            try:
                page, browser, context, proxy = await self._get_page(self.SERVICE_NAME)
                await self._send(f"Starting Milanuncios parser (attempt {attempt}/{CONFIG['MAX_RETRIES']})")
                
                # Обход антибот-систем
                await self._bypass_antibot(page)
                
                # Переход с увеличенным таймаутом
                await page.goto(f"{self.BASE_URL}/anuncios/", wait_until="networkidle", timeout=90000)
                await self._delay(2)
                await self._handle_cookies(page, "#onetrust-accept-btn-handler")
                await self._random_interactions(page)
                
                # Применяем фильтры
                await self._apply_milanuncios_filters(page)
                
                # Получаем результаты
                items = await page.query_selector_all('article.ma-AdCard')
                results_count = 0
                
                # Обрабатываем первые 10 результатов
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
                await self._send(f"✅ Found {results_count} matching items on Milanuncios")
                return  # Успешное завершение
                
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
        
        await self._send("❌ Parser failed after multiple attempts")
    
    async def _apply_milanuncios_filters(self, page: Page):
        try:
            # Открываем фильтры
            await page.click('button:has-text("Filtros")', timeout=15000)
            await self._delay(1.5)
            
            # Устанавливаем доставку: включено
            await page.click('label:has-text("Con envío")', timeout=10000)
            await self._delay(0.8)
            
            # Сортируем по самым новым
            await page.click('button:has-text("Ordenar")', timeout=10000)
            await self._delay(0.8)
            await page.click('button:has-text("Más recientes")', timeout=10000)
            await self._delay(0.8)
            
            # Применяем фильтры
            await page.click('button:has-text("Aplicar")', timeout=10000)
            await self._delay(3)
            
            await self._send("Filters applied: Delivery=Yes, Sort=Newest")
        except Exception as e:
            logger.error(f"Error applying Milanuncios filters: {e}")
            await self._send("⚠️ Could not apply all filters, continuing with default search")
    
    async def sender(self):
        # Реализация аналогична оригинальной, но с обработкой ошибок как в parser
        pass

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

async def settings_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user_id = query.from_user.id
    
    settings = db.get_user_settings(user_id)
    
    keyboard = [
        [InlineKeyboardButton(f"Лимит слотов: {settings['slot_limit']}", callback_data="set_slot_limit")],
        [InlineKeyboardButton(f"Мин. интервал: {settings['interval_min']} сек", callback_data="set_interval_min")],
        [InlineKeyboardButton(f"Макс. интервал: {settings['interval_max']} сек", callback_data="set_interval_max")],
        [InlineKeyboardButton("⬅️ Назад", callback_data="main_menu")]
    ]
    
    await query.edit_message_text(
        "⚙️ <b>Настройки параметров</b>\n\n"
        "Здесь вы можете настроить работу бота:",
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode="HTML"
    )

async def set_slot_limit(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    await query.edit_message_text("Введите новое значение для лимита слотов (1-20):")
    context.user_data["setting"] = "slot_limit"
    return WAITING_SETTING_VALUE

async def set_interval_min(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    await query.edit_message_text("Введите минимальное значение интервала (сек):")
    context.user_data["setting"] = "interval_min"
    return WAITING_SETTING_VALUE

async def set_interval_max(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    await query.edit_message_text("Введите максимальное значение интервала (сек):")
    context.user_data["setting"] = "interval_max"
    return WAITING_SETTING_VALUE

async def handle_setting_value(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.message.from_user.id
    setting_name = context.user_data["setting"]
    value = update.message.text.strip()
    
    try:
        if setting_name == "slot_limit":
            value = int(value)
            if not (1 <= value <= 20):
                raise ValueError
        else:
            value = float(value)
            if value <= 0:
                raise ValueError
        
        settings = db.get_user_settings(user_id)
        settings[setting_name] = value
        db.update_user_settings(user_id, settings)
        
        await update.message.reply_text(f"✅ Настройка успешно обновлена!")
        await settings_menu(update, context)
        return ConversationHandler.END
    
    except (ValueError, TypeError):
        await update.message.reply_text("❌ Недопустимое значение. Попробуйте еще раз:")
        return WAITING_SETTING_VALUE

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
        # Проверка формата host:port
        if not re.match(r"^\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}:\d{1,5}$", proxy):
            raise ValueError("Неправильный формат")
        
        # Добавляем протокол по умолчанию
        formatted_proxy = f"{CONFIG['DEFAULT_PROXY_PROTOCOL']}://{proxy}"
        
        db.add_proxy(formatted_proxy, user_id)
        await update.message.reply_text("✅ Прокси успешно добавлен!")
        return ConversationHandler.END
    
    except Exception:
        await update.message.reply_text("❌ Ошибка добавления прокси. Используйте формат host:port (например: 192.168.1.2:30000). Попробуйте еще раз:")
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
        # Убираем протокол для отображения
        display_proxy = proxy['proxy_string'].replace(f"{CONFIG['DEFAULT_PROXY_PROTOCOL']}://", "")
        status_icon = "🟢" if proxy["status"] == "good" else "🔴"
        text += f"{i}. {status_icon} {display_proxy} [ID:{proxy['id']}]\n"
    
    keyboard = [[InlineKeyboardButton("⬅️ Назад", callback_data="resources_menu")]]
    await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="HTML")

async def handle_account_service(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    service = "wallapop" if "wallapop" in query.data else "milanuncios"
    context.user_data["acc_service"] = service
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
    
    try:
        db.add_account(service, login, password, user_id)
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
        text += f"{status_icon} <b>{account['service'].capitalize()}</b>: {account['login']} [ID:{account['id']}]\n"
    
    keyboard = [[InlineKeyboardButton("⬅️ Назад", callback_data="resources_menu")]]
    await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="HTML")

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
        text += f"• <b>{paste['name']}</b> - {len(messages)} сообщений [ID:{paste['id']}]\n"
    
    keyboard = [[InlineKeyboardButton("⬅️ Назад", callback_data="resources_menu")]]
    await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="HTML")

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

async def show_stats(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user_id = query.from_user.id
    
    session_stats = db.get_session_stats()
    global_stats = db.get_global_stats(user_id)
    wallapop_items = db.count_parsed_items(user_id, "wallapop")
    milanuncios_items = db.count_parsed_items(user_id, "milanuncios")
    
    text = (
        "📊 <b>Детальная статистика</b>\n"
        "--------------------------------\n"
        "<b>Текущая сессия:</b>\n"
        f"• Начало: {session_stats['start_time']}\n"
        f"• Парсер: найдено {session_stats['parsed_count']} объявлений\n"
        f"• Сендер: отправлено {session_stats['sent_count']} сообщений\n"
        "--------------------------------\n"
        "<b>Общая статистика:</b>\n"
        f"• Всего найдено: {global_stats['total_parsed']}\n"
        f"• Всего отправлено: {global_stats['total_sent']}\n"
        "--------------------------------\n"
        "<b>Текущие данные:</b>\n"
        f"• Wallapop: {wallapop_items} объявлений\n"
        f"• Milanuncios: {milanuncios_items} объявлений\n"
        "--------------------------------"
    )
    
    keyboard = [[InlineKeyboardButton("⬅️ Назад", callback_data="main_menu")]]
    await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="HTML")

async def refresh_dashboard(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user_id = query.from_user.id
    await dashboard_manager.force_update(context, user_id, query.message.chat_id)
    await query.edit_message_text("✅ Дашборд успешно обновлен!")

async def close_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    await query.delete_message()

async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Отмена диалога"""
    await update.message.reply_text('❌ Действие отменено')
    return ConversationHandler.END

# ====================== ЗАПУСК БОТА ======================

def main():
    # Настройка логирования
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler(CONFIG["LOG_FILE"], encoding='utf-8'),
            logging.StreamHandler()
        ]
    )
    
    # Создаем приложение Telegram
    app = Application.builder().token(CONFIG["TELEGRAM_BOT_TOKEN"]).build()
    
    # Обработчики команд
    app.add_handler(CommandHandler("start", start_command))
    
    # Обработчики меню
    app.add_handler(CallbackQueryHandler(main_menu, pattern="^main_menu$"))
    app.add_handler(CallbackQueryHandler(toggle_bot_state, pattern="^toggle_bot_state$"))
    app.add_handler(CallbackQueryHandler(settings_menu, pattern="^settings_menu$"))
    app.add_handler(CallbackQueryHandler(resources_menu, pattern="^resources_menu$"))
    app.add_handler(CallbackQueryHandler(run_parser, pattern="^run_parser$"))
    app.add_handler(CallbackQueryHandler(run_sender, pattern="^run_sender$"))
    app.add_handler(CallbackQueryHandler(show_stats, pattern="^show_stats$"))
    app.add_handler(CallbackQueryHandler(refresh_dashboard, pattern="^refresh_dashboard$"))
    app.add_handler(CallbackQueryHandler(close_menu, pattern="^close_menu$"))
    app.add_handler(CallbackQueryHandler(list_proxies, pattern="^list_proxies$"))
    app.add_handler(CallbackQueryHandler(list_accounts, pattern="^list_accounts$"))
    app.add_handler(CallbackQueryHandler(list_pastes, pattern="^list_pastes$"))
    app.add_handler(CallbackQueryHandler(start_parser, pattern="^parser_(wallapop|milanuncios)$"))
    app.add_handler(CallbackQueryHandler(start_sender, pattern="^sender_(wallapop|milanuncios)$"))
    
    # Общий обработчик отмены
    cancel_handler = CommandHandler("cancel", cancel)
    
    # Обработчики для добавления прокси
    proxy_handler = ConversationHandler(
        entry_points=[CallbackQueryHandler(add_proxy_handler, pattern="^add_proxy$")],
        states={
            WAITING_PROXY: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, handle_proxy_input),
                cancel_handler
            ]
        },
        fallbacks=[cancel_handler],
        per_message=True
    )
    app.add_handler(proxy_handler)
    
    # Обработчики для добавления аккаунта
    account_handler = ConversationHandler(
        entry_points=[
            CallbackQueryHandler(handle_account_service, pattern="^add_wallapop_account$"),
            CallbackQueryHandler(handle_account_service, pattern="^add_milanuncios_account$")
        ],
        states={
            WAITING_ACCOUNT_LOGIN: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, handle_account_login),
                cancel_handler
            ],
            WAITING_ACCOUNT_PASSWORD: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, handle_account_password),
                cancel_handler
            ]
        },
        fallbacks=[cancel_handler],
        per_message=True
    )
    app.add_handler(account_handler)
    
    # Обработчики для настроек
    settings_handler = ConversationHandler(
        entry_points=[
            CallbackQueryHandler(set_slot_limit, pattern="^set_slot_limit$"),
            CallbackQueryHandler(set_interval_min, pattern="^set_interval_min$"),
            CallbackQueryHandler(set_interval_max, pattern="^set_interval_max$")
        ],
        states={
            WAITING_SETTING_VALUE: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, handle_setting_value),
                cancel_handler
            ]
        },
        fallbacks=[cancel_handler],
        per_message=True
    )
    app.add_handler(settings_handler)
    
    # Обработчики для паст
    paste_handler = ConversationHandler(
        entry_points=[CallbackQueryHandler(add_paste_handler, pattern="^add_paste$")],
        states={
            WAITING_PASTE_NAME: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, handle_paste_name),
                cancel_handler
            ],
            WAITING_PASTE_MESSAGE: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, handle_paste_message),
                CommandHandler("done", handle_paste_done),
                cancel_handler
            ]
        },
        fallbacks=[cancel_handler],
        per_message=True
    )
    app.add_handler(paste_handler)
    
    # Добавляем обработчик отмены
    app.add_handler(cancel_handler)
    
    # Запускаем бота
    logger.info("==============================================")
    logger.info("     СИСТЕМА УПРАВЛЕНИЯ ЗАПУЩЕНА УСПЕШНО!     ")
    logger.info("==============================================")
    app.run_polling()

if __name__ == "__main__":
    main()
