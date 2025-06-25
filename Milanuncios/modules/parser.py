from playwright.sync_api import sync_playwright
from aiogram import Bot
from config import API_TOKEN, ADMIN_CHAT_ID  # Импорт из config.py

bot = Bot(token=API_TOKEN)

def parse_ads():
    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            context = browser.new_context(
                user_agent='Mozilla/5.0 (Linux; Android 10; Mobile; rv:89.0) Gecko/89.0 Firefox/89.0',
                viewport={'width': 360, 'height': 640}
            )
            page = context.new_page()
            page.goto('https://www.milanuncios.com')

            # Ожидание загрузки динамического контента
            page.wait_for_selector('.ad-item')

            ads = []
            for ad in page.query_selector_all('.ad-item'):
                title = ad.query_selector('.ad-title').inner_text().strip() if ad.query_selector('.ad-title') else "Нет заголовка"
                price = ad.query_selector('.ad-price').inner_text().strip() if ad.query_selector('.ad-price') else "Цена не указана"
                location = ad.query_selector('.ad-location').inner_text().strip() if ad.query_selector('.ad-location') else "Локация не указана"
                ads.append({
                    'title': title,
                    'price': price,
                    'location': location,
                })

            browser.close()

            # Логирование успешного парсинга
            bot.send_message(ADMIN_CHAT_ID, f"Парсинг завершён. Найдено {len(ads)} объявлений.")
            return ads
    except Exception as e:
        # Логирование ошибок
        bot.send_message(ADMIN_CHAT_ID, f"Ошибка парсинга: {e}")
        print(f"Ошибка парсинга: {e}")
        return []
