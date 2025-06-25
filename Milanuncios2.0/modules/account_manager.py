import json
import os
import asyncio
import logging
from datetime import datetime
from typing import Dict, List, Optional, Any

logger = logging.getLogger(__name__)

class AccountManager:
    def __init__(self, accounts_file: str = "accounts.json"):
        """
        Инициализация менеджера аккаунтов.
        
        :param accounts_file: Путь к JSON файлу с данными аккаунтов
        """
        self.accounts_file = accounts_file
        self.current_account_index = 0
        self.accounts = self._load_accounts()
        
    def _load_accounts(self) -> List[Dict[str, Any]]:
        """Загружает аккаунты из файла, создает файл если он не существует."""
        if os.path.exists(self.accounts_file):
            try:
                with open(self.accounts_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except json.JSONDecodeError:
                logger.error(f"Ошибка чтения файла аккаунтов {self.accounts_file}")
                return []
        else:
            # Создание файла с примером структуры
            example_accounts = [
                {
                    "email": "account1@example.com", 
                    "status": "active",
                    "message_count": 0,
                    "last_used": datetime.now().isoformat(),
                    "cookies": {}
                }
            ]
            with open(self.accounts_file, 'w', encoding='utf-8') as f:
                json.dump(example_accounts, f, indent=4)
            return example_accounts
    
    def _save_accounts(self) -> None:
        """Сохраняет аккаунты в файл."""
        with open(self.accounts_file, 'w', encoding='utf-8') as f:
            json.dump(self.accounts, f, indent=4)
    
    def switch_account(self) -> Optional[str]:
        """
        Переключает на следующий активный аккаунт из списка.
        Если активных аккаунтов больше нет, возвращает None.
        """
        if not self.accounts:
            return None
            
        for _ in range(len(self.accounts)):
            self.current_account_index = (self.current_account_index + 1) % len(self.accounts)
            if self.accounts[self.current_account_index]["status"] == "active":
                account = self.accounts[self.current_account_index]
                account["last_used"] = datetime.now().isoformat()
                self._save_accounts()
                return account["email"]
        return None
    
    async def switch_account_async(self) -> Optional[str]:
        """Асинхронная обертка для switch_account."""
        return await asyncio.to_thread(self.switch_account)
        
    def mark_account_inactive(self, email: str) -> bool:
        """Помечает аккаунт как неактивный."""
        for i, account in enumerate(self.accounts):
            if account["email"] == email:
                self.accounts[i]["status"] = "inactive"
                self._save_accounts()
                return True
        return False
    
    def reset_message_count(self, email: Optional[str] = None) -> bool:
        """Сбрасывает счетчик сообщений для указанного аккаунта или текущего."""
        if not email and self.accounts:
            email = self.current_account_info()
            
        for i, account in enumerate(self.accounts):
            if account["email"] == email:
                self.accounts[i]["message_count"] = 0
                self._save_accounts()
                return True
        return False
    
    def increment_message_count(self) -> int:
        """Увеличивает счетчик сообщений для текущего аккаунта."""
        if not self.accounts:
            return 0
            
        account = self.accounts[self.current_account_index]
        if "message_count" not in account:
            account["message_count"] = 0
            
        account["message_count"] += 1
        self._save_accounts()
        return account["message_count"]
    
    def current_account_info(self) -> Optional[str]:
        """
        Возвращает информацию о текущем активном аккаунте.
        Если активных аккаунтов больше нет, возвращает None.
        """
        if not self.accounts:
            return None
            
        if self.accounts[self.current_account_index]["status"] == "active":
            return self.accounts[self.current_account_index]["email"]
        return None
    
    def get_current_account_data(self) -> Dict[str, Any]:
        """Возвращает все данные текущего аккаунта."""
        if not self.accounts:
            return {}
        return self.accounts[self.current_account_index]
        
    def get_active_count(self) -> int:
        """Возвращает количество активных аккаунтов."""
        return sum(1 for account in self.accounts if account["status"] == "active")
        
    def get_all_accounts(self) -> List[Dict[str, Any]]:
        """Возвращает список всех аккаунтов."""
        return self.accounts
        
    def add_account(self, email: str, status: str = "active") -> bool:
        """Добавляет новый аккаунт."""
        for account in self.accounts:
            if account["email"] == email:
                return False  # Аккаунт уже существует
                
        self.accounts.append({
            "email": email,
            "status": status,
            "message_count": 0,
            "last_used": datetime.now().isoformat(),
            "cookies": {}
        })
        self._save_accounts()
        return True
