from playwright.async_api import async_playwright

async def search_ads(query=None, max_results=10, domain="es"):
    url = f"https://{domain}.wallapop.com/search"
    if query:
        url += f"?kws={query}"
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page()
        await page.goto(url)
        await page.wait_for_selector('article[data-testid="item-card"]', timeout=10000)
        cards = await page.query_selector_all('article[data-testid="item-card"]')
        ads = []
        for card in cards[:max_results]:
            title_el = await card.query_selector('p[data-testid="item-card-title"]')
            price_el = await card.query_selector('span[data-testid="item-card-price"]')
            link_el = await card.query_selector('a[href]')
            if title_el and price_el and link_el:
                href = await link_el.get_attribute("href")
                if href and not href.startswith("http"):
                    href = f"https://{domain}.wallapop.com{href}"
                ads.append({
                    "title": await title_el.inner_text(),
                    "price": await price_el.inner_text(),
                    "url": href
                })
        await browser.close()
        return ads
