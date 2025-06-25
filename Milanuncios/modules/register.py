from playwright.sync_api import sync_playwright
from aiogram import Bot
from config import API_TOKEN, ADMIN_CHAT_ID  # Импорт из config.py

bot = Bot(token=API_TOKEN)

def register_account():
    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=False)
            context = browser.new_context(
                user_agent='Mozilla/5.0 (Linux; Android 10; Mobile; rv:89.0) Gecko/89.0 Firefox/89.0',
                viewport={'width': 360, 'height': 640}
            )
            page = context.new_page()
            page.goto('https://www.milanuncios.com/registro')

            # Вход через Google
            page.click('button[data-provider="google"]')  # Кнопка входа через Google
            google_page = context.wait_for_event("page")
            google_page.fill('input[type="email"]', 'your_google_email@gmail.com')
            google_page.click('button[type="submit"]')
            google_page.fill('input[type="password"]', 'your_google_password')
            google_page.click('button[type="submit"]')

            # Ожидание капчи или подтверждения
            if page.locator('img.captcha').is_visible():
                # Отправка капчи в Telegram
                captcha_image = page.locator('img.captcha').screenshot()
                bot.send_photo(ADMIN_CHAT_ID, captcha_image, caption="Введите капчу:")
                
                # Здесь можно реализовать ожидание ответа от пользователя через Telegram
                captcha_solution = input("Введите решение капчи из Telegram: ")
                page.fill('input[name="captcha"]', captcha_solution)
                page.click('button[type="submit"]')

            # Проверка успешной регистрации
            success_text = page.locator('.success-message').inner_text()
            browser.close()
            return "Аккаунт зарегистрирован" in success_text
    except Exception as e:
        print(f"Ошибка регистрации: {e}")
        return False
