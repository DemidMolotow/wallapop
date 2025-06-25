from playwright.sync_api import sync_playwright
import json

def find_selectors(url):
    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=False)
            context = browser.new_context(
                user_agent='Mozilla/5.0 (Linux; Android 10; Mobile; rv:89.0) Gecko/89.0 Firefox/89.0',
                viewport={'width': 360, 'height': 640}
            )
            page = context.new_page()
            page.goto(url)

            # Поиск форм на странице
            forms = page.locator('form')
            selectors = {}
            for i, form in enumerate(forms.element_handles()):
                inputs = form.query_selector_all('input')
                buttons = form.query_selector_all('button')
                
                form_selectors = {}
                # Извлечение текстовых полей
                for input in inputs:
                    placeholder = input.get_attribute('placeholder')
                    name = input.get_attribute('name')
                    if placeholder or name:
                        form_selectors[f"input_{placeholder or name}"] = input.locator()

                # Извлечение кнопок
                for button in buttons:
                    text = button.inner_text()
                    if text:
                        form_selectors[f"button_{text}"] = button.locator()

                selectors[f"form_{i}"] = form_selectors

            browser.close()

            # Сохранение селекторов в JSON
            with open('selectors.json', 'w') as f:
                json.dump(selectors, f, indent=4)
            
            return selectors
    except Exception as e:
        print(f"Ошибка поиска селекторов: {e}")
        return {}