from dataclasses import dataclass

@dataclass
class FilterSettings:
    domain: str = "es"
    min_ads: int = 0
    min_sales: int = 0
    min_purchases: int = 0
    min_views: int = 0
    min_post_date: str = ""
    exclude_rating: bool = False
    delivery: bool = None

    def set(self, key, val):
        if key == "domain":
            self.domain = val
        elif key == "min_ads":
            self.min_ads = int(val)
        elif key == "min_sales":
            self.min_sales = int(val)
        elif key == "min_purchases":
            self.min_purchases = int(val)
        elif key == "min_views":
            self.min_views = int(val)
        elif key == "min_post_date":
            self.min_post_date = val
        elif key == "exclude_rating":
            self.exclude_rating = self._parse_bool(val)
        elif key == "delivery":
            self.delivery = self._parse_bool(val)
        else:
            return False
        return True

    @staticmethod
    def _parse_bool(val):
        val = str(val).strip().lower()
        if val in ("1", "true", "yes", "да", "y"):
            return True
        if val in ("0", "false", "no", "нет", "n"):
            return False
        raise ValueError(f"Невозможно преобразовать '{val}' в bool")

    def apply(self, ads):
        def ok(ad):
            if self.min_ads and ad.get("seller_ads_count", 0) < self.min_ads:
                return False
            if self.min_sales and ad.get("seller_sales", 0) < self.min_sales:
                return False
            if self.min_purchases and ad.get("seller_purchases", 0) < self.min_purchases:
                return False
            if self.min_views and (not ad.get("views") or int(ad.get("views")) < self.min_views):
                return False
            if self.exclude_rating and ad.get("seller_rating", 0):
                return False
            if self.delivery is not None and ad.get("delivery") != self.delivery:
                return False
            return True
        return [ad for ad in ads if ok(ad)]

def filter_to_text(key):
    return {
        "domain": "Домен Wallapop (es, it, pt)",
        "min_ads": "Мин. объявлений у продавца",
        "min_sales": "Мин. продаж у продавца",
        "min_purchases": "Мин. покупок у продавца",
        "min_views": "Мин. просмотров объявления",
        "min_post_date": "Мин. дата размещения",
        "exclude_rating": "Исключить продавцов с рейтингом",
        "delivery": "Требуется доставка",
    }.get(key, key)

def get_filter_keyboard():
    from telegram import InlineKeyboardMarkup, InlineKeyboardButton
    keys = [
        ("domain", "Домен"),
        ("min_ads", "Мин. объявлений"),
        ("min_sales", "Мин. продаж"),
        ("min_purchases", "Мин. покупок"),
        ("min_views", "Мин. просмотров"),
        ("exclude_rating", "Искл. с рейтингом"),
        ("delivery", "Требуется доставка"),
    ]
    return InlineKeyboardMarkup([[InlineKeyboardButton(txt, callback_data=key)] for key, txt in keys])
