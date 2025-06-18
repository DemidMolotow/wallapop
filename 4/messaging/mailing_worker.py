import asyncio
from playwright.async_api import async_playwright

ACCOUNTS_FILE = "wallapop_ready.txt"

# Глобальные переменные для статуса и остановки
_worker_running = False
_stop_event = asyncio.Event()
_status_info = {
    "stage": "Не начато",
    "progress": ""
}

def set_status(stage, progress=""):
    global _status_info
    _status_info["stage"] = stage
    _status_info["progress"] = progress
    print(f"[STATUS] Этап: {stage} | {progress}")

def get_current_status():
    return _status_info.copy()

def stop_worker():
    global _stop_event
    _stop_event.set()
    set_status("Остановлено пользователем", "")
    return "Остановка рассылки инициирована"

async def maybe_close_cookies(page):
    """Пытается закрыть баннер cookies на любой стадии."""
    try:
        await page.click("button:has-text('Aceptar todo')", timeout=2000)
        print("[cookies] Cookie баннер 'Aceptar todo' нажат")
        await asyncio.sleep(0.3)
    except Exception:
        pass  # Не было баннера — идем дальше

async def authorize_account(page, email, password):
    set_status("Авторизация", f"Акаунт: {email}")
    print(f"[authorize_account] Авторизация: {email}")
    await page.goto("https://es.wallapop.com/login", timeout=60000)
    await maybe_close_cookies(page)

    # Всегда кликаем по 'Iniciar sesión'
    try:
        await page.wait_for_selector("text=Iniciar sesión", timeout=6000)
        await maybe_close_cookies(page)
        await page.click("text=Iniciar sesión")
        print("[iniciar_sesion] Клик по 'Iniciar sesión'")
        await asyncio.sleep(1)
        await maybe_close_cookies(page)
    except Exception as e:
        print(f"[iniciar_sesion ERROR] Кнопка 'Iniciar sesión' не найдена: {e}")
        set_status("Ошибка", f"Нет кнопки входа для {email}")
        return False

    # Ввод email
    try:
        await page.wait_for_selector("input[type='email']", timeout=8000)
        await maybe_close_cookies(page)
        await page.fill("input[type='email']", email)
        await maybe_close_cookies(page)
        print("[authorize_account] Email введён")
        await asyncio.sleep(0.5)
    except Exception as e:
        print(f"[authorize_account ERROR] Не найдено поле ввода email или другая ошибка (email): {e}")
        html = await page.content()
        with open(f"login_error_{int(asyncio.get_event_loop().time())}.html", "w", encoding="utf-8") as f:
            f.write(html)
        set_status("Ошибка", f"Акаунт {email}: {str(e)}")
        return False

    # Ввод пароля
    try:
        await page.wait_for_selector("input[type='password']", timeout=8000)
        await maybe_close_cookies(page)
        await page.fill("input[type='password']", password)
        print("[authorize_account] Пароль введён")
        await asyncio.sleep(0.5)
        await maybe_close_cookies(page)
    except Exception as e:
        print(f"[authorize_account ERROR] Не удалось найти или заполнить поле пароля: {e}")
        html = await page.content()
        with open(f"login_error_{int(asyncio.get_event_loop().time())}.html", "w", encoding="utf-8") as f:
            f.write(html)
        set_status("Ошибка", f"Акаунт {email}: {str(e)}")
        return False

    # Ожидание прохождения капчи вручную
    print("ОЖИДАНИЕ: Решите капчу вручную в открытом окне браузера и нажмите Enter в консоли, чтобы продолжить.")
    input("Нажмите Enter после прохождения reCAPTCHA...")

    # Клик по кнопке входа
    try:
        await page.click("button:has-text('Acceder a Wallapop')")
        print("[authorize_account] Клик по входу")
        await asyncio.sleep(2)
        await maybe_close_cookies(page)
        set_status("Авторизация успешна", f"Акаунт: {email}")
        return True
    except Exception as e:
        print(f"[authorize_account ERROR] Не удалось кликнуть вход или другая ошибка (submit): {e}")
        html = await page.content()
        with open(f"login_error_{int(asyncio.get_event_loop().time())}.html", "w", encoding="utf-8") as f:
            f.write(html)
        set_status("Ошибка", f"Акаунт {email}: {str(e)}")
        return False

async def process_accounts(status_update_cb=None):
    global _worker_running
    accounts = []
    try:
        with open(ACCOUNTS_FILE, encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line or ';' not in line: continue
                email, password = line.split(";")
                accounts.append({"email": email, "password": password})
    except Exception as e:
        print(f"[load_email_accounts ERROR] {e}")
        set_status("Ошибка загрузки аккаунтов", str(e))
        if status_update_cb:
            await status_update_cb()
        return

    print(f"[load_email_accounts] Загружено аккаунтов: {len(accounts)} из {ACCOUNTS_FILE}")
    set_status("Загружено аккаунтов", f"{len(accounts)}")
    if status_update_cb:
        await status_update_cb()
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=False)
        context = await browser.new_context()
        page = await context.new_page()
        for idx, acc in enumerate(accounts, 1):
            if _stop_event.is_set():
                print("[process_accounts] Получен сигнал остановки. Прерывание рассылки.")
                set_status("Остановлено пользователем", f"Обработано: {idx-1}/{len(accounts)}")
                if status_update_cb:
                    await status_update_cb()
                break
            set_status("Авторизация", f"{idx}/{len(accounts)} — {acc['email']}")
            if status_update_cb:
                await status_update_cb()
            print(f"[set_status] Авторизация аккаунта {acc['email']}")
            ok = await authorize_account(page, acc["email"], acc["password"])
            if not ok:
                print(f"[process_accounts ERROR] {acc['email']}: Не удалось авторизоваться")
            else:
                print(f"[process_accounts] {acc['email']} успешно авторизован")
            set_status("Прогресс", f"{idx}/{len(accounts)}")
            if status_update_cb:
                await status_update_cb()
        await browser.close()
    _worker_running = False
    if not _stop_event.is_set():
        set_status("Рассылка завершена", f"Всего: {len(accounts)}")
        if status_update_cb:
            await status_update_cb()

async def main_worker(status_update_cb=None):
    global _worker_running, _stop_event
    if _worker_running:
        print("[main_worker] Уже выполняется рассылка.")
        return
    _worker_running = True
    _stop_event.clear()
    set_status("Рассылка начата", "")
    if status_update_cb:
        await status_update_cb()
    await process_accounts(status_update_cb=status_update_cb)

# Пример интеграции с aiogram:
# from messaging.mailing_worker import main_worker, get_current_status, stop_worker
# @dp.message_handler(commands=['start_mailing'])
# async def start_mailing_handler(message: types.Message):
#     asyncio.create_task(main_worker())  # НЕ передавайте status_update_cb если не нужно логировать в бота!
#     await message.answer("Рассылка запущена!")
# @dp.message_handler(commands=['status'])
# async def status_handler(message: types.Message):
#     status = get_current_status()
#     text = f"Статус рассылки:\nЭтап: {status['stage']}\n{status['progress']}"
#     await message.answer(text)
# @dp.message_handler(commands=['stop_mailing'])
# async def stop_handler(message: types.Message):
#     stop_worker()
#     await message.answer("Рассылка будет остановлена.")

if __name__ == "__main__":
    print("Старт рассылки аккаунтов wallapop через main_worker()")
    asyncio.run(main_worker())
