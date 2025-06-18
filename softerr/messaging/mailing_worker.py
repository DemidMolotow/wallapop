import asyncio
import random
from messaging.sender import send_message
from parser import parse_wallapop_ads
from mail_manager.manager import load_email_accounts, connect_imap, find_verification_code, get_imap_server
from proxy_manager.manager import get_random_proxy
from utils import load_lines, random_user_agent
from autodetect_profiles.profiles import ProfileManager
from warming_scenarios.warmer import human_actions
from config import EMAIL_LIST_PATH, EMAIL_READY_PATH, PASTES_PATH, USER_AGENTS

# Глобальные переменные для статуса и остановки
CURRENT_STATUS = {"stage": "Ожидание запуска", "progress": "", "stopped": False, "status_msg_id": None}

def reset_status():
    CURRENT_STATUS.update({"stage": "Ожидание запуска", "progress": "", "stopped": False, "status_msg_id": None})

def set_status(stage=None, progress=None):
    if stage is not None:
        CURRENT_STATUS["stage"] = stage
    if progress is not None:
        CURRENT_STATUS["progress"] = progress

def stop_worker():
    CURRENT_STATUS["stopped"] = True

async def register_account(email, password, proxy):
    # Реальная регистрация аккаунта Wallapop (пример)
    profile_mgr = ProfileManager()
    ua = random_user_agent(USER_AGENTS)
    driver = profile_mgr.open_browser(proxy=proxy, user_agent=ua, headless=True)
    try:
        await human_actions(driver)
        driver.get("https://es.wallapop.com/register")
        await asyncio.sleep(2)
        email_box = driver.find_element("xpath", "//input[@type='email']")
        email_box.send_keys(email)
        driver.find_element("xpath", "//button[contains(.,'Continuar') or contains(.,'Continue')]").click()
        await asyncio.sleep(2)
        imap_server = get_imap_server(email)
        with connect_imap(email, password, imap_server) as mail:
            code = find_verification_code(mail, subject_filter="Wallapop")
        if not code:
            raise Exception("Не найден код подтверждения")
        code_box = driver.find_element("xpath", "//input[@type='text']")
        code_box.send_keys(code)
        driver.find_element("xpath", "//button[contains(.,'Confirmar') or contains(.,'Confirm')]").click()
        await asyncio.sleep(2)
        await human_actions(driver)
        return driver
    except Exception as ex:
        try:
            driver.quit()
        except:
            pass
        raise ex

async def authorize_account(email, password, proxy):
    # Реальная авторизация без регистрации (пример)
    profile_mgr = ProfileManager()
    ua = random_user_agent(USER_AGENTS)
    driver = profile_mgr.open_browser(proxy=proxy, user_agent=ua, headless=True)
    try:
        driver.get("https://es.wallapop.com/login")
        await asyncio.sleep(2)
        email_box = driver.find_element("xpath", "//input[@type='email']")
        email_box.send_keys(email)
        driver.find_element("xpath", "//button[contains(.,'Continuar') or contains(.,'Continue')]").click()
        await asyncio.sleep(2)
        pass_box = driver.find_element("xpath", "//input[@type='password']")
        pass_box.send_keys(password)
        driver.find_element("xpath", "//button[contains(.,'Entrar') or contains(.,'Login') or contains(.,'Sign In')]").click()
        await asyncio.sleep(2)
        await human_actions(driver)
        return driver
    except Exception as ex:
        try:
            driver.quit()
        except:
            pass
        raise ex

async def send_messages_with_driver(driver, pastes, queries):
    sent_cnt = 0
    for query in queries:
        if CURRENT_STATUS["stopped"]:
            break
        ads = parse_wallapop_ads(query)
        if not ads:
            continue
        for ad in ads:
            if CURRENT_STATUS["stopped"]:
                break
            message_text = random.choice(pastes)
            ok = await send_message(driver, ad["url"], message_text)
            if ok:
                sent_cnt += 1
            await asyncio.sleep(random.uniform(2.5, 5))
    return sent_cnt

async def process_accounts(email_path, is_new, pastes, queries, status_update_cb):
    accounts = load_email_accounts(email_path)
    total = len(accounts)
    sent_total = 0
    for idx, acc in enumerate(accounts, 1):
        if CURRENT_STATUS["stopped"]:
            break
        proxy = get_random_proxy()
        try:
            set_status(stage=f"{'Регистрация' if is_new else 'Авторизация'} аккаунта ({idx}/{total})")
            await status_update_cb()
            driver = await (register_account if is_new else authorize_account)(acc["email"], acc["password"], proxy)
            set_status(stage="Рассылка сообщений", progress=f"Аккаунт {acc['email']}")
            await status_update_cb()
            sent = await send_messages_with_driver(driver, pastes, queries)
            sent_total += sent
            driver.quit()
        except Exception as ex:
            set_status(stage="Ошибка", progress=str(ex))
            await status_update_cb()
            continue
        set_status(progress=f"Аккаунтов обработано: {idx}/{total}, сообщений отправлено: {sent_total}")
        await status_update_cb()
    return sent_total

async def main_worker(pastes_path=PASTES_PATH, queries=None, status_update_cb=lambda: None):
    reset_status()
    pastes = load_lines(pastes_path)
    if not queries:
        queries = ["iPhone", "Nike", "Xiaomi"]
    # Сначала регистрируем новые аккаунты (если файл есть)
    try:
        sent_reg = await process_accounts("emails_new.txt", True, pastes, queries, status_update_cb)
    except FileNotFoundError:
        sent_reg = 0
    # Потом работаем с готовыми аккаунтами
    sent_auth = await process_accounts(EMAIL_LIST_PATH, False, pastes, queries, status_update_cb)
    set_status(stage="Рассылка завершена", progress=f"Всего сообщений отправлено: {sent_reg + sent_auth}")
    await status_update_cb()
    return sent_reg + sent_auth

def get_current_status():
    return dict(CURRENT_STATUS)