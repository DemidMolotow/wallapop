import asyncio
from autodetect_profiles.profiles import ProfileManager
from warming_scenarios.warmer import human_actions
from parser import parse_wallapop_ads
from messaging.sender import send_message
from mail_manager.manager import load_email_accounts, connect_imap, find_verification_code, get_imap_server
from proxy_manager.manager import get_random_proxy
from utils import load_lines, random_user_agent
from db.stats import inc_stat
from config import PASTES_PATH, EMAIL_LIST_PATH, USER_AGENTS

async def register_and_send(email, password, proxy, pastes, queries):
    profile_mgr = ProfileManager()
    for query in queries:
        ads = parse_wallapop_ads(query)
        if not ads:
            continue
        for ad in ads:
            ua = profile_mgr.get_new_user_agent()
            driver = profile_mgr.open_browser(proxy=proxy, user_agent=ua, headless=True)
            try:
                await human_actions(driver)
                # Регистрация: переход на страницу, заполнение формы, получение кода
                driver.get("https://es.wallapop.com/register")
                await asyncio.sleep(2)
                email_box = driver.find_element("xpath", "//input[@type='email']")
                email_box.send_keys(email)
                driver.find_element("xpath", "//button[contains(.,'Continuar') or contains(.,'Continue')]").click()
                await asyncio.sleep(2)
                # Ждём код на почте
                imap_server = get_imap_server(email)
                with connect_imap(email, password, imap_server) as mail:
                    code = find_verification_code(mail, subject_filter="Wallapop")
                if not code:
                    inc_stat("errors")
                    continue
                code_box = driver.find_element("xpath", "//input[@type='text']")
                code_box.send_keys(code)
                driver.find_element("xpath", "//button[contains(.,'Confirmar') or contains(.,'Confirm')]").click()
                await asyncio.sleep(2)
                # Прогреваем профиль
                await human_actions(driver)
                # Отправляем сообщение
                message_text = random.choice(pastes)
                ok = await send_message(driver, ad["url"], message_text)
                if ok:
                    inc_stat("messages_sent")
                driver.quit()
            except Exception as ex:
                print(f"Ошибка при работе с объявлением: {ex}")
                try:
                    driver.quit()
                except:
                    pass
                inc_stat("errors")

async def main_worker():
    emails = load_email_accounts(EMAIL_LIST_PATH)
    pastes = load_lines(PASTES_PATH)
    queries = ["iPhone", "Nike", "Xiaomi"]  # Пример ключевых слов, дополни своими
    for acc in emails:
        proxy = get_random_proxy()
        await register_and_send(acc["email"], acc["password"], proxy, pastes, queries)