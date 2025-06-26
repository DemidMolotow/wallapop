# -*- coding: utf-8 -*-
"""
main.py Wallapop/Milanuncios - антифрод максимальный (мобильный, mouse/touch, cookies, proxy mgr)
Часть 1/8: Импорты, настройки, DataManager, ProxyManager, CookieManager, базовые сервисные классы.
"""

import asyncio
import json
import logging
import os
import random
import threading
import uuid
from typing import Dict, Any, List, Tuple, Optional
from datetime import datetime

from faker import Faker
from playwright.async_api import async_playwright, Page, Browser, TimeoutError as PlaywrightTimeoutError, BrowserContext
from playwright_stealth import stealth_async
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, InputFile
from telegram.ext import (Application, CommandHandler, CallbackQueryHandler,
                          MessageHandler, ConversationHandler, ContextTypes, filters)

CONFIG = {
    "TELEGRAM_BOT_TOKEN": "7512529507:AAHga264aQDpBF9fsSHrvDVgInkjwfPJ96o",
    "HEADLESS_MODE": False,
    "MAX_CONCURRENT_TASKS": 5,
    "DATA_FILE": "bot_data.json",
    "COOKIES_DIR": "cookies",
    "LOG_FILE": "bot_logs.log",
    "ACTION_DELAY_MIN": 2.2,
    "ACTION_DELAY_MAX": 5.5,
    "SURF_STEPS_MIN": 2,
    "SURF_STEPS_MAX": 5,
    "SCROLLS_PER_PAGE": 2,
}

logger = logging.getLogger(__name__)
fake = Faker()
MAX_PARSER_RESULTS = 30
TASK_MANAGER: Dict[str, asyncio.Task] = {}

MOBILE_USER_AGENTS = [
    # Самые частые на 2025 год/Android/iOS
    "Mozilla/5.0 (Linux; Android 14; SM-S918B) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Mobile Safari/537.36",
    "Mozilla/5.0 (Linux; Android 14; Pixel 8 Pro) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Mobile Safari/537.36",
    "Mozilla/5.0 (iPhone; CPU iPhone OS 17_5_1 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0 Mobile/15E148 Safari/604.1",
    "Mozilla/5.0 (Linux; Android 14; Redmi Note 13 Pro) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Mobile Safari/537.36",
]

MOBILE_VIEWPORTS = [
    {"width": 390, "height": 844},   # iPhone 15 Pro
    {"width": 412, "height": 915},   # Pixel 8 Pro
    {"width": 393, "height": 873},   # Galaxy S24
    {"width": 414, "height": 896},   # iPhone 11 Pro Max
    {"width": 360, "height": 800},   # Android средний
]

# ПРАВИЛЬНО
(
    MENU, MANAGE, ADD_PROXY, ADD_PROXY_INPUT, DEL_PROXY, DEL_PROXY_CHOOSE, LIST_PROXY,
    ADD_ACCOUNT, ADD_ACCOUNT_SERVICE, ADD_ACCOUNT_LOGIN, ADD_ACCOUNT_PASS, ADD_ACCOUNT_TYPE, ADD_ACCOUNT_GOOGLE_EMAIL, ADD_ACCOUNT_GOOGLE_PASS,
    DEL_ACCOUNT, DEL_ACCOUNT_CHOOSE, LIST_ACCOUNT,
    ADD_PASTE, PASTE_ADD_TEXT, PASTE_ADD_DONE, DEL_PASTE, DEL_PASTE_CHOOSE, LIST_PASTE,
    PARSER_CRITERIA, PARSER_CRITERIA_INPUT, PARSER_SERVICE, PARSER_RESULTS, PARSER_DATE,
    SENDER_START, SENDER_CHOOSE_SERVICE, SENDER_CHOOSE_ACC, SENDER_CHOOSE_PASTE, SENDER_QUERY, SENDER_CONFIRM, SENDER_PROGRESS
) = range(35)

# ============== DataManager, ProxyManager, CookieManager ================
class DataManager:
    _lock = threading.Lock()
    @staticmethod
    def _load() -> Dict:
        with DataManager._lock:
            if not os.path.exists(CONFIG["DATA_FILE"]): return {"proxies": [], "accounts": [], "pastes": []}
            try:
                with open(CONFIG["DATA_FILE"], 'r', encoding='utf-8') as f: return json.load(f)
            except (json.JSONDecodeError, FileNotFoundError): return {"proxies": [], "accounts": [], "pastes": []}
    @staticmethod
    def _save(data: Dict):
        with DataManager._lock:
            with open(CONFIG["DATA_FILE"], 'w', encoding='utf-8') as f: json.dump(data, f, indent=4, ensure_ascii=False)
    @classmethod
    def add(cls, key: str, value: Any):
        data = cls._load()
        if key not in data: data[key] = []
        if value in data[key]: return False
        data[key].append(value)
        cls._save(data)
        return True
    @classmethod
    def get(cls, key: str) -> List:
        return cls._load().get(key, [])
    @classmethod
    def delete(cls, key: str, idx: int) -> bool:
        data = cls._load()
        if key in data and 0 <= idx < len(data[key]):
            data[key].pop(idx)
            cls._save(data)
            return True
        return False
    # Аккаунты и пасты — отдельные методы для поиска по id и имени
    @classmethod
    def accounts(cls) -> List[Dict]:
        return cls.get("accounts")
    @classmethod
    def get_account_by_id(cls, acc_id: str) -> Optional[Dict]:
        return next((acc for acc in cls.accounts() if acc.get("id") == acc_id), None)
    @classmethod
    def add_account(cls, acc: Dict) -> bool:
        data = cls._load()
        accs = data.get("accounts", [])
        if any(a["login"] == acc["login"] and a["service"] == acc["service"] for a in accs): return False
        accs.append(acc)
        data["accounts"] = accs
        cls._save(data)
        return True
    @classmethod
    def delete_account(cls, acc_id: str) -> bool:
        data = cls._load()
        accs = data.get("accounts", [])
        new_accs = [a for a in accs if a.get("id") != acc_id]
        if len(new_accs) == len(accs): return False
        data["accounts"] = new_accs
        cls._save(data)
        return True
    @classmethod
    def proxies(cls) -> List[str]:
        return cls.get("proxies")
    @classmethod
    def add_proxy(cls, proxy: str) -> bool:
        data = cls._load()
        if "proxies" not in data: data["proxies"] = []
        if proxy in data["proxies"]: return False
        data["proxies"].append(proxy)
        cls._save(data)
        return True
    @classmethod
    def delete_proxy(cls, proxy: str) -> bool:
        data = cls._load()
        proxies = data.get("proxies", [])
        new_proxies = [p for p in proxies if p != proxy]
        if len(new_proxies) == len(proxies): return False
        data["proxies"] = new_proxies
        cls._save(data)
        return True
    @classmethod
    def random_proxy(cls) -> Optional[str]:
        proxies = cls.proxies()
        return random.choice(proxies) if proxies else None
    @classmethod
    def pastes(cls) -> List[Dict]:
        return cls.get("pastes")
    @classmethod
    def add_paste(cls, name: str, messages: List[str]) -> bool:
        data = cls._load()
        pastes = data.get("pastes", [])
        if any(p["name"] == name for p in pastes): return False
        pastes.append({"name": name, "messages": messages})
        data["pastes"] = pastes
        cls._save(data)
        return True
    @classmethod
    def delete_paste(cls, name: str) -> bool:
        data = cls._load()
        pastes = data.get("pastes", [])
        new_pastes = [p for p in pastes if p["name"] != name]
        if len(new_pastes) == len(pastes): return False
        data["pastes"] = new_pastes
        cls._save(data)
        return True
    @classmethod
    def get_paste(cls, name: str) -> Optional[Dict]:
        return next((p for p in cls.pastes() if p["name"] == name), None)
    @classmethod
    def get_paste_names(cls) -> List[str]:
        return [p["name"] for p in cls.pastes()]
    @classmethod
    def get_random_paste(cls) -> Optional[Dict]:
        pastes = cls.pastes()
        return random.choice(pastes) if pastes else None

class ProxyManager:
    """Прокси-менеджер с автоматической заменой 'битых' прокси"""
    _lock = threading.Lock()
    _bad_proxies: set = set()
    @classmethod
    def get_proxy(cls) -> Optional[str]:
        proxies = [p for p in DataManager.proxies() if p not in cls._bad_proxies]
        if not proxies:
            cls._bad_proxies.clear()
            proxies = DataManager.proxies()
        if not proxies:
            return None
        return random.choice(proxies)
    @classmethod
    def mark_bad(cls, proxy: str):
        with cls._lock:
            cls._bad_proxies.add(proxy)
    @classmethod
    def mark_good(cls, proxy: str):
        with cls._lock:
            if proxy in cls._bad_proxies:
                cls._bad_proxies.remove(proxy)

class CookieManager:
    """Сохраняет и грузит cookies для каждого аккаунта по сервису"""
    @staticmethod
    def get_cookie_path(service: str, login: str) -> str:
        safe = login.replace("@", "_at_").replace(":", "_")
        dirp = CONFIG["COOKIES_DIR"]
        if not os.path.exists(dirp): os.makedirs(dirp)
        return os.path.join(dirp, f"{service}_{safe}.json")
    @staticmethod
    async def save_cookies(context: BrowserContext, service: str, login: str):
        path = CookieManager.get_cookie_path(service, login)
        cookies = await context.cookies()
        with open(path, "w", encoding="utf-8") as f:
            json.dump(cookies, f)
    @staticmethod
    async def load_cookies(context: BrowserContext, service: str, login: str):
        path = CookieManager.get_cookie_path(service, login)
        if os.path.exists(path):
            with open(path, "r", encoding="utf-8") as f:
                cookies = json.load(f)
            await context.add_cookies(cookies)
            
# v-- НАЧАЛО НОВОГО БЛОКА --v
# ПРАВИЛЬНО
def run_task_in_background(coroutine: asyncio.coroutines.coroutine):
    """Создает и запускает задачу в фоне, управляя ее жизненным циклом."""
    task_id = str(uuid.uuid4())

    async def task_wrapper():
        try:
            await coroutine
        except Exception as e:
            logger.error(f"Критическая ошибка в задаче {task_id[:6]}: {e}", exc_info=True)
        finally:
            # Удаляем задачу из менеджера по завершении
            TASK_MANAGER.pop(task_id, None)
            logger.info(f"Задача {task_id[:6]} завершена и удалена из менеджера.")

    task = asyncio.create_task(task_wrapper())
    TASK_MANAGER[task_id] = task
    logger.info(f"Запущена новая фоновая задача. ID: {task_id[:6]}. Всего активных: {len(TASK_MANAGER)}")
# ^-- КОНЕЦ НОВОГО БЛОКА --^

            

# ======= Базовый сервис (мобильный, mouse/touch, scroll, имитация “серфинга”) ==========
class BaseServiceModule:
    def __init__(self, context: ContextTypes.DEFAULT_TYPE, task_id: str):
        self.context, self.task_id = context, task_id
        self.chat_id = context.user_data.get('chat_id')
    async def _get_page(self, service: str, login: Optional[str]=None) -> Tuple[Page, Browser, BrowserContext, Optional[str]]:
        p = await async_playwright().start()
        proxy = ProxyManager.get_proxy()
        viewport = random.choice(MOBILE_VIEWPORTS)
        user_agent = random.choice(MOBILE_USER_AGENTS)
        browser = await p.chromium.launch(
            headless=CONFIG["HEADLESS_MODE"],
            proxy={"server": proxy} if proxy else None
        )
        context = await browser.new_context(
            user_agent=user_agent,
            viewport=viewport,
            locale="es-ES",
            is_mobile=True,
            device_scale_factor=2.6,
            java_script_enabled=True,
            has_touch=True,
            permissions=["geolocation"]
        )
        page = await context.new_page()
        await stealth_async(page)
        if login:
            await CookieManager.load_cookies(context, service, login)
        logger.info(f"Задача {self.task_id[:6]}: браузер Mobile, прокси: {proxy or 'Нет'} UA: {user_agent}")
        return page, browser, context, proxy
    async def _send(self, message: str, **kwargs):
        await self.context.bot.send_message(chat_id=self.chat_id, text=f"[Задача {self.task_id[:6]}] {message}", **kwargs)
    async def _delay(self, k: float=1.0):
        await asyncio.sleep(random.uniform(CONFIG["ACTION_DELAY_MIN"], CONFIG["ACTION_DELAY_MAX"])*k)
    async def _handle_cookies(self, page: Page, selector: str):
        try:
            await page.locator(selector).click(timeout=7000)
            await self._send("Приняты cookies.")
            await self._delay(0.6)
        except PlaywrightTimeoutError:
            logger.warning(f"Задача {self.task_id[:6]}: Селектор cookies не найден.")
    async def _mouse_surf(self, page: Page):
        """Имитация тапа/скролла/случайных переходов"""
        width, height = page.viewport_size['width'], page.viewport_size['height']
        # Скроллы
        for _ in range(random.randint(1, CONFIG["SCROLLS_PER_PAGE"])):
            await page.mouse.wheel(0, random.randint(200, height-100))
            await self._delay(0.5)
        # Тапы/клики
        for _ in range(random.randint(CONFIG["SURF_STEPS_MIN"], CONFIG["SURF_STEPS_MAX"])):
            x = random.randint(10, width - 10)
            y = random.randint(80, height - 40)
            await page.mouse.move(x, y, steps=random.randint(5, 20))
            await self._delay(0.4)
            await page.mouse.down()
            await self._delay(0.1)
            await page.mouse.up()
            await self._delay(0.6)
        # Possible случайные переходы по ссылкам
        links = await page.query_selector_all('a')
        links = [l for l in links if (await l.is_visible()) and (await l.get_attribute('href'))]
        if links and random.random() < 0.5:
            lnk = random.choice(links)
            await lnk.click()
            await self._delay(1.5)
            await page.go_back()
            await self._delay(0.6)

# Следующая часть: WallapopService, MilanunciosService с актуальными мобильными селекторами и обходом.
# -*- coding: utf-8 -*-
"""
main.py (Часть 2/8) Wallapop/MilanunciosService (мобильный обход фрода, актуальные селекторы 2025)
"""

# =================== WALLAPOP SERVICE (мобильный, антибот) ===================

class WallapopService(BaseServiceModule):
    SERVICE_NAME = "wallapop"
    BASE_URL = "https://es.wallapop.com"

    async def _login_email(self, page: Page, account: Dict, context: BrowserContext):
        await self._send(f"Выполняю вход (email) в {account['login']}...")
        try:
            await page.goto(f"{self.BASE_URL}/login", wait_until="networkidle")
            await self._handle_cookies(page, "#onetrust-accept-btn-handler")
            await self._mouse_surf(page)
            await page.fill('input[type="email"]', account['login'])
            await self._delay(0.9)
            await page.fill('input[type="password"]', account['password'])
            await self._delay(0.8)
            await page.locator('button[type="submit"]').click()
            await self._delay(2)
            await self._mouse_surf(page)
            await page.wait_for_selector('a[data-testid="profile-link"]', timeout=15000)
            await CookieManager.save_cookies(context, self.SERVICE_NAME, account['login'])
            await self._send("✅ Вход по email выполнен успешно.")
            return True
        except Exception as e:
            logger.error(f"Ошибка входа Wallapop (email) для {account['login']}: {e}")
            await self._send("❌ Ошибка входа. Неверный логин/пароль или сработала защита.")
            return False

    async def login(self, page: Page, account: Dict, context: BrowserContext):
        # Только email-логин для мобильного обхода (Google на мобиле часто банит playwright)
        return await self._login_email(page, account, context)

    async def parser(self, criteria: Dict, chat_id: int):
        # criteria: dict (delivery, min_rating, pub_date, ...), chat_id для отправки результатов
        page, browser, context, proxy = await self._get_page(self.SERVICE_NAME)
        try:
            await page.goto(f"{self.BASE_URL}/search", wait_until="domcontentloaded")
            await self._delay()
            await self._handle_cookies(page, "#onetrust-accept-btn-handler")
            await self._mouse_surf(page)
            # Фильтры на Wallapop работают по параметрам URL, но мы собираем карточки из выдачи
            items = await page.query_selector_all('div[data-testid="search-result-item"] a[data-testid="item-card-link"]')
            results = []
            for item in items[:MAX_PARSER_RESULTS]:
                try:
                    href = await item.get_attribute('href')
                    card = await item.evaluate_handle('el => el.closest("div[data-testid=\'search-result-item\']")')
                    title_el = await card.query_selector('h2')
                    title = await title_el.inner_text() if title_el else "Без названия"
                    price_el = await card.query_selector('span[data-testid="item-card-price"]')
                    price = await price_el.inner_text() if price_el else "?"
                    location_el = await card.query_selector('span[data-testid="item-card-location"]')
                    location = await location_el.inner_text() if location_el else "?"
                    delivery_icon = await card.query_selector('svg[data-testid="shipping-icon"]')
                    delivery = "вкл." if delivery_icon else "нет"
                    adv_url = f"{self.BASE_URL}{href}"
                    await page.goto(adv_url, wait_until="domcontentloaded")
                    await self._delay()
                    await self._mouse_surf(page)
                    descr_el = await page.query_selector('div[data-testid="item-description"]')
                    descr = await descr_el.inner_text() if descr_el else "—"
                    seller = await page.query_selector('a[data-testid="seller-link"]')
                    seller_name = await seller.inner_text() if seller else "?"
                    rating = await page.query_selector('span[data-testid="profile-rating-value"]')
                    rating = await rating.inner_text() if rating else "0"
                    deals = await page.query_selector('span[data-testid="profile-total-sales"]')
                    deals = await deals.inner_text() if deals else "0"
                    buys = await page.query_selector('span[data-testid="profile-total-purchases"]')
                    buys = await buys.inner_text() if buys else "0"
                    adv_count = await page.query_selector('span[data-testid="profile-total-products"]')
                    adv_count = await adv_count.inner_text() if adv_count else "?"
                    pub_time = await page.query_selector('span[data-testid="publication-date"]')
                    pub_time_text = await pub_time.inner_text() if pub_time else "?"
                    # --- Фильтры ---
                    if criteria.get("delivery") and delivery != "вкл.": continue
                    if criteria.get("min_rating"):
                        try:
                            if float(rating) < float(criteria["min_rating"]): continue
                        except: pass
                    if criteria.get("min_seller_sales"):
                        if deals.isdigit() and int(deals) < int(criteria["min_seller_sales"]): continue
                    if criteria.get("min_seller_buys"):
                        if buys.isdigit() and int(buys) < int(criteria["min_seller_buys"]): continue
                    if criteria.get("min_seller_ads"):
                        if adv_count.isdigit() and int(adv_count) < int(criteria["min_seller_ads"]): continue
                    # --- Дата публикации фильтр ---
                    match_date = True
                    if criteria.get("pub_date"):
                        date_ok = False
                        text = pub_time_text.strip().lower()
                        now = datetime.now()
                        try:
                            if "минут" in text or "мин." in text or "час" in text or "день" in text or "дн." in text:
                                date = now
                            elif any(char.isdigit() for char in text):
                                for fmt in ["%d/%m/%Y", "%d/%m/%y"]:
                                    try:
                                        date = datetime.strptime(text, fmt)
                                        break
                                    except Exception: continue
                                else:
                                    date = now
                            else:
                                date = now
                            date_limit = datetime.strptime(criteria["pub_date"], "%Y-%m-%d")
                            if date >= date_limit:
                                date_ok = True
                        except Exception:
                            date_ok = False
                        match_date = date_ok
                    if not match_date: continue
                    txt = (
                        f"Объявление: {title}\n"
                        f"💸 Цена: {price}\n"
                        f"📍 Локация: {location}\n"
                        f"🚚 Доставка: {delivery}\n"
                        f"📝 Описание: {descr[:100]}{'...' if len(descr)>100 else ''}\n"
                        f"👤 Продавец: {seller_name}\n"
                        f"⭐️ Оценок: {rating}\n"
                        f"📥 Покупок: {buys}\n"
                        f"📤 Продаж: {deals}\n"
                        f"📑 Объявлений: {adv_count}\n"
                        f"📅 Опубликовано: {pub_time_text}\n"
                        f"🔗 Перейти к объявлению: {adv_url}"
                    )
                    results.append(txt)
                except Exception as e:
                    logger.error(f"Ошибка при парсинге Wallapop: {e}")
            await self._send(f"🔍 Найдено объявлений: {len(results)}")
            for group in range(0, len(results), 5):
                await self._send("\n\n".join(results[group:group+5]))
        except Exception as e:
            logger.error(f"Ошибка Wallapop parser: {e}")
            await self._send("❌ Ошибка парсинга Wallapop.")
            if proxy: ProxyManager.mark_bad(proxy)
        finally:
            if proxy: ProxyManager.mark_good(proxy)
            if 'browser' in locals(): await browser.close()

    async def sender(self, account_id: str, query: str, chat_id: int):
        account = DataManager.get_account_by_id(account_id)
        paste = DataManager.get_random_paste()
        if not paste:
            await self._send("❌ Нет ни одной пасты для рассылки. Добавьте пасту через меню управления.")
            return
        page, browser, context, proxy = await self._get_page(self.SERVICE_NAME, account["login"])
        try:
            if not await self.login(page, account, context): return
            await self._send(f"✉️ Запуск рассылки Wallapop для {account['login']}... Используем пасту: {paste['name']}")
            await page.goto(f"{self.BASE_URL}/search?keywords={query.replace(' ', '+')}", wait_until="domcontentloaded")
            await self._delay()
            await self._mouse_surf(page)
            items = await page.query_selector_all('div[data-testid="search-result-item"] a[data-testid="item-card-link"]')
            if not items: return await self._send("🤷‍♂️ Не найдено целей для рассылки.")
            target_href = await items[0].get_attribute('href')
            await page.goto(f"{self.BASE_URL}{target_href}", wait_until="domcontentloaded")
            await self._delay()
            await self._mouse_surf(page)
            await page.click('button[data-testid="chat-button"]')
            await self._delay()
            for msg in paste["messages"]:
                await page.fill('textarea', msg)
                await self._delay(0.8)
                await page.click('button[data-testid="send-message-button"]')
                await self._delay(1)
            await self._send("✅ Все сообщения из пасты отправлены.")
            await CookieManager.save_cookies(context, self.SERVICE_NAME, account['login'])
        except Exception as e:
            logger.error(f"Ошибка рассылки Wallapop: {e}")
            await self._send("❌ Критическая ошибка во время рассылки.")
            if proxy: ProxyManager.mark_bad(proxy)
        finally:
            if proxy: ProxyManager.mark_good(proxy)
            if 'browser' in locals(): await browser.close()

# =================== MILANUNCIOS SERVICE (мобильный, антибот) ===================

class MilanunciosService(BaseServiceModule):
    SERVICE_NAME = "milanuncios"
    BASE_URL = "https://www.milanuncios.com"

    async def _login_email(self, page: Page, account: Dict, context: BrowserContext):
        await self._send(f"Выполняю вход (email) в {account['login']}...")
        try:
            await page.goto(f"{self.BASE_URL}/login/", wait_until="networkidle")
            await self._handle_cookies(page, "#onetrust-accept-btn-handler")
            await self._mouse_surf(page)
            await page.fill('input[type="email"]', account['login'])
            await self._delay(0.9)
            await page.click('button:has-text("Continuar")')
            await self._delay(1)
            await page.fill('input[type="password"]', account['password'])
            await self._delay(0.8)
            await page.click('button:has-text("Iniciar sesión")')
            await self._delay(2)
            await self._mouse_surf(page)
            await page.wait_for_selector('div.ma-UserNav', timeout=15000)
            await CookieManager.save_cookies(context, self.SERVICE_NAME, account['login'])
            await self._send("✅ Вход выполнен успешно.")
            return True
        except Exception as e:
            logger.error(f"Ошибка входа Milanuncios (email): {e}")
            await self._send("❌ Ошибка входа.")
            return False

    async def login(self, page: Page, account: Dict, context: BrowserContext):
        return await self._login_email(page, account, context)

    async def parser(self, criteria: Dict, chat_id: int):
        page, browser, context, proxy = await self._get_page(self.SERVICE_NAME)
        try:
            await page.goto(f"{self.BASE_URL}/anuncios/", wait_until="domcontentloaded")
            await self._delay()
            await self._handle_cookies(page, "#onetrust-accept-btn-handler")
            await self._mouse_surf(page)
            items = await page.query_selector_all('article.ma-AdCard')
            results = []
            for item in items[:MAX_PARSER_RESULTS]:
                try:
                    title_el = await item.query_selector('a.ma-AdCard-titleLink')
                    title = await title_el.inner_text() if title_el else "Без названия"
                    adv_url = await title_el.get_attribute("href") if title_el else ""
                    price_el = await item.query_selector('span.ma-AdPrice-value')
                    price = await price_el.inner_text() if price_el else "?"
                    location_el = await item.query_selector('span.ma-AdCard-location')
                    location = await location_el.inner_text() if location_el else "?"
                    delivery_icon = await item.query_selector('svg[aria-label="Envío"]')
                    delivery = "вкл." if delivery_icon else "нет"
                    descr_el = await item.query_selector('div.ma-AdCard-description')
                    descr = await descr_el.inner_text() if descr_el else "—"
                    img = await item.query_selector('img')
                    img_url = await img.get_attribute("src") if img else "—"
                    seller_block = await item.query_selector('a.ma-AdCard-userLink')
                    seller_name = await seller_block.inner_text() if seller_block else "?"
                    seller_url = await seller_block.get_attribute("href") if seller_block else ""
                    # --- Переход к объявлению для доп.данных
                    if adv_url:
                        await page.goto(adv_url if adv_url.startswith("http") else self.BASE_URL + adv_url, wait_until="domcontentloaded")
                        await self._delay()
                        await self._mouse_surf(page)
                    rating = await page.query_selector('span[data-testid="user-rating"]')
                    rating = await rating.inner_text() if rating else "0"
                    deals = await page.query_selector('span[data-testid="user-sales"]')
                    deals = await deals.inner_text() if deals else "0"
                    buys = await page.query_selector('span[data-testid="user-purchases"]')
                    buys = await buys.inner_text() if buys else "0"
                    adv_count = await page.query_selector('span[data-testid="user-active-products"]')
                    adv_count = await adv_count.inner_text() if adv_count else "?"
                    pub_time = await page.query_selector('span[data-testid="ad-published"]')
                    pub_time_text = await pub_time.inner_text() if pub_time else "?"
                    # --- Фильтры
                    if criteria.get("delivery") and delivery != "вкл.": continue
                    if criteria.get("min_rating"):
                        try:
                            if float(rating) < float(criteria["min_rating"]): continue
                        except: pass
                    if criteria.get("min_seller_sales"):
                        if deals.isdigit() and int(deals) < int(criteria["min_seller_sales"]): continue
                    if criteria.get("min_seller_buys"):
                        if buys.isdigit() and int(buys) < int(criteria["min_seller_buys"]): continue
                    if criteria.get("min_seller_ads"):
                        if adv_count.isdigit() and int(adv_count) < int(criteria["min_seller_ads"]): continue
                    # --- Дата публикации фильтр ---
                    match_date = True
                    if criteria.get("pub_date"):
                        date_ok = False
                        text = pub_time_text.strip().lower()
                        now = datetime.now()
                        try:
                            if "hace" in text or "hora" in text or "minuto" in text or "día" in text:
                                date = now
                            elif any(char.isdigit() for char in text):
                                for fmt in ["%d/%m/%Y", "%d/%m/%y"]:
                                    try:
                                        date = datetime.strptime(text, fmt)
                                        break
                                    except Exception: continue
                                else:
                                    date = now
                            else:
                                date = now
                            date_limit = datetime.strptime(criteria["pub_date"], "%Y-%m-%d")
                            if date >= date_limit:
                                date_ok = True
                        except Exception:
                            date_ok = False
                        match_date = date_ok
                    if not match_date: continue
                    txt = (
                        f"Объявление: {title}\n"
                        f"💸 Цена: {price}\n"
                        f"📍 Локация: {location}\n"
                        f"🚚 Доставка: {delivery}\n"
                        f"📝 Описание: {descr[:100]}{'...' if len(descr)>100 else ''}\n"
                        f"👤 Продавец: {seller_name}\n"
                        f"⭐️ Оценок: {rating}\n"
                        f"📥 Покупок: {buys}\n"
                        f"📤 Продаж: {deals}\n"
                        f"📑 Объявлений: {adv_count}\n"
                        f"📅 Опубликовано: {pub_time_text}\n"
                        f"🔗 Перейти к объявлению: {adv_url}"
                    )
                    results.append(txt)
                except Exception as e:
                    logger.error(f"Ошибка при парсинге Milanuncios: {e}")
            await self._send(f"🔍 Найдено объявлений: {len(results)}")
            for group in range(0, len(results), 5):
                await self._send("\n\n".join(results[group:group+5]))
        except Exception as e:
            logger.error(f"Ошибка Milanuncios parser: {e}")
            await self._send("❌ Ошибка парсинга Milanuncios.")
            if proxy: ProxyManager.mark_bad(proxy)
        finally:
            if proxy: ProxyManager.mark_good(proxy)
            if 'browser' in locals(): await browser.close()

    async def sender(self, account_id: str, query: str, chat_id: int):
        account = DataManager.get_account_by_id(account_id)
        paste = DataManager.get_random_paste()
        if not paste:
            await self._send("❌ Нет ни одной пасты для рассылки. Добавьте пасту через меню управления.")
            return
        page, browser, context, proxy = await self._get_page(self.SERVICE_NAME, account["login"])
        try:
            if not await self.login(page, account, context): return
            await self._send(f"✉️ Запуск рассылки Milanuncios для {account['login']}... Используем пасту: {paste['name']}")
            await page.goto(f"{self.BASE_URL}/anuncios/?s={query.replace(' ', '+')}", wait_until="domcontentloaded")
            await self._delay()
            await self._mouse_surf(page)
            items = await page.query_selector_all('article.ma-AdCard a.ma-AdCard-titleLink')
            if not items: return await self._send("🤷‍♂️ Не найдено целей для рассылки.")
            target_href = await items[0].get_attribute('href')
            await page.goto(target_href if target_href.startswith("http") else self.BASE_URL + target_href, wait_until="domcontentloaded")
            await self._delay()
            await self._mouse_surf(page)
            await page.click('button:has-text("Contactar")')
            await self._delay()
            for msg in paste["messages"]:
                await page.fill('textarea[name="message"]', msg)
                await self._delay(0.8)
                await page.click('button:has-text("Enviar")')
                await self._delay(1)
            await self._send("✅ Все сообщения из пасты отправлены.")
            await CookieManager.save_cookies(context, self.SERVICE_NAME, account['login'])
        except Exception as e:
            logger.error(f"Ошибка рассылки Milanuncios: {e}")
            await self._send("❌ Критическая ошибка во время рассылки.")
            if proxy: ProxyManager.mark_bad(proxy)
        finally:
            if proxy: ProxyManager.mark_good(proxy)
            if 'browser' in locals(): await browser.close()
# -*- coding: utf-8 -*-
"""
main.py (Часть 3/8) — Telegram menu: аккаунты, прокси, пасты, парсер, рассылка, все шаги
"""

from telegram.constants import ParseMode

# =================== МЕНЮ И ОСНОВНЫЕ ОБРАБОТЧИКИ ===================

async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data['chat_id'] = update.effective_chat.id
    keyboard = [
        [InlineKeyboardButton("🔧 Управление", callback_data="menu_manage")],
        [InlineKeyboardButton("🚀 Wallapop парсер", callback_data="menu_wallapop_parser")],
        [InlineKeyboardButton("🔥 Milanuncios парсер", callback_data="menu_milanuncios_parser")],
        [InlineKeyboardButton("💬 Пасты", callback_data="menu_pastes")],
        [InlineKeyboardButton("✉️ Рассылка", callback_data="menu_sender")],
    ]
    await update.message.reply_text("👋 Боевая система активирована.\nВыберите действие:", reply_markup=InlineKeyboardMarkup(keyboard))
    return MENU

async def main_menu_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [
        [InlineKeyboardButton("🔧 Управление", callback_data="menu_manage")],
        [InlineKeyboardButton("🚀 Wallapop парсер", callback_data="menu_wallapop_parser")],
        [InlineKeyboardButton("🔥 Milanuncios парсер", callback_data="menu_milanuncios_parser")],
        [InlineKeyboardButton("💬 Пасты", callback_data="menu_pastes")],
        [InlineKeyboardButton("✉️ Рассылка", callback_data="menu_sender")],
    ]
    await update.callback_query.edit_message_text("Главное меню:", reply_markup=InlineKeyboardMarkup(keyboard))
    return MENU

# =================== ПРОКСИ ===================

async def menu_manage_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [
        [InlineKeyboardButton("➕ Прокси", callback_data="add_proxy")],
        [InlineKeyboardButton("🔗 Список прокси", callback_data="list_proxy")],
        [InlineKeyboardButton("❌ Удалить прокси", callback_data="del_proxy")],
        [InlineKeyboardButton("👤 Аккаунты", callback_data="menu_accounts")],
        [InlineKeyboardButton("⬅️ Назад", callback_data="main_menu")],
    ]
    await update.callback_query.edit_message_text("Управление прокси и аккаунтами:", reply_markup=InlineKeyboardMarkup(keyboard))
    return MANAGE

async def add_proxy_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.callback_query.edit_message_text("Введите прокси (например, socks5://user:pass@host:port):")
    return ADD_PROXY_INPUT

async def add_proxy_input(update: Update, context: ContextTypes.DEFAULT_TYPE):
    proxy = update.message.text.strip()
    ok = DataManager.add_proxy(proxy)
    if ok:
        await update.message.reply_text("Прокси добавлен!", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("⬅️ Назад", callback_data="main_menu")]]))
    else:
        await update.message.reply_text("Такой прокси уже есть.", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("⬅️ Назад", callback_data="main_menu")]]))
    return MENU

async def list_proxy(update: Update, context: ContextTypes.DEFAULT_TYPE):
    proxies = DataManager.proxies()
    if not proxies:
        await update.callback_query.edit_message_text("Нет прокси.")
    else:
        txt = "Список прокси:\n\n"
        for i, p in enumerate(proxies):
            txt += f"{i+1}. `{p}`\n"
        await update.callback_query.edit_message_text(txt, parse_mode=ParseMode.MARKDOWN)
    return MANAGE

async def del_proxy_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    proxies = DataManager.proxies()
    if not proxies:
        await update.callback_query.edit_message_text("Нет прокси для удаления.")
        return MANAGE
    keyboard = [[InlineKeyboardButton(f"{p[:40]}...", callback_data=f"delproxy_{i}")] for i, p in enumerate(proxies)]
    keyboard.append([InlineKeyboardButton("⬅️ Назад", callback_data="main_menu")])
    await update.callback_query.edit_message_text("Выберите прокси для удаления:", reply_markup=InlineKeyboardMarkup(keyboard))
    return DEL_PROXY_CHOOSE

async def del_proxy_choose(update: Update, context: ContextTypes.DEFAULT_TYPE):
    idx = int(update.callback_query.data.replace("delproxy_", ""))
    proxies = DataManager.proxies()
    if idx >= len(proxies):
        await update.callback_query.edit_message_text("Ошибка! Такой прокси не найден.")
        return MANAGE
    DataManager.delete("proxies", idx)
    await update.callback_query.edit_message_text("Прокси удалён.")
    return MANAGE

# =================== АККАУНТЫ ===================

async def menu_accounts_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [
        [InlineKeyboardButton("➕ Добавить аккаунт", callback_data="add_account")],
        [InlineKeyboardButton("👁 Список аккаунтов", callback_data="list_accounts")],
        [InlineKeyboardButton("❌ Удалить аккаунт", callback_data="del_account")],
        [InlineKeyboardButton("⬅️ Назад", callback_data="main_menu")],
    ]
    await update.callback_query.edit_message_text("Управление аккаунтами:", reply_markup=InlineKeyboardMarkup(keyboard))
    return MANAGE

async def add_account_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [
        [InlineKeyboardButton("Wallapop", callback_data="accserv_wallapop")],
        [InlineKeyboardButton("Milanuncios", callback_data="accserv_milanuncios")],
        [InlineKeyboardButton("⬅️ Назад", callback_data="main_menu")],
    ]
    await update.callback_query.edit_message_text("Выберите сервис для аккаунта:", reply_markup=InlineKeyboardMarkup(keyboard))
    return ADD_ACCOUNT_SERVICE

async def add_account_service(update: Update, context: ContextTypes.DEFAULT_TYPE):
    service = update.callback_query.data.replace("accserv_", "")
    context.user_data["new_acc_service"] = service
    await update.callback_query.edit_message_text("Введите логин (email):")
    return ADD_ACCOUNT_LOGIN

async def add_account_login(update: Update, context: ContextTypes.DEFAULT_TYPE):
    login = update.message.text.strip()
    context.user_data["new_acc_login"] = login
    await update.message.reply_text("Введите пароль:")
    return ADD_ACCOUNT_PASS

async def add_account_pass(update: Update, context: ContextTypes.DEFAULT_TYPE):
    password = update.message.text.strip()
    context.user_data["new_acc_password"] = password
    acc = {
        "id": str(uuid.uuid4()),
        "service": context.user_data["new_acc_service"],
        "login": context.user_data["new_acc_login"],
        "password": password,
    }
    ok = DataManager.add_account(acc)
    if ok:
        await update.message.reply_text("Аккаунт добавлен!", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("⬅️ Назад", callback_data="main_menu")]]))
    else:
        await update.message.reply_text("Аккаунт уже есть.", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("⬅️ Назад", callback_data="main_menu")]]))
    return MANAGE

async def list_accounts(update: Update, context: ContextTypes.DEFAULT_TYPE):
    accs = DataManager.accounts()
    if not accs:
        await update.callback_query.edit_message_text("Нет аккаунтов.")
    else:
        txt = "Список аккаунтов:\n\n"
        for i, a in enumerate(accs):
            txt += f"{i+1}. [{a['service']}] {a['login']}\n"
        await update.callback_query.edit_message_text(txt)
    return MANAGE

async def del_account_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    accs = DataManager.accounts()
    if not accs:
        await update.callback_query.edit_message_text("Нет аккаунтов для удаления.")
        return MANAGE
    keyboard = [[InlineKeyboardButton(f"[{a['service']}] {a['login']}", callback_data=f"delacc_{a['id']}")] for a in accs]
    keyboard.append([InlineKeyboardButton("⬅️ Назад", callback_data="main_menu")])
    await update.callback_query.edit_message_text("Выберите аккаунт для удаления:", reply_markup=InlineKeyboardMarkup(keyboard))
    return DEL_ACCOUNT_CHOOSE

async def del_account_choose(update: Update, context: ContextTypes.DEFAULT_TYPE):
    acc_id = update.callback_query.data.replace("delacc_", "")
    ok = DataManager.delete_account(acc_id)
    if ok:
        await update.callback_query.edit_message_text("Аккаунт удалён.")
    else:
        await update.callback_query.edit_message_text("Ошибка! Такой аккаунт не найден.")
    return MANAGE

# =================== ПАСТЫ ===================

async def menu_pastes_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [
        [InlineKeyboardButton("➕ Добавить пасту", callback_data="add_paste")],
        [InlineKeyboardButton("📋 Список паст", callback_data="list_pastes")],
        [InlineKeyboardButton("❌ Удалить пасту", callback_data="del_paste")],
        [InlineKeyboardButton("⬅️ Назад", callback_data="main_menu")],
    ]
    await update.callback_query.edit_message_text("Пасты — управление наборами сообщений для рассылки.", reply_markup=InlineKeyboardMarkup(keyboard))
    return MANAGE

async def add_paste_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.callback_query.edit_message_text("Введите имя новой пасты:")
    return ADD_PASTE

async def add_paste_name(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["new_paste_name"] = update.message.text.strip()
    await update.message.reply_text("Вводите сообщения пасты по одному. Когда закончите — напишите /done")
    context.user_data["new_paste_msgs"] = []
    return PASTE_ADD_TEXT

async def add_paste_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    msg = update.message.text.strip()
    context.user_data["new_paste_msgs"].append(msg)
    await update.message.reply_text("Добавлено! Следующее сообщение или /done")
    return PASTE_ADD_TEXT

async def add_paste_done(update: Update, context: ContextTypes.DEFAULT_TYPE):
    name = context.user_data.get("new_paste_name")
    msgs = context.user_data.get("new_paste_msgs", [])
    if not msgs:
        await update.message.reply_text("Паста не может быть пустой.")
        return PASTE_ADD_TEXT
    ok = DataManager.add_paste(name, msgs)
    if ok:
        await update.message.reply_text(f"Паста '{name}' сохранена! ({len(msgs)} сообщений)")
    else:
        await update.message.reply_text("Паста с таким именем уже есть.")
    return MANAGE

async def list_pastes(update: Update, context: ContextTypes.DEFAULT_TYPE):
    pastes = DataManager.pastes()
    if not pastes:
        await update.callback_query.edit_message_text("Нет ни одной пасты.")
    else:
        txt = "Список паст:\n\n"
        for p in pastes:
            txt += f"• {p['name']} ({len(p['messages'])} сообщений)\n"
        await update.callback_query.edit_message_text(txt)
    return MANAGE

async def del_paste_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    names = DataManager.get_paste_names()
    if not names:
        await update.callback_query.edit_message_text("Нет паст для удаления.")
        return MANAGE
    keyboard = [[InlineKeyboardButton(n, callback_data=f"delpaste_{n}")] for n in names]
    keyboard.append([InlineKeyboardButton("⬅️ Назад", callback_data="main_menu")])
    await update.callback_query.edit_message_text("Выберите пасту для удаления:", reply_markup=InlineKeyboardMarkup(keyboard))
    return DEL_PASTE_CHOOSE

async def del_paste_choose(update: Update, context: ContextTypes.DEFAULT_TYPE):
    name = update.callback_query.data.replace("delpaste_", "")
    ok = DataManager.delete_paste(name)
    if ok:
        await update.callback_query.edit_message_text(f"Паста '{name}' удалена.")
    else:
        await update.callback_query.edit_message_text(f"Паста '{name}' не найдена.")
    return MANAGE

# =================== ПАРСЕР ===================

async def parser_service_select(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [
        [InlineKeyboardButton("Wallapop", callback_data="parser_service_wallapop")],
        [InlineKeyboardButton("Milanuncios", callback_data="parser_service_milanuncios")],
        [InlineKeyboardButton("⬅️ Назад", callback_data="main_menu")],
    ]
    if update.callback_query:
        await update.callback_query.edit_message_text("Выберите площадку для парсинга:", reply_markup=InlineKeyboardMarkup(keyboard))
    else:
        await update.message.reply_text("Выберите площадку для парсинга:", reply_markup=InlineKeyboardMarkup(keyboard))
    return PARSER_SERVICE

async def parser_criteria_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["parser_criteria"] = {}
    keyboard = [
        [InlineKeyboardButton("Только с доставкой", callback_data="parser_delivery")],
        [InlineKeyboardButton("Мин. рейтинг продавца", callback_data="parser_min_rating")],
        [InlineKeyboardButton("Мин. активных объявлений", callback_data="parser_min_seller_ads")],
        [InlineKeyboardButton("Мин. продаж", callback_data="parser_min_seller_sales")],
        [InlineKeyboardButton("Мин. покупок", callback_data="parser_min_seller_buys")],
        [InlineKeyboardButton("Дата публикации", callback_data="parser_pub_date")],
        [InlineKeyboardButton("Старт парсинга", callback_data="parser_run")],
        [InlineKeyboardButton("⬅️ Назад", callback_data="main_menu")],
    ]
    await update.callback_query.edit_message_text("Выберите критерии парсера (или сразу 'Старт парсинга'):", reply_markup=InlineKeyboardMarkup(keyboard))
    return PARSER_CRITERIA

async def parser_criteria_buttons_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    d = context.user_data.get('parser_criteria', {})
    if query.data == "parser_delivery":
        d["delivery"] = True
    elif query.data == "parser_min_rating":
        await query.edit_message_text("Введите минимальный рейтинг продавца (например, 2):")
        context.user_data['parser_criteria_next'] = "min_rating"
        return PARSER_CRITERIA_INPUT
    elif query.data == "parser_min_seller_ads":
        await query.edit_message_text("Введите мин. число активных объявлений у продавца:")
        context.user_data['parser_criteria_next'] = "min_seller_ads"
        return PARSER_CRITERIA_INPUT
    elif query.data == "parser_min_seller_sales":
        await query.edit_message_text("Введите мин. число продаж продавца:")
        context.user_data['parser_criteria_next'] = "min_seller_sales"
        return PARSER_CRITERIA_INPUT
    elif query.data == "parser_min_seller_buys":
        await query.edit_message_text("Введите мин. число покупок продавца:")
        context.user_data['parser_criteria_next'] = "min_seller_buys"
        return PARSER_CRITERIA_INPUT
    elif query.data == "parser_pub_date":
        await query.edit_message_text("Введите дату публикации не ранее (ГГГГ-ММ-ДД):")
        context.user_data['parser_criteria_next'] = "pub_date"
        return PARSER_DATE
    elif query.data == "parser_run":
        return await parser_run(update, context)
    elif query.data == "main_menu":
        await main_menu_handler(update, context)
        return MENU
    context.user_data['parser_criteria'] = d
    return await parser_criteria_start(update, context)

async def parser_criteria_input_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    key = context.user_data.get('parser_criteria_next')
    val = update.message.text.strip()
    if key == "pub_date":
        try:
            datetime.strptime(val, "%Y-%m-%d")
        except Exception:
            await update.message.reply_text("Введите дату в формате: ГГГГ-ММ-ДД")
            return PARSER_DATE
    else:
        try:
            val = float(val)
        except ValueError:
            await update.message.reply_text("Введите числовое значение.")
            return PARSER_CRITERIA_INPUT
    context.user_data.setdefault('parser_criteria', {})[key] = val
    context.user_data['parser_criteria_next'] = None
    return await parser_criteria_start(update, context)

# Замените всю эту функцию
async def parser_run(update: Update, context: ContextTypes.DEFAULT_TYPE):
    criteria = context.user_data.get("parser_criteria", {})
    service = context.user_data.get("parser_service", "wallapop")
    chat_id = context.user_data.get("chat_id")

    if service == "wallapop":
        # Создаем корутину, но не запускаем ее через await
        task_coro = WallapopService(context, "parser").parser(criteria, chat_id)
    else:
        # Создаем корутину, но не запускаем ее через await
        task_coro = MilanunciosService(context, "parser").parser(criteria, chat_id)
    
    # Запускаем корутину в фоновом режиме
    run_task_in_background(task_coro)

    await update.callback_query.edit_message_text(f"✅ Парсер для {service.capitalize()} запущен в фоновом режиме!")
    return MENU

# =================== РАССЫЛКА ===================

async def sender_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [
        [InlineKeyboardButton("Wallapop", callback_data="sender_wallapop")],
        [InlineKeyboardButton("Milanuncios", callback_data="sender_milanuncios")],
        [InlineKeyboardButton("⬅️ Назад", callback_data="main_menu")],
    ]
    if update.callback_query:
        await update.callback_query.edit_message_text("Выберите площадку для рассылки:", reply_markup=InlineKeyboardMarkup(keyboard))
    else:
        await update.message.reply_text("Выберите площадку для рассылки:", reply_markup=InlineKeyboardMarkup(keyboard))
    return SENDER_CHOOSE_SERVICE

async def sender_choose_service(update: Update, context: ContextTypes.DEFAULT_TYPE):
    service = update.callback_query.data.replace("sender_", "")
    context.user_data["sender_service"] = service
    accs = [a for a in DataManager.accounts() if a["service"] == service]
    if not accs:
        await update.callback_query.edit_message_text("Нет аккаунтов для выбранной площадки.")
        return MENU
    keyboard = [[InlineKeyboardButton(a["login"], callback_data=f"sender_acc_{a['id']}")] for a in accs]
    await update.callback_query.edit_message_text("Выберите аккаунт для рассылки:", reply_markup=InlineKeyboardMarkup(keyboard))
    return SENDER_CHOOSE_ACC

async def sender_choose_acc(update: Update, context: ContextTypes.DEFAULT_TYPE):
    acc_id = update.callback_query.data.replace("sender_acc_", "")
    context.user_data["sender_acc"] = acc_id
    pastes = DataManager.get_paste_names()
    if not pastes:
        await update.callback_query.edit_message_text("Нет паст для рассылки.")
        return MENU
    keyboard = [[InlineKeyboardButton(n, callback_data=f"sender_paste_{n}")] for n in pastes]
    await update.callback_query.edit_message_text("Выберите пасту:", reply_markup=InlineKeyboardMarkup(keyboard))
    return SENDER_CHOOSE_PASTE

async def sender_choose_paste(update: Update, context: ContextTypes.DEFAULT_TYPE):
    paste_name = update.callback_query.data.replace("sender_paste_", "")
    context.user_data["sender_paste"] = paste_name
    await update.callback_query.edit_message_text("Введите ключевое слово для поиска цели рассылки:")
    return SENDER_QUERY

# Замените всю эту функцию
async def sender_query_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.message.text.strip()
    context.user_data["sender_query"] = query
    service = context.user_data.get("sender_service", "wallapop")
    acc_id = context.user_data.get("sender_acc")
    chat_id = context.user_data.get("chat_id")

    if service == "wallapop":
        # Создаем корутину
        task_coro = WallapopService(context, "sender").sender(acc_id, query, chat_id)
    else:
        # Создаем корутину
        task_coro = MilanunciosService(context, "sender").sender(acc_id, query, chat_id)
    
    # Запускаем корутину в фоновом режиме
    run_task_in_background(task_coro)

    await update.message.reply_text("✅ Рассылка запущена в фоновом режиме!", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("⬅️ Назад", callback_data="main_menu")]]))
    return MENU

# =================== ПОДКЛЮЧЕНИЕ ConversationHandler ===================

def build_conversation_handler():
    return ConversationHandler(
        entry_points=[CommandHandler('start', start_command)],
        states={
            MENU: [
                CallbackQueryHandler(main_menu_handler, pattern='^main_menu$'),
                CallbackQueryHandler(menu_manage_handler, pattern='^menu_manage$'),
                CallbackQueryHandler(menu_pastes_handler, pattern='^menu_pastes$'),
                CallbackQueryHandler(menu_accounts_handler, pattern='^menu_accounts$'),
                CallbackQueryHandler(parser_service_select, pattern='^menu_wallapop_parser$|^menu_milanuncios_parser$'),
                CallbackQueryHandler(sender_menu, pattern='^menu_sender$'),
            ],
            MANAGE: [
                CallbackQueryHandler(menu_manage_handler, pattern='^menu_manage$'),
                CallbackQueryHandler(add_proxy_start, pattern='^add_proxy$'),
                CallbackQueryHandler(list_proxy, pattern='^list_proxy$'),
                CallbackQueryHandler(del_proxy_start, pattern='^del_proxy$'),
                CallbackQueryHandler(menu_accounts_handler, pattern='^menu_accounts$'),
                CallbackQueryHandler(add_account_start, pattern='^add_account$'),
                CallbackQueryHandler(list_accounts, pattern='^list_accounts$'),
                CallbackQueryHandler(del_account_start, pattern='^del_account$'),
                CallbackQueryHandler(menu_pastes_handler, pattern='^menu_pastes$'),
                CallbackQueryHandler(main_menu_handler, pattern='^main_menu$'),
                CallbackQueryHandler(del_proxy_choose, pattern='^delproxy_'),
                CallbackQueryHandler(del_account_choose, pattern='^delacc_'),
            ],
            ADD_PROXY_INPUT: [MessageHandler(filters.TEXT & ~filters.COMMAND, add_proxy_input)],
            DEL_PROXY_CHOOSE: [CallbackQueryHandler(del_proxy_choose, pattern='^delproxy_')],
            ADD_ACCOUNT_SERVICE: [CallbackQueryHandler(add_account_service, pattern='^accserv_')],
            ADD_ACCOUNT_LOGIN: [MessageHandler(filters.TEXT & ~filters.COMMAND, add_account_login)],
            ADD_ACCOUNT_PASS: [MessageHandler(filters.TEXT & ~filters.COMMAND, add_account_pass)],
            DEL_ACCOUNT_CHOOSE: [CallbackQueryHandler(del_account_choose, pattern='^delacc_')],
            ADD_PASTE: [MessageHandler(filters.TEXT & ~filters.COMMAND, add_paste_name)],
            PASTE_ADD_TEXT: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, add_paste_text),
                CommandHandler('done', add_paste_done)
            ],
            DEL_PASTE_CHOOSE: [CallbackQueryHandler(del_paste_choose, pattern='^delpaste_')],
            PARSER_SERVICE: [
                CallbackQueryHandler(parser_criteria_start, pattern='^parser_service_wallapop$'),
                CallbackQueryHandler(parser_criteria_start, pattern='^parser_service_milanuncios$'),
            ],
            PARSER_CRITERIA: [
                CallbackQueryHandler(parser_criteria_buttons_handler, pattern='^parser_'),
            ],
            PARSER_CRITERIA_INPUT: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, parser_criteria_input_handler)
            ],
            PARSER_DATE: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, parser_criteria_input_handler)
            ],
            SENDER_CHOOSE_SERVICE: [
                CallbackQueryHandler(sender_choose_service, pattern='^sender_'),
            ],
            SENDER_CHOOSE_ACC: [
                CallbackQueryHandler(sender_choose_acc, pattern='^sender_acc_'),
            ],
            SENDER_CHOOSE_PASTE: [
                CallbackQueryHandler(sender_choose_paste, pattern='^sender_paste_'),
            ],
            SENDER_QUERY: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, sender_query_handler)
            ],
        },
        fallbacks=[CommandHandler('start', start_command)],
        per_user=True, per_chat=True,
    )
# -*- coding: utf-8 -*-
"""
main.py (Часть 4/8) — запуск main, логирование, сборка и запуск Telegram-бота
"""

def main():
    # Логирование
    log_dir = os.path.dirname(CONFIG["LOG_FILE"])
    if log_dir and not os.path.exists(log_dir):
        os.makedirs(log_dir)
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s',
        handlers=[logging.FileHandler(CONFIG["LOG_FILE"], encoding='utf-8'), logging.StreamHandler()]
    )

    # Telegram Application
    app = Application.builder().token(CONFIG["TELEGRAM_BOT_TOKEN"]).build()
    app.add_handler(build_conversation_handler())

    logger.info("==============================================")
    logger.info("   БОЕВАЯ СИСТЕМА УСПЕШНО ЗАПУЩЕНА И ГОТОВА   ")
    logger.info("==============================================")
    app.run_polling()

if __name__ == "__main__":
    main()
# -*- coding: utf-8 -*-
"""
main.py (Часть 5/8) — Экспорт/импорт данных, очистка, продвинутый fallback
"""

from telegram.error import BadRequest

# Экспорт данных (json)
async def export_data(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        with open(CONFIG["DATA_FILE"], "rb") as f:
            await update.message.reply_document(document=InputFile(f, filename="bot_data_export.json"), caption="Экспорт данных бота.")
    except Exception as e:
        await update.message.reply_text(f"Ошибка экспорта: {e}")

# Импорт данных (json)
async def import_data(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message.document:
        await update.message.reply_text("Пришлите файл .json для импорта.")
        return
    file = await update.message.document.get_file()
    data_bytes = await file.download_as_bytearray()
    try:
        data = json.loads(data_bytes.decode("utf-8"))
        DataManager._save(data)
        await update.message.reply_text("✅ Данные успешно импортированы!")
    except Exception as e:
        await update.message.reply_text(f"Ошибка импорта: {e}")

# Очистка данных (сброс всего)
async def clear_data(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        DataManager._save({"proxies": [], "accounts": [], "pastes": []})
        await update.message.reply_text("🧹 Все данные сброшены.")
    except Exception as e:
        await update.message.reply_text(f"Ошибка очистки: {e}")

# Расширенные fallbacks и глобальный обработчик ошибок
async def global_error_handler(update, context):
    logger.error(f"Ошибка Telegram: {context.error}")
    try:
        if update and hasattr(update, "message") and update.message:
            await update.message.reply_text("Произошла неожиданная ошибка. Попробуйте ещё раз или перезапустите бот (/start).")
        elif update and hasattr(update, "callback_query") and update.callback_query:
            await update.callback_query.answer()
            await update.callback_query.edit_message_text("Произошла неожиданная ошибка. Попробуйте ещё раз или перезапустите бот (/start).")
    except BadRequest:
        pass

# Расширяем main (вставить ДО app.run_polling())
def add_util_handlers(app):
    # Команды: /export, /import, /clear
    app.add_handler(CommandHandler("export", export_data))
    app.add_handler(CommandHandler("clear", clear_data))
    app.add_handler(MessageHandler(filters.Document.ALL & filters.CaptionRegex("^/import$"), import_data))

def add_error_handler(app):
    app.add_error_handler(global_error_handler)
# -*- coding: utf-8 -*-
"""
main.py (Часть 6/8) — расширенные проверки, авто-бан прокси, авто-очистка cookies, утилиты
"""

import shutil

# Безопасное добавление аккаунта (без дублей)
def safe_add_account(acc: dict) -> bool:
    # Вернуть False если такой логин+сервис уже есть
    accs = DataManager.accounts()
    if any(a["login"] == acc["login"] and a["service"] == acc["service"] for a in accs):
        return False
    return DataManager.add_account(acc)

# Очистка cookies при удалении аккаунта
def cleanup_account_cookies(acc_id: str):
    acc = DataManager.get_account_by_id(acc_id)
    if not acc: return
    path = CookieManager.get_cookie_path(acc["service"], acc["login"])
    if os.path.exists(path):
        os.remove(path)

# Модификация удаления аккаунта для очистки cookies
def patched_delete_account(acc_id: str) -> bool:
    res = DataManager.delete_account(acc_id)
    cleanup_account_cookies(acc_id)
    return res

# Патчинг DataManager.delete_account на новую версию
DataManager.delete_account = patched_delete_account

# При удалении всех данных — очистить папку cookies
def clear_all_data_and_cookies():
    DataManager._save({"proxies": [], "accounts": [], "pastes": []})
    if os.path.exists(CONFIG["COOKIES_DIR"]):
        shutil.rmtree(CONFIG["COOKIES_DIR"], ignore_errors=True)

# Переопределение команды очистки данных
async def clear_data(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        clear_all_data_and_cookies()
        await update.message.reply_text("🧹 Все данные и cookies полностью сброшены.")
    except Exception as e:
        await update.message.reply_text(f"Ошибка очистки: {e}")

# Доработка ProxyManager: авто-банить “битый” прокси при ошибке playwright
async def handle_browser_error(proxy, exc, context):
    logger.error(f"Proxy {proxy} забанен из-за ошибки: {exc}")
    ProxyManager.mark_bad(proxy)
    await context.bot.send_message(chat_id=context.user_data.get('chat_id'), text=f"Прокси {proxy} временно убран из ротации из-за ошибки соединения.")

# В сервисных классах WallapopService/MilanunciosService — внутри except: добавь:
#   if proxy: await handle_browser_error(proxy, e, self.context)
# Это уже реализовано через ProxyManager.mark_bad(proxy), но если хочешь уведомлять в чат — используй эту функцию.

# Утилита для проверки наличия дубликатов паст, прокси и аккаунтов
def check_duplicates():
    d = DataManager._load()
    for key in ["accounts", "proxies", "pastes"]:
        items = d.get(key, [])
        if len(items) != len(set(map(str, items))):
            logger.warning(f"Дубли в {key}!")
    logger.info("Проверка на дубли завершена.")

# (Можно вызывать check_duplicates() при старте main, если нужно)
# -*- coding: utf-8 -*-
"""
main.py (Часть 7/8) — production-утилиты, авто-ротация proxy/cookies, dev-команды, структура, деплой
"""

# ========== Production-режим: авто-ротация proxy+cookies для массовых рассылок ==========

async def mass_sender(service_name, query, chat_id, context, limit_per_account=5):
    """Отправляет массовую рассылку через ВСЕ аккаунты выбранного сервиса, с ротацией прокси/cookies"""
    accs = [a for a in DataManager.accounts() if a["service"] == service_name]
    paste = DataManager.get_random_paste()
    if not accs or not paste:
        await context.bot.send_message(chat_id=chat_id, text="⚠️ Нет аккаунтов или пасты для массовой рассылки.")
        return
    for acc in accs:
        try:
            if service_name == "wallapop":
                await WallapopService(context, "mass_sender").sender(acc["id"], query, chat_id)
            else:
                await MilanunciosService(context, "mass_sender").sender(acc["id"], query, chat_id)
            await asyncio.sleep(random.uniform(13, 25))  # антипалево!
        except Exception as e:
            logger.error(f"Ошибка массовой рассылки для {acc['login']}: {e}")
            continue

# ========== Dev-команды: прямой экспорт, ручная проверка cookies/proxy, быстрая отладка ==========

async def dev_show_cookies(update: Update, context: ContextTypes.DEFAULT_TYPE):
    accs = DataManager.accounts()
    msg = ""
    for acc in accs:
        path = CookieManager.get_cookie_path(acc["service"], acc["login"])
        msg += f"{acc['login']} ({acc['service']}): {'есть' if os.path.exists(path) else 'нет'}\n"
    await update.message.reply_text(msg or "Нет аккаунтов/cookies.")

async def dev_proxy_status(update: Update, context: ContextTypes.DEFAULT_TYPE):
    proxies = DataManager.proxies()
    bad = getattr(ProxyManager, "_bad_proxies", set())
    txt = ""
    for p in proxies:
        txt += f"{p} — {'BAD' if p in bad else 'OK'}\n"
    await update.message.reply_text(txt or "Нет прокси.")

# ========== Рекомендации по деплою (для тебя, не для кода) ==========

"""
Рекомендуется запускать данный бот:
- На выделенном сервере под Linux (Ubuntu 22.04+)
- Python 3.11+, playwright>=1.43.0, playwright-stealth, python-telegram-bot>=20
- Виртуальное окружение venv
- Установить playwright браузеры: python -m playwright install
- Для стабильной работы мобильных сессий и прокси: не менее 2Gb RAM/ядер, стабильный интернет
- Для массовых рассылок — использовать не более 1 аккаунта на 1 IP/proxy одновременно
- Храните DATA_FILE и COOKIES_DIR в защищённых папках, делайте backup
- Для production — переведите HEADLESS_MODE в True, но для отладки удобно False

Структура main.py после склейки частей:
- Импорты, константы, DataManager, ProxyManager, CookieManager
- BaseServiceModule (mobile anti-bot)
- WallapopService, MilanunciosService (актуальные селекторы 2025, mouse/touch, cookies)
- Telegram menu: прокси, аккаунты, пасты, парсер, рассылка, ConversationHandler
- Production-утилиты: экспорт/импорт, очистка, error-handler
- Расширенные проверки, авто-бан прокси, авто-очистка cookies
- Mass sender/routing, dev-команды
- main(): сборка, запуск

"""

# ========== Добавление dev-команд в main ==========

def add_dev_handlers(app):
    app.add_handler(CommandHandler("dev_cookies", dev_show_cookies))
    app.add_handler(CommandHandler("dev_proxy", dev_proxy_status))
# -*- coding: utf-8 -*-
"""
main.py (Часть 8/8) — auto-setup playwright, оглавление функций, финальные best practice
"""

import sys
import subprocess

# ====== Auto-setup playwright browsers (автоматическая установка браузеров при первом запуске) ======

def playwright_auto_install():
    try:
        import playwright
        from playwright.sync_api import sync_playwright
        # Проверяем, установлен ли chromium
        from pathlib import Path
        browsers_dir = Path.home() / ".cache/ms-playwright"
        chromium_dir = browsers_dir / "chromium"
        if not chromium_dir.exists():
            print("Playwright browsers not installed. Installing...")
            subprocess.run([sys.executable, "-m", "playwright", "install", "chromium"], check=True)
    except Exception as e:
        print(f"Ошибка playwright auto-install: {e}")
        subprocess.run([sys.executable, "-m", "playwright", "install", "chromium"], check=True)

# ====== Функция-оглавление для быстрого поиска ======
"""
Файл main.py (итог) включает:
- Импорты, константы, DataManager, ProxyManager, CookieManager
- BaseServiceModule (mobile anti-bot)
- WallapopService, MilanunciosService (антифрод, mouse/touch, cookies, актуальные селекторы 2025)
- Telegram menu: прокси, аккаунты, пасты, парсер, рассылка, ConversationHandler
- Production-утилиты: экспорт/импорт, очистка, error-handler, mass sender
- Расширенные проверки, авто-бан прокси, авто-очистка cookies, dev-команды
- main(): запуск, логирование, playwright_auto_install()
"""

# ====== Финальные best practice и напоминания ======
"""
- Для массовой рассылки рекомендуется не превышать 1 аккаунт на 1 прокси/IP одновременно.
- Храните DATA_FILE и COOKIES_DIR в приватном месте, делайте резервные копии.
- Используйте HEADLESS_MODE=True для production, но отлаживайте на False.
- Регулярно обновляйте Playwright и playwright-stealth.
- Обновляйте селекторы раз в несколько месяцев (или чаще, если площадки меняют верстку).
- Используйте Python 3.11+ для стабильной работы!
"""

# ====== Исправленный main() с auto-setup, handlers, dev, утилиты ======
def main():
    playwright_auto_install()

    # Логирование
    log_dir = os.path.dirname(CONFIG["LOG_FILE"])
    if log_dir and not os.path.exists(log_dir):
        os.makedirs(log_dir)
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s',
        handlers=[logging.FileHandler(CONFIG["LOG_FILE"], encoding='utf-8'), logging.StreamHandler()]
    )

    # Telegram Application
    app = Application.builder().token(CONFIG["TELEGRAM_BOT_TOKEN"]).build()
    app.add_handler(build_conversation_handler())
    add_util_handlers(app)
    add_error_handler(app)
    add_dev_handlers(app)

    logger.info("==============================================")
    logger.info("   БОЕВАЯ СИСТЕМА УСПЕШНО ЗАПУЩЕНА И ГОТОВА   ")
    logger.info("==============================================")
    app.run_polling()

if __name__ == "__main__":
    main()
