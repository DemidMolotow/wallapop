from playwright.sync_api import sync_playwright

def warmup_account():
    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=False)
            context = browser.new_context(
                user_agent='Mozilla/5.0 (Linux; Android 10; Mobile; rv:89.0) Gecko/89.0 Firefox/89.0',
                viewport={'width': 360, 'height': 640}
            )
            page = context.new_page()
            page.goto('https://www.milanuncios.com')

            # Эмуляция активности
            page.click('.random-ad')
            page.click('.favorite-button')
            browser.close()
        return "Прогрев завершён"
    except Exception as e:
        print(f"Ошибка прогрева: {e}")
        return False