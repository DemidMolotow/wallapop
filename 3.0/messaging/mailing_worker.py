import asyncio
from playwright.async_api import async_playwright

ACCOUNTS_FILE = "wallapop_ready.txt"

async def authorize_account(page, email, password):
    print(f"[authorize_account] Авторизация: {email}")
    await page.goto("https://es.wallapop.com/login", timeout=60000)
    # Cookie баннер
    try:
        await page.click("button:has-text('Aceptar todo')", timeout=3000)
        print("[cookies] Cookie баннер 'Aceptar todo' нажат")
    except Exception:
        print("[cookies] Cookie баннер не найден или уже закрыт")
    # Клик по 'Iniciar sesión'
    try:
        await page.click("text=Iniciar sesión", timeout=5000)
        print("[iniciar_sesion] Клик по 'Iniciar sesión'")
    except Exception as e:
        print(f"[iniciar_sesion ERROR] Кнопка не найдена: {e}")
        return False

    # Ждём появления поля ввода email
    try:
        await page.wait_for_selector("input[type='email']", timeout=8000)
        await page.fill("input[type='email']", email)
        await page.click("button:has-text('Continuar')")
        print("[authorize_account] Email введён")
        await page.wait_for_selector("input[type='password']", timeout=8000)
        await page.fill("input[type='password']", password)
        await page.click("button:has-text('Entrar')")
        print("[authorize_account] Пароль введён, вход...")
        await asyncio.sleep(2)
        return True
    except Exception as e:
        print(f"[authorize_account ERROR] Не найдено поле ввода email или другая ошибка: {e}")
        # Сохраним html для отладки
        html = await page.content()
        with open(f"login_error_{int(asyncio.get_event_loop().time())}.html", "w", encoding="utf-8") as f:
            f.write(html)
        return False

async def process_accounts():
    accounts = []
    try:
        with open(ACCOUNTS_FILE, encoding="utf-8") as f:
            for line in f:
                email, password = line.strip().split(";")
                accounts.append({"email": email, "password": password})
    except Exception as e:
        print(f"[load_email_accounts ERROR] {e}")
        return

    print(f"[load_email_accounts] Загружено аккаунтов: {len(accounts)} из {ACCOUNTS_FILE}")
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=False)
        context = await browser.new_context()
        page = await context.new_page()
        for acc in accounts:
            print(f"[set_status] Авторизация аккаунта {acc['email']}")
            ok = await authorize_account(page, acc["email"], acc["password"])
            if not ok:
                print(f"[process_accounts ERROR] {acc['email']}: Не удалось авторизоваться")
            else:
                print(f"[process_accounts] {acc['email']} успешно авторизован")
        await browser.close()
