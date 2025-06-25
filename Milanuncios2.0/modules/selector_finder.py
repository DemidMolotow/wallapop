import asyncio
from playwright.async_api import async_playwright
import json
import logging
from typing import Dict, Any, List, Optional

logger = logging.getLogger(__name__)

class SelectorFinder:
    """
    Класс для поиска и сохранения селекторов на веб-страницах.
    Полезен для подготовки к автоматизации или обновления селекторов при изменении сайта.
    """
    
    def __init__(self, headless: bool = False):
        """
        Инициализирует поиск селекторов.
        
        :param headless: Использовать headless режим браузера
        """
        self.headless = headless
    
    async def find_selectors_async(self, url: str, output_file: str = 'selectors.json') -> Dict[str, Any]:
        """
        Асинхронный поиск селекторов на странице.
        
        :param url: URL страницы для анализа
        :param output_file: Имя файла для сохранения селекторов
        :return: Словарь с найденными селекторами
        """
        try:
            logger.info(f"Начинаю поиск селекторов на {url}")
            
            async with async_playwright() as p:
                browser = await p.chromium.launch(headless=self.headless)
                context = await browser.new_context(
                    user_agent='Mozilla/5.0 (Linux; Android 10; Mobile; rv:89.0) Gecko/89.0 Firefox/89.0',
                    viewport={'width': 360, 'height': 640}
                )
                
                page = await context.new_page()
                await page.goto(url, wait_until='networkidle')
                
                selectors = {}
                
                # Поиск и анализ форм
                selectors['forms'] = await self._analyze_forms(page)
                
                # Поиск важных навигационных элементов
                selectors['navigation'] = await self._analyze_navigation(page)
                
                # Поиск элементов для авторизации
                selectors['auth'] = await self._analyze_auth(page)
                
                # Поиск элементов списка объявлений
                selectors['ads'] = await self._analyze_ads(page)
                
                await browser.close()
                
                # Сохранение результатов в файл
                with open(output_file, 'w', encoding='utf-8') as f:
                    json.dump(selectors, f, indent=4)
                
                logger.info(f"Селекторы сохранены в {output_file}")
                return selectors
                
        except Exception as e:
            logger.error(f"Ошибка поиска селекторов: {e}")
            return {}
    
    async def _analyze_forms(self, page) -> Dict[str, Any]:
        """Анализирует формы на странице."""
        result = {}
        
        try:
            forms = await page.query_selector_all('form')
            
            for i, form in enumerate(forms):
                form_id = await form.get_attribute('id') or f"form_{i}"
                form_data = {
                    "selector": f"form#{form_id}" if await form.get_attribute('id') else f"form:nth-of-type({i+1})",
                    "inputs": {},
                    "buttons": {}
                }
                
                # Анализ полей ввода
                inputs = await form.query_selector_all('input, select, textarea')
                for input_el in inputs:
                    input_type = await input_el.get_attribute('type') or 'text'
                    input_name = await input_el.get_attribute('name')
                    input_id = await input_el.get_attribute('id')
                    
                    if not input_name and not input_id:
                        continue
                        
                    selector_key = input_id or input_name
                    form_data["inputs"][selector_key] = {
                        "selector": f"#{input_id}" if input_id else f"[name='{input_name}']",
                        "type": input_type,
                        "required": await input_el.get_attribute('required') is not None
                    }
                
                # Анализ кнопок
                buttons = await form.query_selector_all('button, input[type="submit"], input[type="button"]')
                for j, button in enumerate(buttons):
                    button_text = await button.inner_text() if await button.get_property('tagName') == 'BUTTON' else await button.get_attribute('value')
                    button_id = await button.get_attribute('id')
                    button_type = await button.get_attribute('type') or 'button'
                    
                    selector_key = f"button_{j}"
                    if button_text:
                        selector_key = f"button_{button_text.lower().replace(' ', '_')}"
                    elif button_id:
                        selector_key = f"button_{button_id}"
                    
                    form_data["buttons"][selector_key] = {
                        "selector": f"#{button_id}" if button_id else f"button:contains('{button_text}')" if button_text else f"button:nth-of-type({j+1})",
                        "text": button_text,
                        "type": button_type
                    }
                
                result[form_id] = form_data
            
        except Exception as e:
            logger.error(f"Ошибка при анализе форм: {e}")
        
        return result
    
    async def _analyze_navigation(self, page) -> Dict[str, Any]:
        """Анализирует навигационные элементы."""
        result = {}
        
        try:
            # Поиск элементов навигации
            nav_elements = await page.query_selector_all('nav, [role="navigation"], .nav, .menu, .navigation')
            
            for i, nav in enumerate(nav_elements):
                nav_id = await nav.get_attribute('id') or f"nav_{i}"
                
                # Поиск ссылок в навигации
                links = await nav.query_selector_all('a')
                nav_links = {}
                
                for j, link in enumerate(links):
                    link_text = await link.inner_text()
                    link_href = await link.get_attribute('href')
                    
                    if not link_text.strip():
                        continue
                    
                    link_key = f"link_{link_text.lower().replace(' ', '_')}"
                    nav_links[link_key] = {
                        "selector": f"a:contains('{link_text}')",
                        "href": link_href
                    }
                
                result[nav_id] = {
                    "selector": f"#{nav_id}" if await nav.get_attribute('id') else f"nav:nth-of-type({i+1})",
                    "links": nav_links
                }
            
        except Exception as e:
            logger.error(f"Ошибка при анализе навигации: {e}")
        
        return result
    
    async def _analyze_auth(self, page) -> Dict[str, Any]:
        """Анализирует элементы авторизации."""
        result = {}
        
        try:
            # Поиск кнопок логина/регистрации
            login_buttons = await page.query_selector_all('a:text-matches("(Login|Log in|Iniciar sesión|Entrar)", "i"), button:text-matches("(Login|Log in|Iniciar sesión|Entrar)", "i")')
            
            if login_buttons:
                login_button = login_buttons[0]
                result["login_button"] = {
                    "selector": await self._get_best_selector(login_button),
                    "text": await login_button.inner_text()
                }
            
            # Поиск кнопок регистрации
            register_buttons = await page.query_selector_all('a:text-matches("(Register|Sign up|Registro|Registrarse)", "i"), button:text-matches("(Register|Sign up|Registro|Registrarse)", "i")')
            
            if register_buttons:
                register_button = register_buttons[0]
                result["register_button"] = {
                    "selector": await self._get_best_selector(register_button),
                    "text": await register_button.inner_text()
                }
            
            # Поиск полей для ввода логина/пароля
            email_inputs = await page.query_selector_all('input[type="email"], input[name*="email"], input[placeholder*="email"], input[name*="login"], input[placeholder*="login"]')
            
            if email_inputs:
                email_input = email_inputs[0]
                result["email_input"] = {
                    "selector": await self._get_best_selector(email_input),
                    "type": await email_input.get_attribute('type'),
                    "name": await email_input.get_attribute('name')
                }
            
            # Поиск полей для ввода пароля
            password_inputs = await page.query_selector_all('input[type="password"]')
            
            if password_inputs:
                password_input = password_inputs[0]
                result["password_input"] = {
                    "selector": await self._get_best_selector(password_input),
                    "name": await password_input.get_attribute('name')
                }
            
        except Exception as e:
            logger.error(f"Ошибка при анализе элементов авторизации: {e}")
        
        return result
    
    async def _analyze_ads(self, page) -> Dict[str, Any]:
        """Анализирует элементы списка объявлений."""
        result = {}
        
        try:
            # Поиск блоков объявлений по популярным классам
            ad_containers = await page.query_selector_all('.ad, .ad-item, .listing-item, .product-item, [class*="ad-"], [class*="listing-"], [class*="product-"]')
            
            if ad_containers:
                # Берем первое объявление как образец
                ad = ad_containers[0]
                
                result["container_selector"] = await self._get_best_selector(ad)
                
                # Поиск элементов заголовка
                title_element = await ad.query_selector('h1, h2, h3, .title, [class*="title"], [class*="name"]')
                if title_element:
                    result["title_selector"] = await self._get_relative_selector(title_element, ad)
                
                # Поиск элементов цены
                price_element = await ad.query_selector('.price, [class*="price"], .cost, [class*="cost"]')
                if price_element:
                    result["price_selector"] = await self._get_relative_selector(price_element, ad)
                
                # Поиск элементов локации
                location_element = await ad.query_selector('.location, [class*="location"], .address, [class*="address"]')
                if location_element:
                    result["location_selector"] = await self._get_relative_selector(location_element, ad)
                
                # Поиск ссылки объявления
                link_element = await ad.query_selector('a')
                if link_element:
                    result["link_selector"] = await self._get_relative_selector(link_element, ad)
            
        except Exception as e:
            logger.error(f"Ошибка при анализе элементов объявлений: {e}")
        
        return result
    
    async def _get_best_selector(self, element) -> str:
        """Получает наиболее оптимальный селектор для элемента."""
        try:
            # Попытка использовать ID
            element_id = await element.get_attribute('id')
            if element_id:
                return f"#{element_id}"
            
            # Попытка использовать уникальный класс
            element_class = await element.get_attribute('class')
            if element_class:
                classes = element_class.split()
                if len(classes) > 0:
                    return f".{classes[0]}"
            
            # Резервный вариант - использовать XPath
            return await element.evaluate('el => {const xpath = []; let elem = el; while (elem && elem.nodeType === 1) { let idx = 1; for (let sibling = elem.previousSibling; sibling; sibling = sibling.previousSibling) { if (sibling.nodeType === 1 && sibling.tagName === elem.tagName) idx++; } const tagName = elem.tagName.toLowerCase(); xpath.unshift(`${tagName}[${idx}]`); elem = elem.parentNode; } return `/${xpath.join("/")}`;}')
            
        except Exception as e:
            logger.error(f"Ошибка получения селектора: {e}")
            return "unknown-selector"
    
    async def _get_relative_selector(self, child, parent) -> str:
        """Получает селектор дочернего элемента относительно родителя."""
        try:
            child_tag = await child.evaluate('el => el.tagName.toLowerCase()')
            
            # Попытка использовать ID
            child_id = await child.get_attribute('id')
            if child_id:
                return f"#{child_id}"
            
            # Попытка использовать класс
            child_class = await child.get_attribute('class')
            if child_class:
                classes = child_class.split()
                if len(classes) > 0:
                    return f".{classes[0]}"
            
            # Попытка использовать атрибут name
            child_name = await child.get_attribute('name')
            if child_name:
                return f"{child_tag}[name='{child_name}']"
            
            # Резервный вариант
            return child_tag
            
        except Exception as e:
            logger.error(f"Ошибка получения относительного селектора: {e}")
            return "unknown-selector"
