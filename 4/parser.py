import asyncio
from playwright.async_api import async_playwright

async def parse_wallapop_ads(query, page=1):
    url = f"https://es.wallapop.com/app/search?keywords={query}&page={page}"
    ads = []
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context()
        page_obj = await context.new_page()
        await page_obj.goto(url, timeout=60000)
        # Ждем загрузки данных, можно добавить ожидание по селектору если потребуется
        content = await page_obj.content()
        # Wallapop может отдавать данные через JS, поэтому предпочтительно взаимодействовать через XHR/fetch
        # Но если API отдает JSON, проще использовать fetch внутри браузера:
        ads_data = await page_obj.evaluate(
            """async (url) => {
                const resp = await fetch(url, {headers: {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/120.0.0.0 Safari/537.36"}});
                if (!resp.ok) return [];
                const data = await resp.json();
                return data.search_objects || [];
            }""", url
        )
        for item in ads_data:
            ads.append({
                "id": item.get("id"),
                "title": item.get("title"),
                "price": item.get("price"),
                "url": f"https://es.wallapop.com/item/{item.get('id')}",
            })
        await browser.close()
    return ads

# Пример использования:
# asyncio.run(parse_wallapop_ads("iphone"))
