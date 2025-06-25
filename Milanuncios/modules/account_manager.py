# Модуль управления аккаунтами

# Список доступных аккаунтов
ACCOUNTS = [
    {"email": "account1@example.com", "status": "active"},
    {"email": "account2@example.com", "status": "active"},
    {"email": "account3@example.com", "status": "active"},
]

# Текущий аккаунт
current_account_index = 0

def switch_account():
    """
    Переключает на следующий активный аккаунт из списка.
    Если активных аккаунтов больше нет, возвращает None.
    """
    global current_account_index
    for _ in range(len(ACCOUNTS)):
        current_account_index = (current_account_index + 1) % len(ACCOUNTS)
        if ACCOUNTS[current_account_index]["status"] == "active":
            return ACCOUNTS[current_account_index]["email"]
    return None  # Если активных аккаунтов больше нет

def mark_account_inactive(email):
    """
    Помечает аккаунт как неактивный.
    """
    for account in ACCOUNTS:
        if account["email"] == email:
            account["status"] = "inactive"
            break

def current_account_info():
    """
    Возвращает информацию о текущем активном аккаунте.
    Если активных аккаунтов больше нет, возвращает None.
    """
    if ACCOUNTS[current_account_index]["status"] == "active":
        return ACCOUNTS[current_account_index]["email"]
    return None
