from playwright.sync_api import sync_playwright
from aiogram import Bot
from config import API_TOKEN, ADMIN_CHAT_ID  # Импорт из config.py

bot = Bot(token=API_TOKEN)

# Лимит отправленных сообщений
MESSAGE_LIMIT = 20
message_count = 0

def send_message():
    global message_count
    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=False)
            context = browser.new_context(
                user_agent='Mozilla/5.0 (Linux; Android 10; Mobile; rv:89.0 Firefox/89.0',
                viewport={'width': 360, 'height': 640}
            )
            page = context.new_page()
            page.goto('https://www.milanuncios.com/messages')

            # Проверка лимита сообщений
            if message_count >= MESSAGE_LIMIT:
                bot.send_message(ADMIN_CHAT_ID, "Лимит сообщений достигнут. Требуется смена аккаунта.")
                return False, True  # Возвращаем флаг, что лимит достигнут

            # Отправка сообщения
            page.fill('textarea[name="message"]', 'Здравствуйте! Интересует ваш товар.')
            page.click('button[type="submit"]')
            message_count += 1  # Увеличиваем счётчик

            # Логирование успешной отправки
            bot.send_message(ADMIN_CHAT_ID, f"Сообщение отправлено. Всего отправлено: {message_count}.")
            browser.close()
        return True, False  # Сообщения успешно отправлены, лимит не достигнут
    except Exception as e:
        print(f"Ошибка отправки сообщений: {e}")
        bot.send_message(ADMIN_CHAT_ID, f"Ошибка отправки сообщений: {e}")
        return False, False  # Ошибка отправки сообщений
