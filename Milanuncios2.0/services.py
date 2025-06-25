import asyncio
import logging
from typing import List, Dict, Any, Tuple, Optional
import os
import json

logger = logging.getLogger(__name__)

class MilanunciosService:
    """Сервисный класс для управления функциями Milanuncios"""
    
    def __init__(self, bot, admin_chat_id, account_manager, register_module, 
                parser_module, warmup_module, message_sender):
        """Инициализация сервиса"""
        self.bot = bot
        self.admin_chat_id = admin_chat_id
        self.account_manager = account_manager
        self.register_module = register_module
        self.parser_module = parser_module
        self.warmup_module = warmup_module
        self.message_sender = message_sender
        
        # Дополнительное состояние для управления рассылкой
        self.mailing_active = False
        self.mailing_task = None
        
        # Загрузка прокси и шаблонов
        self._load_proxies()
        self._load_message_templates()
        
        # Инициализация воркеров (заглушки)
        self.workers = ["Worker-1", "Worker-2", "Worker-3"]
        self.worker_status = {i: "stopped" for i in range(len(self.workers))}
    
    # --- Базовые операции с логами ---
    
    async def log_to_admin(self, message: str):
        """Отправка логов в административный чат"""
        logger.info(message)
        try:
            await self.bot.send_message(self.admin_chat_id, message)
        except Exception as e:
            logger.error(f"Ошибка отправки сообщения в админ-чат: {e}")
    
    # --- Операции с аккаунтами ---
    
    def get_accounts(self) -> List[Dict[str, Any]]:
        """Получение списка аккаунтов"""
        return self.account_manager.get_all_accounts()
    
    def get_current_account(self) -> Optional[str]:
        """Получение текущего аккаунта"""
        return self.account_manager.current_account_info()
    
    async def register_new_account(self) -> bool:
        """Регистрация нового аккаунта"""
        success = await self.register_module.register_account_async()
        return success
    
    async def delete_account(self, idx: int) -> str:
        """Удаление аккаунта"""
        accounts = self.get_accounts()
        if idx < 0 or idx >= len(accounts):
            return "Аккаунт не найден"
        
        email = accounts[idx]["email"]
        result = self.account_manager.mark_account_inactive(email)
        
        if result:
            await self.log_to_admin(f"Аккаунт {email} помечен как неактивный")
            return f"Аккаунт {email} помечен как неактивный"
        else:
            return f"Ошибка при изменении статуса аккаунта {email}"
    
    async def switch_account(self) -> Optional[str]:
        """Переключение на другой аккаунт"""
        return await self.account_manager.switch_account_async()
    
    # --- Операции с рассылкой ---
    
    async def start_mailing(self) -> str:
        """Запуск автоматической рассылки"""
        if self.mailing_active:
            return "Рассылка уже запущена"
        
        self.mailing_active = True
        self.mailing_task = asyncio.create_task(self._mailing_worker())
        await self.log_to_admin("Автоматическая рассылка запущена")
        return "Автоматическая рассылка запущена"
    
    async def stop_mailing(self) -> str:
        """Остановка автоматической рассылки"""
        if not self.mailing_active:
            return "Рассылка не запущена"
        
        self.mailing_active = False
        if self.mailing_task:
            self.mailing_task.cancel()
            self.mailing_task = None
        
        await self.log_to_admin("Автоматическая рассылка остановлена")
        return "Автоматическая рассылка остановлена"
    
    async def _mailing_worker(self):
        """Фоновый процесс для автоматической рассылки"""
        try:
            while self.mailing_active:
                await self.log_to_admin("Выполняется автоматическая рассылка...")
                
                # Парсим объявления
                ads = await self.parser_module.parse_ads_async(max_ads=5)  # Ограничиваем количество
                
                if ads:
                    # Перебираем объявления и отправляем сообщения
                    for ad in ads:
                        if not self.mailing_active:
                            break
                            
                        if "url" in ad:
                            success, limit_reached = await self.message_sender.send_message_async(ad_url=ad["url"])
                            
                            if limit_reached:
                                # Если достигнут лимит, переключаем аккаунт
                                await self.log_to_admin("Достигнут лимит сообщений. Переключение аккаунта...")
                                new_account = await self.switch_account()
                                
                                if not new_account:
                                    await self.log_to_admin("Нет доступных аккаунтов. Рассылка приостановлена.")
                                    self.mailing_active = False
                                    break
                            
                            # Пауза между сообщениями
                            await asyncio.sleep(30)  # 30 секунд между сообщениями
                
                # Пауза между циклами рассылки
                await asyncio.sleep(300)  # 5 минут между циклами
                
        except asyncio.CancelledError:
            await self.log_to_admin("Задача рассылки отменена")
        except Exception as e:
            await self.log_to_admin(f"Ошибка в задаче рассылки: {e}")
            self.mailing_active = False
    
    async def get_stats(self) -> str:
        """Получение статистики работы"""
        active_accounts = sum(1 for acc in self.get_accounts() if acc["status"] == "active")
        current_account = self.get_current_account() or "Нет"
        
        stats = f"📊 Статистика:\n\n"
        stats += f"Активных аккаунтов: {active_accounts}/{len(self.get_accounts())}\n"
        stats += f"Текущий аккаунт: {current_account}\n"
        stats += f"Рассылка активна: {'Да' if self.mailing_active else 'Нет'}\n"
        stats += f"Прокси: {len(self.get_proxies())}\n"
        stats += f"Шаблонов сообщений: {len(self.get_message_templates())}\n"
        
        return stats
    
    # --- Операции с Milanuncios ---
    
    async def parse_ads(self, max_ads: int = 20) -> List[Dict[str, str]]:
        """Парсинг объявлений"""
        return await self.parser_module.parse_ads_async(max_ads=max_ads)
    
    async def warmup_account(self) -> str:
        """Прогрев аккаунта"""
        return await self.warmup_module.warmup_account_async()
    
    async def send_message(self, ad_url: Optional[str] = None) -> Tuple[bool, bool]:
        """Отправка сообщения"""
        return await self.message_sender.send_message_async(ad_url)
    
    # --- Операции с прокси ---
    
    def _load_proxies(self):
        """Загрузка списка прокси из файла"""
        self.proxies = []
        try:
            if os.path.exists("proxies.json"):
                with open("proxies.json", "r", encoding="utf-8") as f:
                    self.proxies = json.load(f)
        except Exception as e:
            logger.error(f"Ошибка загрузки прокси: {e}")
            self.proxies = []
    
    def _save_proxies(self):
        """Сохранение списка прокси в файл"""
        try:
            with open("proxies.json", "w", encoding="utf-8") as f:
                json.dump(self.proxies, f, indent=4)
        except Exception as e:
            logger.error(f"Ошибка сохранения прокси: {e}")
    
    def get_proxies(self) -> List[str]:
        """Получение списка прокси"""
        return self.proxies
    
    async def add_proxy(self) -> str:
        """Добавление нового прокси (заглушка)"""
        # В реальном коде здесь должен быть запрос на ввод прокси
        new_proxy = f"http://user:pass@proxy{len(self.proxies)+1}.example.com:8080"
        self.proxies.append(new_proxy)
        self._save_proxies()
        await self.log_to_admin(f"Добавлен новый прокси: {new_proxy}")
        return f"Прокси {new_proxy} успешно добавлен"
    
    async def delete_proxy(self, idx: int) -> str:
        """Удаление прокси"""
        if idx < 0 or idx >= len(self.proxies):
            return "Прокси не найден"
        
        deleted = self.proxies.pop(idx)
        self._save_proxies()
        await self.log_to_admin(f"Удален прокси: {deleted}")
        return f"Прокси {deleted} успешно удален"
    
    # --- Операции с шаблонами сообщений ---
    
    def _load_message_templates(self):
        """Загрузка шаблонов сообщений из файла"""
        self.message_templates = [
            "Здравствуйте! Интересует ваш товар. Можно узнать подробнее?",
            "Добрый день! Заинтересовал ваш товар. Он все еще доступен?",
            "Привет! Хочу уточнить актуальность вашего объявления.",
            "Здравствуйте! Можно узнать дополнительную информацию по вашему объявлению?"
        ]
        
        try:
            if os.path.exists("message_templates.json"):
                with open("message_templates.json", "r", encoding="utf-8") as f:
                    self.message_templates = json.load(f)
        except Exception as e:
            logger.error(f"Ошибка загрузки шаблонов: {e}")
    
    def _save_message_templates(self):
        """Сохранение шаблонов сообщений в файл"""
        try:
            with open("message_templates.json", "w", encoding="utf-8") as f:
                json.dump(self.message_templates, f, indent=4)
        except Exception as e:
            logger.error(f"Ошибка сохранения шаблонов: {e}")
    
    def get_message_templates(self) -> List[str]:
        """Получение списка шаблонов сообщений"""
        return self.message_templates
    
    async def add_message_template(self) -> str:
        """Добавление нового шаблона (заглушка)"""
        # В реальном коде здесь должен быть запрос на ввод шаблона
        new_template = f"Шаблон сообщения #{len(self.message_templates)+1}"
        self.message_templates.append(new_template)
        self._save_message_templates()
        await self.log_to_admin(f"Добавлен новый шаблон сообщения")
        return f"Шаблон успешно добавлен"
    
    async def delete_message_template(self, idx: int) -> str:
        """Удаление шаблона"""
        if idx < 0 or idx >= len(self.message_templates):
            return "Шаблон не найден"
        
        deleted = self.message_templates.pop(idx)
        self._save_message_templates()
        await self.log_to_admin(f"Удален шаблон сообщения: {deleted[:20]}...")
        return f"Шаблон успешно удален"
    
    # --- Операции с воркерами (заглушки) ---
    
    def get_workers(self) -> List[str]:
        """Получение списка воркеров"""
        return self.workers
    
    async def start_workers(self) -> str:
        """Запуск всех воркеров"""
        for i in range(len(self.workers)):
            self.worker_status[i] = "running"
        
        await self.log_to_admin("Запущены все воркеры")
        return "Запущены все воркеры"
    
    async def stop_all_workers(self) -> str:
        """Остановка всех воркеров"""
        for i in range(len(self.workers)):
            self.worker_status[i] = "stopped"
        
        await self.log_to_admin("Остановлены все воркеры")
        return "Остановлены все воркеры"
    
    async def worker_action(self, worker_id: int, action: str) -> str:
        """Выполнение действия над воркером"""
        if worker_id < 0 or worker_id >= len(self.workers):
            return "Воркер не найден"
        
        worker_name = self.workers[worker_id]
        
        if action == "start":
            self.worker_status[worker_id] = "running"
            await self.log_to_admin(f"Запущен воркер {worker_name}")
            return f"Запущен воркер {worker_name}"
        
        elif action == "stop":
            self.worker_status[worker_id] = "stopped"
            await self.log_to_admin(f"Остановлен воркер {worker_name}")
            return f"Остановлен воркер {worker_name}"
        
        elif action == "status":
            status = self.worker_status[worker_id]
            return f"Статус воркера {worker_name}: {status}"
        
        elif action == "logs":
            return f"Логи воркера {worker_name}:\nПример лога 1\nПример лога 2\nПример лога 3"
        
        elif action == "delete":
            del self.workers[worker_id]
            del self.worker_status[worker_id]
            await self.log_to_admin(f"Удален воркер {worker_name}")
            return f"Удален воркер {worker_name}"
        
        return f"Неизвестное действие {action} для воркера {worker_name}"
    
    # --- Операции с логами, ошибками и настройками ---
    
    async def get_logs(self) -> str:
        """Получение последних логов"""
        try:
            if os.path.exists("bot.log"):
                with open("bot.log", "r", encoding="utf-8") as f:
                    logs = f.readlines()
                return "📝 Последние логи:\n\n" + "".join(logs[-20:])  # Последние 20 строк
            return "Файл логов не найден"
        except Exception as e:
            return f"Ошибка при чтении логов: {e}"
    
    async def get_errors(self) -> str:
        """Получение списка ошибок"""
        try:
            if os.path.exists("bot.log"):
                with open("bot.log", "r", encoding="utf-8") as f:
                    logs = f.readlines()
                
                # Фильтруем только строки с ошибками
                errors = [log for log in logs if "ERROR" in log]
                return "❌ Последние ошибки:\n\n" + "".join(errors[-10:])  # Последние 10 ошибок
            return "Файл логов не найден"
        except Exception as e:
            return f"Ошибка при чтении логов: {e}"
    
    async def get_settings(self) -> str:
        """Получение текущих настроек"""
        settings = "⚙️ Настройки:\n\n"
        settings += f"✅ Headless режим: {'Включен' if True else 'Выключен'}\n"
        settings += f"✅ Лимит сообщений: {self.message_sender.message_limit}\n"
        settings += f"✅ Автоматическая смена IP: {'Включена' if True else 'Выключена'}\n"
        settings += f"✅ Интервал отправки: 30 секунд\n"
        return settings
    
    async def update_setting(self, setting_name: str) -> str:
        """Обновление настройки"""
        # Заглушка для обновления настроек
        await self.log_to_admin(f"Изменена настройка: {setting_name}")
        return f"Настройка {setting_name} изменена"