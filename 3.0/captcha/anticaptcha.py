import httpx
import time

class CaptchaSolver2Captcha:
    def __init__(self, api_key):
        self.api_key = api_key
        self.api_url = "http://2captcha.com"

    def submit_recaptcha(self, site_key, url):
        data = {
            'key': self.api_key,
            'method': 'userrecaptcha',
            'googlekey': site_key,
            'pageurl': url,
            'json': 1
        }
        r = httpx.post(f"{self.api_url}/in.php", data=data)
        if r.status_code != 200 or r.json().get("status") != 1:
            return None
        request_id = r.json()["request"]
        return request_id

    def get_solution(self, request_id, max_wait=120):
        params = {
            'key': self.api_key,
            'action': 'get',
            'id': request_id,
            'json': 1
        }
        start = time.time()
        while time.time() - start < max_wait:
            r = httpx.get(f"{self.api_url}/res.php", params=params)
            if r.status_code == 200:
                result = r.json()
                if result.get("status") == 1:
                    return result["request"]
                elif result.get("request") != "CAPCHA_NOT_READY":
                    break
            time.sleep(5)
        return None

def solve_captcha(api_key, site_key, url):
    solver = CaptchaSolver2Captcha(api_key)
    request_id = solver.submit_recaptcha(site_key, url)
    if not request_id:
        return None
    solution = solver.get_solution(request_id)
    return solution

# Использование:
# solution = solve_captcha(CAPTCHA_API_KEY, site_key, url)