import asyncio
from playwright.async_api import async_playwright
import logging
import random
from typing import Tuple, Dict, Any, Optional, List

logger = logging.getLogger(__name__)

class MessageSender:
    def __init__(self, bot, admin_chat_id, account_manager, message_limit: int = 20):
        """
        Инициализирует отправитель сообщений.
        
        :param bot: Объект бота для отправки уведомлений
        :param admin_chat_id: ID чата для логирования
        :param account_manager: Объект менеджера аккаунтов
        :param message_limit: Максимальное количество сообщений для одного аккаунта
        """
        self.bot = bot
        self.admin_chat_id = admin_chat_id
        self.account_manager = account_manager
        self.message_limit = message_limit
        self.message_templates = [
            "Здравствуйте! Интересует ваш товар. Можно узнать подробнее?",
            "Добрый день! Заинтересовал ваш товар. Он все еще доступен?",
            "Привет! Хочу уточнить актуальность вашего объявления.",
            "Здравствуйте! Можно узнать дополнительную информацию по вашему объявлению?"
        ]
        
    async def send_message_async(self, ad_url: Optional[str] = None) -> Tuple[bool, bool]:
        """
        Асинхронная функция отправки сообщения.
        
        :param ad_url: URL объявления для отправки сообщения
        :return: Tuple (успех, лимит_достигнут)
        """
        async def log_message(message: str):
            logger.info(message)
            try:
                await self.bot.send_message(self.admin_chat_id, message)
            except Exception as e:
                logger.error(f"Ошибка отправки сообщения в админ-чат: {e}")
        
        try:
            # Получаем текущий аккаунт
            account_data = self.account_manager.get_current_account_data()
            
            if not account_data:
                await log_message("Нет доступных аккаунтов для отправки сообщений.")
                return False, False
            
            current_message_count = account_data.get("message_count", 0)
            
            # Проверка лимита сообщений
            if current_message_count >= self.message_limit:
                await log_message(f"Достигнут лимит сообщений для аккаунта {account_data['email']}.")
                return False, True
            
            await log_message(f"Отправляю сообщение от аккаунта {account_data['email']} ({current_message_count + 1}/{self.message_limit})")
            
            async with async_playwright() as p:
                browser = await p.chromium.launch(headless=True)
                context = await browser.new_context(
                    user_agent='Mozilla/5.0 (Linux; Android 10; Mobile; rv:89.0) Gecko/89.0 Firefox/89.0',
                    viewport={'width': 360, 'height': 640}
                )
                
                # Восстановление cookies если они есть
                if "cookies" in account_data and account_data["cookies"]:
                    await context.add_cookies(account_data["cookies"])
                
                page = await context.new_page()
                
                # Переход на страницу объявления или сообщений
                url = ad_url or 'https://www.milanuncios.com/messages'
                await page.goto(url)
                
                # Проверка авторизации
                is_logged_in = await self._check_logged_in(page)
                if not is_logged_in:
                    await log_message("Необходимо выполнить вход в аккаунт.")
                    # Здесь можно добавить код для входа в аккаунт
                    await browser.close()
                    return False, False
                
                # Выбор случайного шаблона сообщения
                message_text = random.choice(self.message_templates)
                
                # Если перешли на страницу объявления, ищем кнопку "Написать сообщение"
                if ad_url:
                    try:
                        contact_button = await page.wait_for_selector('button:has-text("Контакт"), button:has-text("Написать"), [class*="contact"]', timeout=5000)
                        await contact_button.click()
                    except Exception as e:
                        await log_message(f"Не удалось найти кнопку контакта: {e}")
                        await browser.close()
                        return False, False
                
                # Ожидание загрузки формы отправки сообщения
                try:
                    await page.wait_for_selector('textarea[name="message"], [role="textbox"]', timeout=5000)
                except Exception as e:
                    await log_message(f"Не удалось найти поле для сообщения: {e}")
                    await browser.close()
                    return False, False
                
                # Отправка сообщения
                await page.fill('textarea[name="message"], [role="textbox"]', message_text)
                
                # Небольшая задержка перед отправкой (имитация человека)
                await asyncio.sleep(random.uniform(1, 3))
                
                # Нажатие на кнопку отправки
                await page.click('button[type="submit"], button:has-text("Отправить"), button:has-text("Enviar")')
                
                # Проверка успешной отправки (может быть различной на разных сайтах)
                try:
                    success_element = await page.wait_for_selector('.success-message, [class*="success"]', timeout=5000)
                    success_text = await success_element.inner_text()
                    await log_message(f"Сообщение успешно отправлено. Статус: {success_text}")
                except Exception as e:
                    # Проверим наличие сообщения в истории как альтернативный способ проверки
                    await page.goto('https://www.milanuncios.com/messages')
                    if await page.locator(':text("' + message_text[:20] + '")').count() > 0:
                        await log_message("Сообщение отправлено успешно (проверено по истории).")
                    else:
                        await log_message(f"Не удалось подтвердить отправку сообщения: {e}")
                        await browser.close()
                        return False, False
                
                # Увеличиваем счетчик отправленных сообщений
                self.account_manager.increment_message_count()
                
                # Сохраняем обновленные cookies
                cookies = await context.cookies()
                account_data["cookies"] = cookies
                
                await browser.close()
                return True, False  # Сообщение успешно отправлено, лимит не достигнут
                
        except Exception as e:
            error_msg = f"Ошибка отправки сообщений: {str(e)}"
            logger.error(error_msg)
            await log_message(error_msg)
            return False, False
    
    async def _check_logged_in(self, page) -> bool:
        """Проверяет, авторизован ли пользователь."""
        try:
            # Проверка наличия элементов, которые видны только авторизованным пользователям
            profile_elements = await page.query_selector_all('[class*="profile"], [class*="account"], .user-menu, .avatar')
            return len(profile_elements) > 0
        except Exception:
            return False
