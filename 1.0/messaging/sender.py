import asyncio

async def send_message(driver, ad_url, message_text):
    try:
        driver.get(ad_url)
        await asyncio.sleep(2)
        chat_btn = driver.find_element("xpath", "//button[contains(.,'Chat') or contains(.,'Contactar') or contains(.,'Contact')]")
        chat_btn.click()
        await asyncio.sleep(1)
        msg_box = driver.find_element("xpath", "//textarea")
        msg_box.send_keys(message_text)
        send_btn = driver.find_element("xpath", "//button[contains(.,'Send') or contains(.,'Enviar') or contains(.,'Отправить')]")
        send_btn.click()
        await asyncio.sleep(2)
        return True
    except Exception as ex:
        # Можно добавить логирование ошибок
        return False