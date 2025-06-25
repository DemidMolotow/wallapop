import asyncio
from playwright.async_api import async_playwright
import logging
import random
from typing import List, Dict, Any, Optional

logger = logging.getLogger(__name__)

class WarmupModule:
    def __init__(self, bot, admin_chat_id):
        """
        Инициализирует модуль прогрева аккаунта.
        
        :param bot: Объект бота для отправки уведомлений
        :param admin_chat_id: ID чата для логирования
        """
        self.bot = bot
        self.admin_chat_id = admin_chat_id
        
    async def warmup_account_async(self, use_headless: bool = True) -> str:
        """
        Асинхронная функция для прогрева аккаунта.
        
        :param use_headless: Использовать headless режим браузера
        :return: Результат прогрева в виде строки
        """
        async def log_message(message: str):
            logger.info(message)
            try:
                await self.bot.send_message(self.admin_chat_id, message)
            except Exception as e:
                logger.error(f"Ошибка отправки сообщения в админ-чат: {e}")
        
        try:
            await log_message("Начинаю прогрев аккаунта...")
            
            async with async_playwright() as p:
                # Запуск браузера
                browser = await p.chromium.launch(headless=use_headless)
                context = await browser.new_context(
                    user_agent='Mozilla/5.0 (Linux; Android 10; Mobile; rv:89.0) Gecko/89.0 Firefox/89.0',
                    viewport={'width': 360, 'height': 640}
                )
                
                # Добавление трекера активности для имитации человеческого поведения
                await context.route('**/*', lambda route: route.continue_())
                
                page = await context.new_page()
                
                # Выполнение различных действий для прогрева
                await log_message("1. Открываю главную страницу...")
                await page.goto('https://www.milanuncios.com')
                await self._random_delay(2, 4)
                
                # Прокрутка страницы
                await log_message("2. Прокручиваю страницу...")
                await self._random_scroll(page)
                
                # Переход в случайные категории
                await log_message("3. Просматриваю категории...")
                await self._browse_categories(page)
                
                # Поиск случайных товаров
                await log_message("4. Выполняю поиск...")
                await self._perform_search(page)
                
                # Просмотр деталей объявлений
                await log_message("5. Просматриваю объявления...")
                await self._browse_ads(page)
                
                # Добавление в избранное
                await log_message("6. Добавляю объявления в избранное...")
                await self._add_to_favorites(page)
                
                # Просмотр профиля
                await log_message("7. Проверяю профиль...")
                await self._check_profile(page)
                
                await browser.close()
                await log_message("Прогрев аккаунта успешно завершён!")
                return "Прогрев успешно завершён"
                
        except Exception as e:
            error_msg = f"Ошибка прогрева аккаунта: {str(e)}"
            logger.error(error_msg)
            await log_message(error_msg)
            return f"Ошибка прогрева: {str(e)}"
    
    async def _random_delay(self, min_seconds: float = 1.0, max_seconds: float = 5.0) -> None:
        """Выполняет случайную задержку для имитации человеческого поведения."""
        delay = random.uniform(min_seconds, max_seconds)
        await asyncio.sleep(delay)
    
    async def _random_scroll(self, page) -> None:
        """Выполняет случайную прокрутку страницы."""
        scroll_count = random.randint(3, 7)
        for _ in range(scroll_count):
            await page.evaluate(f'window.scrollBy(0, {random.randint(300, 700)})')
            await self._random_delay(0.5, 2.0)
    
    async def _browse_categories(self, page) -> None:
        """Просматривает случайные категории."""
        try:
            # Попытка найти категории на странице
            categories = await page.query_selector_all('a[href*="categoria"]')
            if categories and len(categories) > 0:
                # Выбираем случайную категорию
                random_category = random.choice(categories)
                await random_category.click()
                await self._random_delay(2, 5)
                # Возвращаемся назад
                await page.go_back()
                await self._random_delay(1, 3)
        except Exception as e:
            logger.error(f"Ошибка при просмотре категорий: {e}")
    
    async def _perform_search(self, page) -> None:
        """Выполняет поиск случайных товаров."""
        try:
            search_terms = ["mesa", "silla", "teléfono", "ordenador", "coche"]
            search_term = random.choice(search_terms)
            
            # Находим поле поиска и вводим запрос
            search_input = await page.query_selector('input[type="search"]')
            if search_input:
                await search_input.fill(search_term)
                await self._random_delay(0.5, 1.5)
                await page.keyboard.press('Enter')
                await page.wait_for_load_state('networkidle')
                await self._random_delay(2, 4)
        except Exception as e:
            logger.error(f"Ошибка при выполнении поиска: {e}")
    
    async def _browse_ads(self, page) -> None:
        """Просматривает детали объявлений."""
        try:
            ads = await page.query_selector_all('a.ad-item')
            if ads and len(ads) > 0:
                # Выбираем несколько случайных объявлений
                browse_count = min(random.randint(2, 4), len(ads))
                
                for _ in range(browse_count):
                    ad = random.choice(ads)
                    await ad.click()
                    await self._random_delay(3, 7)
                    
                    # Прокрутка на странице объявления
                    await self._random_scroll(page)
                    
                    # Возвращаемся назад
                    await page.go_back()
                    await self._random_delay(1, 3)
        except Exception as e:
            logger.error(f"Ошибка при просмотре объявлений: {e}")
    
    async def _add_to_favorites(self, page) -> None:
        """Добавляет объявления в избранное."""
        try:
            favorite_buttons = await page.query_selector_all('.favorite-button, [class*="favorite"], [class*="like"]')
            if favorite_buttons and len(favorite_buttons) > 0:
                # Добавляем в избранное 1-2 объявления
                add_count = min(random.randint(1, 2), len(favorite_buttons))
                
                for i in range(add_count):
                    button = favorite_buttons[i]
                    await button.click()
                    await self._random_delay(1, 2)
        except Exception as e:
            logger.error(f"Ошибка при добавлении в избранное: {e}")
    
    async def _check_profile(self, page) -> None:
        """Проверяет профиль пользователя."""
        try:
            profile_link = await page.query_selector('a[href*="perfil"], [class*="profile"], [class*="account"]')
            if profile_link:
                await profile_link.click()
                await self._random_delay(2, 4)
                await self._random_scroll(page)
                await page.go_back()
                await self._random_delay(1, 2)
        except Exception as e:
            logger.error(f"Ошибка при проверке профиля: {e}")
