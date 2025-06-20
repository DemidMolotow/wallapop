import asyncio
import re
import json

class WallapopParser:
    def __init__(self, domain="es"):
        self.base_url = f"https://{domain}.wallapop.com"
        self.domain = domain

    async def parse_stream(self, max_pages=1):
        from playwright.async_api import async_playwright

        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True)
            context = await browser.new_context(
                user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                           "AppleWebKit/537.36 (KHTML, like Gecko) "
                           "Chrome/124.0.0.0 Safari/537.36"
            )
            try:
                for page_num in range(1, max_pages + 1):
                    url = f"{self.base_url}/"
                    page = await context.new_page()
                    await page.goto(url, wait_until="domcontentloaded")
                    try:
                        await page.wait_for_selector('a[href^="/item/"]', timeout=15000)
                    except Exception:
                        print(f"Карточки не найдены на странице {page_num}")
                        await page.close()
                        continue
                    cards = await page.query_selector_all('a[href^="/item/"]')
                    print(f"Парсим страницу {page_num}, найдено карточек: {len(cards)}")
                    for card in cards:
                        ad_url = await card.get_attribute("href")
                        if not ad_url:
                            continue
                        if not ad_url.startswith("http"):
                            ad_url = self.base_url + ad_url
                        ad = await self.parse_listing_page(context, ad_url)
                        print(f"Нашёл объявление: {ad.get('title') if ad else 'None'}")
                        if ad:
                            yield ad
                    await page.close()
            finally:
                await context.close()
                await browser.close()

    async def parse_listing_page(self, context, url):
        page = await context.new_page()
        try:
            await page.goto(url, wait_until="domcontentloaded")
            await asyncio.sleep(2)
            html = await page.content()

            match = re.search(r'<script type="application/ld\+json">(.*?)</script>', html, re.DOTALL)
            data = {}
            if match:
                try:
                    data = json.loads(match.group(1))
                except Exception:
                    data = {}

            title = data.get('name') or await self._get_selector_text(page, 'h1') or ""
            price = data.get('offers', {}).get('price', '') if data.get('offers') else ""
            image = data.get('image', '') or await self._get_selector_attr(page, 'img', 'src') or ""
            desc = data.get('description', '') or await self._get_selector_text(page, '[data-testid*="item-description"]') or ""
            ad_url = url

            delivery = False
            if "delivery" in html.lower():
                delivery = True

            seller_id = None
            m = re.search(r'"user":{"id":"(.*?)"', html)
            if m:
                seller_id = m.group(1)
            if not seller_id and 'seller' in data and isinstance(data['seller'], dict):
                seller_id = data['seller'].get('identifier')

            seller_info = {}
            if seller_id:
                seller_info = await self.parse_seller_profile(context, seller_id)

            location = await self._get_selector_text(page, '[data-testid*="item-location"]')
            post_date = await self._get_selector_text(page, '[data-testid*="item-published-date"]')
            views = await self._get_selector_text(page, '[data-testid*="item-views"]')
            chat_url = ""
            chat_el = await page.query_selector('a[href*="chat?userId="]')
            if chat_el:
                chat_url = await chat_el.get_attribute("href")

            ad = {
                "title": title,
                "price": price,
                "desc": desc,
                "location": location or "",
                "delivery": delivery,
                "url": ad_url,
                "photo": image,
                "chat_url": chat_url,
                "post_date": post_date or "",
                "views": views or "",
            }
            ad.update(seller_info)
            return ad
        finally:
            await page.close()

    async def parse_seller_profile(self, context, seller_id):
        profile_url = f"https://{self.domain}.wallapop.com/user/{seller_id}"
        page = await context.new_page()
        try:
            await page.goto(profile_url, wait_until="domcontentloaded")
            await asyncio.sleep(2)

            seller_name = await self._get_selector_text(page, 'h1[data-testid*="profile-username"]') or ""
            rating_el = await page.query_selector('span[data-testid*="profile-rating-score"]')
            try:
                seller_rating = float(await rating_el.inner_text()) if rating_el else 0
            except Exception:
                seller_rating = 0

            spans = await page.query_selector_all('span')
            seller_ads_count = seller_sales = seller_purchases = 0
            seller_reg_date = ""
            for sp in spans:
                txt = (await sp.inner_text()).lower()
                if "anuncio" in txt:
                    seller_ads_count = int(''.join(filter(str.isdigit, txt)))
                elif "venta" in txt:
                    seller_sales = int(''.join(filter(str.isdigit, txt)))
                elif "compra" in txt:
                    seller_purchases = int(''.join(filter(str.isdigit, txt)))
                elif "miembro desde" in txt:
                    seller_reg_date = txt

            profile_img = await self._get_selector_attr(page, 'img[data-testid*="profile-image"]', 'src') or ""
            seller_info = {
                "seller_name": seller_name,
                "seller_rating": seller_rating,
                "seller_ads_count": seller_ads_count,
                "seller_sales": seller_sales,
                "seller_purchases": seller_purchases,
                "seller_reg_date": seller_reg_date,
                "seller_profile_img": profile_img,
            }
            return seller_info
        finally:
            await page.close()

    async def _get_selector_text(self, page, selector):
        try:
            el = await page.query_selector(selector)
            if el:
                return await el.inner_text()
        except Exception:
            return ""
        return ""

    async def _get_selector_attr(self, page, selector, attr):
        try:
            el = await page.query_selector(selector)
            if el:
                return await el.get_attribute(attr)
        except Exception:
            return ""
        return ""
