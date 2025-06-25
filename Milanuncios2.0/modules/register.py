import asyncio
from playwright.async_api import async_playwright
import logging
import os
import random
import string
from typing import Dict, Any, Tuple, Optional, List
import json
from datetime import datetime

logger = logging.getLogger(__name__)

class RegisterModule:
    def __init__(self, bot, admin_chat_id):
        """
        Инициализирует модуль регистрации.
        
        :param bot: Объект бота для отправки уведомлений
        :param admin_chat_id: ID чата для логирования
        """
        self.bot = bot
        self.admin_chat_id = admin_chat_id
        self._captcha_response = None
        self._captcha_requested = False
    
    async def register_account_async(self, use_headless: bool = False) -> bool:
        """
        Асинхронная функция регистрации аккаунта.
        
        :param use_headless: Использовать headless режим
        :return: True если регистрация успешна, иначе False
        """
        async def log_message(message: str):
            logger.info(message)
            try:
                await self.bot.send_message(self.admin_chat_id, message)
            except Exception as e:
                logger.error(f"Ошибка отправки сообщения в админ-чат: {e}")
        
        try:
            await log_message("Начинаю регистрацию аккаунта...")
            
            # Генерация случайных учетных данных
            email = self._generate_email()
            password = self._generate_password()
            
            async with async_playwright() as p:
                browser = await p.chromium.launch(headless=use_headless)
                context = await browser.new_context(
                    user_agent='Mozilla/5.0 (Linux; Android 10; Mobile; rv:89.0) Gecko/89.0 Firefox/89.0',
                    viewport={'width': 360, 'height': 640}
                )
                
                page = await context.new_page()
                await page.goto('https://www.milanuncios.com/registro')
                
                # Проверка наличия формы регистрации
                try:
                    await page.wait_for_selector('form', timeout=10000)
                except Exception as e:
                    await log_message(f"Форма регистрации не найдена: {e}")
                    return False
                
                # Заполнение формы регистрации
                await page.fill('input[name="email"]', email)
                await page.fill('input[name="password"]', password)
                await page.fill('input[name="confirmPassword"]', password)
                
                # Отметка согласия с условиями
                await page.check('input[name="termsAccepted"]')
                
                # Проверка наличия капчи
                if await page.locator('img.captcha').count() > 0:
                    # Отправка капчи в Telegram
                    captcha_image = await page.locator('img.captcha').screenshot()
                    
                    # Сбрасываем флаг ответа на запрос капчи
                    self._captcha_requested = True
                    self._captcha_response = None
                    
                    # Отправка изображения в админ-чат
                    await self.bot.send_photo(
                        self.admin_chat_id, 
                        captcha_image, 
                        caption="Введите капчу (отправьте текст в ответном сообщении):"
                    )
                    
                    # Ожидание ответа от пользователя через Telegram (максимум 2 минуты)
                    captcha_solution = await self._wait_for_captcha(120)
                    
                    if not captcha_solution:
                        await log_message("Время ожидания ввода капчи истекло")
                        await browser.close()
                        return False
                    
                    await page.fill('input[name="captcha"]', captcha_solution)
                
                # Нажатие кнопки регистрации
                await page.click('button[type="submit"]')
                
                # Ожидание результата
                try:
                    # Проверяем успешную регистрацию по наличию сообщения об успехе
                    await page.wait_for_selector('.success-message', timeout=10000)
                    
                    # Сохраняем куки для дальнейшего использования
                    cookies = await context.cookies()
                    self._save_credentials(email, password, cookies)
                    
                    await browser.close()
                    await log_message(f"Аккаунт успешно зарегистрирован: {email}")
                    return True
                    
                except Exception as e:
                    # Проверка на ошибку регистрации
                    error_text = await page.locator('.error-message').inner_text() if await page.locator('.error-message').count() > 0 else "неизвестная ошибка"
                    await log_message(f"Ошибка регистрации: {error_text}")
                    await browser.close()
                    return False
                    
        except Exception as e:
            error_msg = f"Ошибка при регистрации аккаунта: {str(e)}"
            logger.error(error_msg)
            await log_message(error_msg)
            return False
    
    def _generate_email(self) -> str:
        """Генерирует случайный электронный адрес."""
        random_part = ''.join(random.choices(string.ascii_lowercase + string.digits, k=8))
        return f"user_{random_part}@example.com"
    
    def _generate_password(self) -> str:
        """Генерирует случайный надежный пароль."""
        # Минимум 8 символов, включая буквы разного регистра, цифры и спец. символы
        chars = string.ascii_letters + string.digits + "!@#$%^&*"
        return ''.join(random.choices(chars, k=12))
    
    def _save_credentials(self, email: str, password: str, cookies: list) -> None:
        """Сохраняет учетные данные в файл."""
        credentials_file = "credentials.json"
        
        # Загружаем существующие данные
        credentials = []
        if os.path.exists(credentials_file):
            try:
                with open(credentials_file, 'r', encoding='utf-8') as f:
                    credentials = json.load(f)
            except:
                credentials = []
        
        # Добавляем новые данные
        credentials.append({
            "email": email,
            "password": password,  # В реальном приложении следует использовать безопасное хранение, например, через keyring
            "created_at": datetime.now().isoformat(),
            "cookies": cookies
        })
        
        # Сохраняем обновленные данные
        with open(credentials_file, 'w', encoding='utf-8') as f:
            json.dump(credentials, f, indent=4)
        
        # Установим безопасные разрешения для файла
        try:
            os.chmod(credentials_file, 0o600)  # Только владелец может читать и писать
        except:
            pass  # Может не работать на Windows
    
    async def _wait_for_captcha(self, timeout: int = 120) -> Optional[str]:
        """
        Ожидает ответ на запрос капчи.
        
        :param timeout: Время ожидания в секундах
        :return: Текст капчи или None, если время истекло
        """
        start_time = datetime.now()
        
        while (datetime.now() - start_time).total_seconds() < timeout:
            if self._captcha_response:
                response = self._captcha_response
                self._captcha_response = None
                self._captcha_requested = False
                return response
            await asyncio.sleep(1)
        
        return None
    
    async def set_captcha_response(self, response: str) -> None:
        """
        Устанавливает ответ на запрос капчи.
        
        :param response: Текст капчи
        """
        if self._captcha_requested:
            self._captcha_response = response
