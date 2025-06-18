import asyncio
from playwright.async_api import Page

async def send_message(page: Page, ad_url: str, message_text: str):
    try:
        await page.goto(ad_url, timeout=60000)
        await asyncio.sleep(2)
        # Открыть чат/контакты
        chat_btn = await page.query_selector(
            "//button[contains(.,'Chat') or contains(.,'Contactar') or contains(.,'Contact')]"
        )
        if chat_btn:
            await chat_btn.click()
            await asyncio.sleep(1)
            msg_box = await page.query_selector("//textarea")
            if msg_box:
                await msg_box.fill(message_text)
                send_btn = await page.query_selector(
                    "//button[contains(.,'Send') or contains(.,'Enviar') or contains(.,'Отправить')]"
                )
                if send_btn:
                    await send_btn.click()
                    await asyncio.sleep(2)
                    return True
        return False
    except Exception as ex:
        # Можно добавить логирование ошибок
        return False
