import asyncio
from playwright.async_api import async_playwright
from typing import List, Dict, Any, Optional
import logging
import random
import time

logger = logging.getLogger(__name__)

class ParserModule:
    def __init__(self, bot, admin_chat_id):
        """
        Инициализирует модуль парсера.
        
        :param bot: Объект бота для отправки уведомлений
        :param admin_chat_id: ID чата для логирования
        """
        self.bot = bot
        self.admin_chat_id = admin_chat_id
        self.user_agents = [
            'Mozilla/5.0 (Linux; Android 10; Mobile; rv:89.0) Gecko/89.0 Firefox/89.0',
            'Mozilla/5.0 (iPhone; CPU iPhone OS 14_6 like Mac OS X) AppleWebKit/605.1.15 Mobile/15E148 Safari/604.1',
            'Mozilla/5.0 (Linux; Android 11; SM-G975F) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.120 Mobile Safari/537.36'
        ]
    
    async def parse_ads_async(self, url: str = 'https://www.milanuncios.com', max_ads: int = 30) -> List[Dict[str, str]]:
        """
        Асинхронная функция парсинга объявлений.
        
        :param url: URL для парсинга
        :param max_ads: Максимальное количество объявлений для парсинга
        :return: Список словарей с данными объявлений
        """
        async def log_message(message: str):
            logger.info(message)
            try:
                await self.bot.send_message(self.admin_chat_id, message)
            except Exception as e:
                logger.error(f"Ошибка отправки сообщения в админ-чат: {e}")
        
        try:
            await log_message(f"Начинаю парсинг объявлений с {url}")
            
            async with async_playwright() as p:
                # Случайный выбор User-Agent
                user_agent = random.choice(self.user_agents)
                
                # Запуск браузера с прокси, если настроено
                browser = await p.chromium.launch(headless=True)
                
                context = await browser.new_context(
                    user_agent=user_agent,
                    viewport={'width': 360, 'height': 640}
                )
                
                # Добавляем задержку для имитации человеческого поведения
                await asyncio.sleep(random.uniform(1, 3))
                
                page = await context.new_page()
                await page.goto(url, wait_until='domcontentloaded')
                
                # Ожидание загрузки динамического контента
                try:
                    await page.wait_for_selector('.ad-item', timeout=30000)
                except Exception as e:
                    await log_message(f"Ошибка ожидания селектора: {e}")
                    return []
                
                # Прокрутка страницы для загрузки дополнительного контента
                await self._scroll_page(page)

                ads = []
                ad_elements = await page.query_selector_all('.ad-item')
                
                for i, ad in enumerate(ad_elements):
                    if i >= max_ads:
                        break
                        
                    try:
                        title_element = await ad.query_selector('.ad-title')
                        price_element = await ad.query_selector('.ad-price')
                        location_element = await ad.query_selector('.ad-location')
                        
                        title = await title_element.inner_text() if title_element else "Нет заголовка"
                        price = await price_element.inner_text() if price_element else "Цена не указана"
                        location = await location_element.inner_text() if location_element else "Локация не указана"
                        
                        # Извлечение URL объявления
                        url_element = await ad.query_selector('a')
                        url = await url_element.get_attribute('href') if url_element else ""
                        
                        ads.append({
                            'title': title.strip(),
                            'price': price.strip(),
                            'location': location.strip(),
                            'url': url
                        })
                    except Exception as e:
                        logger.error(f"Ошибка при парсинге объявления: {e}")

                await browser.close()
                
                await log_message(f"Парсинг завершён. Найдено {len(ads)} объявлений.")
                return ads
                
        except Exception as e:
            error_msg = f"Ошибка парсинга: {str(e)}"
            logger.error(error_msg)
            await log_message(error_msg)
            return []

    async def _scroll_page(self, page, scrolls: int = 3, scroll_delay: float = 1.0):
        """Прокручивает страницу для загрузки динамического контента"""
        for _ in range(scrolls):
            await page.evaluate('window.scrollBy(0, window.innerHeight)')
            await asyncio.sleep(scroll_delay)
