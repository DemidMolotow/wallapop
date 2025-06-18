import asyncio
import random
import os
import traceback
import time
from messaging.sender import send_message
from parser import parse_wallapop_ads
from mail_manager.manager import load_email_accounts, connect_imap, find_verification_code, get_imap_server
from proxy_manager.manager import get_random_proxy
from utils import load_lines, random_user_agent
from autodetect_profiles.profiles import ProfileManager
from warming_scenarios.warmer import human_actions
from config import EMAIL_LIST_PATH, WALLAPOP_READY_PATH, PASTES_PATH, USER_AGENTS

from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

CURRENT_STATUS = {"stage": "Ожидание запуска", "progress": "", "stopped": False, "status_msg_id": None}

def reset_status():
    print("[reset_status] Сброс статуса рассылки")
    CURRENT_STATUS.update({"stage": "Ожидание запуска", "progress": "", "stopped": False, "status_msg_id": None})

def set_status(stage=None, progress=None):
    if stage is not None:
        CURRENT_STATUS["stage"] = stage
    if progress is not None:
        CURRENT_STATUS["progress"] = progress
    print(f"[set_status] {CURRENT_STATUS}")

def stop_worker():
    print("[stop_worker] Остановка рассылки")
    CURRENT_STATUS["stopped"] = True

async def register_account(email, password, proxy):
    print(f"[register_account] Старт регистрации: {email}")
    profile_mgr = ProfileManager()
    ua = random_user_agent(USER_AGENTS)
    timing = {}
    t0 = time.time()
    driver = profile_mgr.open_browser(proxy=proxy, user_agent=ua, headless=True)
    timing['open_browser'] = time.time() - t0

    try:
        t1 = time.time()
        await human_actions(driver)
        timing['human_actions_1'] = time.time() - t1

        t2 = time.time()
        driver.get("https://es.wallapop.com/register")
        await asyncio.sleep(2)
        timing['open_register_page'] = time.time() - t2

        t3 = time.time()
        WebDriverWait(driver, 20).until(EC.presence_of_element_located((By.XPATH, "//input[@type='email']")))
        email_box = driver.find_element("xpath", "//input[@type='email']")
        email_box.send_keys(email)
        timing['fill_email'] = time.time() - t3

        t4 = time.time()
        driver.find_element("xpath", "//button[contains(.,'Continuar') or contains(.,'Continue')]").click()
        await asyncio.sleep(2)
        timing['press_continue'] = time.time() - t4

        t5 = time.time()
        imap_server = get_imap_server(email)
        with connect_imap(email, password, imap_server) as mail:
            code = find_verification_code(mail, subject_filter="Wallapop")
        timing['get_code_from_mail'] = time.time() - t5

        if not code:
            print(f"[register_account ERROR] Код подтверждения не найден для {email}")
            raise Exception("Не найден код подтверждения")

        t6 = time.time()
        WebDriverWait(driver, 20).until(EC.presence_of_element_located((By.XPATH, "//input[@type='text']")))
        code_box = driver.find_element("xpath", "//input[@type='text']")
        code_box.send_keys(code)
        driver.find_element("xpath", "//button[contains(.,'Confirmar') or contains(.,'Confirm')]").click()
        await asyncio.sleep(2)
        timing['fill_code_and_confirm'] = time.time() - t6

        t7 = time.time()
        await human_actions(driver)
        timing['human_actions_2'] = time.time() - t7

        print(f"[register_account] Регистрация завершена для {email}")
        print("[register_account] Этапы и время:")
        for k, v in timing.items():
            print(f"  {k}: {v:.2f} сек")
        return driver
    except Exception as ex:
        print(f"[register_account ERROR] {email}: {ex}")
        traceback.print_exc()

        try:
            # Сохраняем скриншот и страницу для анализа ошибок
            driver.save_screenshot(f"register_error_{int(time.time())}.png")
            with open(f"register_error_{int(time.time())}.html", "w", encoding='utf-8') as f:
                f.write(driver.page_source)
        except Exception:
            pass

        try:
            driver.quit()
        except:
            pass
        raise

async def authorize_account(email, password, proxy):
    print(f"[authorize_account] Авторизация: {email}")
    profile_mgr = ProfileManager()
    ua = random_user_agent(USER_AGENTS)
    timing = {}
    t0 = time.time()
    driver = profile_mgr.open_browser(proxy=proxy, user_agent=ua, headless=True)
    timing['open_browser'] = time.time() - t0

    try:
        t1 = time.time()
        driver.get("https://es.wallapop.com/login")
        await asyncio.sleep(2)
        timing['open_login_page'] = time.time() - t1

        t2 = time.time()
        try:
            WebDriverWait(driver, 20).until(EC.presence_of_element_located((By.XPATH, "//input[@type='email']")))
            email_box = driver.find_element("xpath", "//input[@type='email']")
        except Exception as e:
            print(f"[authorize_account ERROR] {email}: Не найдено поле email")
            traceback.print_exc()
            try:
                driver.save_screenshot(f"login_error_{int(time.time())}.png")
                with open(f"login_error_{int(time.time())}.html", "w", encoding='utf-8') as f:
                    f.write(driver.page_source)
            except Exception:
                pass
            raise Exception("Не найдено поле ввода email на странице входа!")
        email_box.clear()
        email_box.send_keys(email)
        timing['fill_email'] = time.time() - t2

        t3 = time.time()
        driver.find_element("xpath", "//button[contains(.,'Continuar') or contains(.,'Continue')]").click()
        await asyncio.sleep(2)
        timing['press_continue'] = time.time() - t3

        t4 = time.time()
        try:
            WebDriverWait(driver, 20).until(EC.presence_of_element_located((By.XPATH, "//input[@type='password']")))
            pass_box = driver.find_element("xpath", "//input[@type='password']")
        except Exception as e:
            print(f"[authorize_account ERROR] {email}: Не найдено поле пароля")
            traceback.print_exc()
            try:
                driver.save_screenshot(f"login_pass_error_{int(time.time())}.png")
                with open(f"login_pass_error_{int(time.time())}.html", "w", encoding='utf-8') as f:
                    f.write(driver.page_source)
            except Exception:
                pass
            raise Exception("Не найдено поле ввода пароля после ввода email!")
        pass_box.clear()
        pass_box.send_keys(password)
        timing['fill_password'] = time.time() - t4

        t5 = time.time()
        driver.find_element("xpath", "//button[contains(.,'Entrar') or contains(.,'Login') or contains(.,'Sign In')]").click()
        await asyncio.sleep(3)
        timing['press_login'] = time.time() - t5

        t6 = time.time()
        await human_actions(driver)
        timing['human_actions'] = time.time() - t6

        page_source = driver.page_source
        if "contraseña" in page_source.lower() and ("incorrecta" in page_source.lower() or "incorrect" in page_source.lower()):
            print(f"[authorize_account ERROR] {email}: Неверный пароль!")
            raise Exception("Введён неверный пароль!")
        if "captcha" in page_source.lower():
            print(f"[authorize_account ERROR] {email}: Капча!")
            raise Exception("Требуется решить капчу. Авторизация невозможна.")

        print(f"[authorize_account] Успешная авторизация: {email}")
        print("[authorize_account] Этапы и время:")
        for k, v in timing.items():
            print(f"  {k}: {v:.2f} сек")
        return driver
    except Exception as ex:
        print(f"[authorize_account ERROR] {email}: {ex}")
        traceback.print_exc()
        try:
            driver.save_screenshot(f"login_fatal_error_{int(time.time())}.png")
            with open(f"login_fatal_error_{int(time.time())}.html", "w", encoding='utf-8') as f:
                f.write(driver.page_source)
        except Exception:
            pass
        try:
            driver.quit()
        except:
            pass
        raise

# Остальной код без изменений...
# (process_accounts, main_worker и т.д.)
