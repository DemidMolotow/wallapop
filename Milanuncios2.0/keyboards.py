from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from typing import List, Dict, Any

# --- ГЛАВНОЕ МЕНЮ ---
def main_menu() -> InlineKeyboardMarkup:
    """Клавиатура главного меню"""
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="▶️ Запустить рассылку", callback_data="start_mailing")],
        [InlineKeyboardButton(text="⏹️ Остановить рассылку", callback_data="stop_mailing")],
        [InlineKeyboardButton(text="📊 Статистика", callback_data="stats")],
        [InlineKeyboardButton(text="🔑 Аккаунты", callback_data="accounts_menu")],
        [InlineKeyboardButton(text="🌐 Milanuncios", callback_data="milanuncios_menu")],
        [InlineKeyboardButton(text="🔄 Прокси", callback_data="proxies_menu")],
        [InlineKeyboardButton(text="📝 Шаблоны", callback_data="pastes_menu")],
        [InlineKeyboardButton(text="👷 Воркеры", callback_data="workers_menu")],
        [InlineKeyboardButton(text="📜 Логи", callback_data="logs_menu")],
        [InlineKeyboardButton(text="❌ Ошибки", callback_data="errors_menu")],
        [InlineKeyboardButton(text="⚙️ Настройки", callback_data="settings_menu")]
    ])
    return keyboard

# --- МЕНЮ АККАУНТОВ ---
def accounts_menu(page: int = 0, accounts: List[Dict[str, Any]] = None) -> InlineKeyboardMarkup:
    """Клавиатура меню аккаунтов с пагинацией"""
    keyboard = []
    
    if accounts:
        # Вычисляем индексы для пагинации
        per_page = 5
        start = page * per_page
        end = min(start + per_page, len(accounts))
        
        # Добавляем кнопки для каждого аккаунта на текущей странице
        for i in range(start, end):
            account = accounts[i]
            status_emoji = "✅" if account["status"] == "active" else "❌"
            keyboard.append([
                InlineKeyboardButton(
                    text=f"{status_emoji} {account['email']}",
                    callback_data=f"account_info_{i}_{page}"
                ),
                InlineKeyboardButton(
                    text="❌ Удалить",
                    callback_data=f"account_del_{i}_{page}"
                )
            ])
        
        # Добавляем кнопки пагинации при необходимости
        nav_buttons = []
        if page > 0:
            nav_buttons.append(InlineKeyboardButton(
                text="◀️ Назад",
                callback_data=f"accounts_menu_{page-1}"
            ))
        
        if end < len(accounts):
            nav_buttons.append(InlineKeyboardButton(
                text="▶️ Вперед",
                callback_data=f"accounts_menu_{page+1}"
            ))
        
        if nav_buttons:
            keyboard.append(nav_buttons)
    
    # Кнопки добавления аккаунта и возврата
    keyboard.append([InlineKeyboardButton(text="➕ Добавить аккаунт", callback_data="account_add")])
    keyboard.append([InlineKeyboardButton(text="🔙 Назад", callback_data="back_main")])
    
    return InlineKeyboardMarkup(inline_keyboard=keyboard)

# --- МЕНЮ MILANUNCIOS ---
def milanuncios_menu() -> InlineKeyboardMarkup:
    """Клавиатура меню Milanuncios"""
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📝 Регистрация", callback_data="milanuncios_register")],
        [InlineKeyboardButton(text="🔍 Парсинг объявлений", callback_data="milanuncios_parse")],
        [InlineKeyboardButton(text="🔥 Прогрев аккаунта", callback_data="milanuncios_warmup")],
        [InlineKeyboardButton(text="✉️ Отправка сообщений", callback_data="milanuncios_send")],
        [InlineKeyboardButton(text="🔄 Сменить аккаунт", callback_data="milanuncios_switch")],
        [InlineKeyboardButton(text="📋 Список аккаунтов", callback_data="milanuncios_list")],
        [InlineKeyboardButton(text="🔙 Назад", callback_data="back_main")]
    ])
    return keyboard

# --- МЕНЮ ПРОКСИ ---
def proxies_menu(page: int = 0, proxies: List[str] = None) -> InlineKeyboardMarkup:
    """Клавиатура меню прокси с пагинацией"""
    keyboard = []
    
    if proxies:
        # Вычисляем индексы для пагинации
        per_page = 5
        start = page * per_page
        end = min(start + per_page, len(proxies))
        
        # Добавляем кнопки для каждого прокси на текущей странице
        for i in range(start, end):
            proxy = proxies[i]
            keyboard.append([
                # Укорачиваем отображение прокси для удобства
                InlineKeyboardButton(
                    text=f"{proxy[:25]}..." if len(proxy) > 28 else proxy,
                    callback_data=f"proxy_info_{i}_{page}"
                ),
                InlineKeyboardButton(
                    text="❌",
                    callback_data=f"proxy_del_{i}_{page}"
                )
            ])
        
        # Добавляем кнопки пагинации при необходимости
        nav_buttons = []
        if page > 0:
            nav_buttons.append(InlineKeyboardButton(
                text="◀️ Назад",
                callback_data=f"proxies_menu_{page-1}"
            ))
        
        if end < len(proxies):
            nav_buttons.append(InlineKeyboardButton(
                text="▶️ Вперед",
                callback_data=f"proxies_menu_{page+1}"
            ))
        
        if nav_buttons:
            keyboard.append(nav_buttons)
    
    # Кнопки добавления прокси и возврата
    keyboard.append([InlineKeyboardButton(text="➕ Добавить прокси", callback_data="proxy_add")])
    keyboard.append([InlineKeyboardButton(text="🔙 Назад", callback_data="back_main")])
    
    return InlineKeyboardMarkup(inline_keyboard=keyboard)

# --- МЕНЮ ШАБЛОНОВ ---
def pastes_menu(page: int = 0, pastes: List[str] = None) -> InlineKeyboardMarkup:
    """Клавиатура меню шаблонов с пагинацией"""
    keyboard = []
    
    if pastes:
        # Вычисляем индексы для пагинации
        per_page = 5
        start = page * per_page
        end = min(start + per_page, len(pastes))
        
        # Добавляем кнопки для каждого шаблона на текущей странице
        for i in range(start, end):
            paste = pastes[i]
            # Обрезаем длинные шаблоны для удобства
            display_text = paste[:25] + "..." if len(paste) > 28 else paste
            keyboard.append([
                InlineKeyboardButton(
                    text=display_text,
                    callback_data=f"paste_info_{i}_{page}"
                ),
                InlineKeyboardButton(
                    text="❌",
                    callback_data=f"paste_del_{i}_{page}"
                )
            ])
        
        # Добавляем кнопки пагинации при необходимости
        nav_buttons = []
        if page > 0:
            nav_buttons.append(InlineKeyboardButton(
                text="◀️ Назад",
                callback_data=f"pastes_menu_{page-1}"
            ))
        
        if end < len(pastes):
            nav_buttons.append(InlineKeyboardButton(
                text="▶️ Вперед",
                callback_data=f"pastes_menu_{page+1}"
            ))
        
        if nav_buttons:
            keyboard.append(nav_buttons)
    
    # Кнопки добавления шаблона и возврата
    keyboard.append([InlineKeyboardButton(text="➕ Добавить шаблон", callback_data="paste_add")])
    keyboard.append([InlineKeyboardButton(text="🔙 Назад", callback_data="back_main")])
    
    return InlineKeyboardMarkup(inline_keyboard=keyboard)

# --- МЕНЮ ВОРКЕРОВ ---
def workers_menu() -> InlineKeyboardMarkup:
    """Клавиатура меню воркеров"""
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="▶️ Запустить всех", callback_data="workers_start")],
        [InlineKeyboardButton(text="⏹️ Остановить всех", callback_data="workers_stop_all")],
        [InlineKeyboardButton(text="📋 Список воркеров", callback_data="workers_list")],
        [InlineKeyboardButton(text="🔙 Назад", callback_data="back_main")]
    ])
    return keyboard

def workers_list_menu(workers: List[str] = None) -> InlineKeyboardMarkup:
    """Клавиатура списка воркеров"""
    keyboard = []
    
    if not workers:
        workers = []
        
    # Добавляем кнопку для каждого воркера
    for i, worker_name in enumerate(workers):
        keyboard.append([InlineKeyboardButton(
            text=worker_name, 
            callback_data=f"worker_{i}_menu"
        )])
    
    # Кнопка возврата
    keyboard.append([InlineKeyboardButton(text="🔙 Назад", callback_data="workers_menu")])
    
    return InlineKeyboardMarkup(inline_keyboard=keyboard)

def worker_actions_menu(worker_id: int) -> InlineKeyboardMarkup:
    """Клавиатура действий над воркером"""
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="▶️ Запустить", callback_data=f"worker_{worker_id}_start")],
        [InlineKeyboardButton(text="⏹️ Остановить", callback_data=f"worker_{worker_id}_stop")],
        [InlineKeyboardButton(text="📊 Статус", callback_data=f"worker_{worker_id}_status")],
        [InlineKeyboardButton(text="📝 Логи", callback_data=f"worker_{worker_id}_logs")],
        [InlineKeyboardButton(text="❌ Удалить", callback_data=f"worker_{worker_id}_delete")],
        [InlineKeyboardButton(text="🔙 Назад", callback_data="workers_list")]
    ])
    return keyboard

# --- МЕНЮ НАСТРОЕК ---
def settings_menu() -> InlineKeyboardMarkup:
    """Клавиатура меню настроек"""
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🔄 Headless режим", callback_data="settings_headless")],
        [InlineKeyboardButton(text="🔄 Лимит сообщений", callback_data="settings_limit")],
        [InlineKeyboardButton(text="🔄 Интервал сообщений", callback_data="settings_interval")],
        [InlineKeyboardButton(text="🔄 Автосмена IP", callback_data="settings_auto_ip")],
        [InlineKeyboardButton(text="🔙 Назад", callback_data="back_main")]
    ])
    return keyboard