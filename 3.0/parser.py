from bs4 import BeautifulSoup
import httpx

def parse_wallapop_ads(query, page=1):
    url = f"https://es.wallapop.com/app/search?keywords={query}&page={page}"
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/120.0.0.0 Safari/537.36"
    }
    resp = httpx.get(url, headers=headers)
    if resp.status_code != 200:
        return []
    data = resp.json()
    ads = []
    for item in data.get("search_objects", []):
        ads.append({
            "id": item.get("id"),
            "title": item.get("title"),
            "price": item.get("price"),
            "url": f"https://es.wallapop.com/item/{item.get('id')}",
        })
    return ads