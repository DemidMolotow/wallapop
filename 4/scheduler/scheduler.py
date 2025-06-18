import asyncio
import random
import time

class RateLimiter:
    def __init__(self, min_delay=15, max_delay=60):
        self.min_delay = min_delay
        self.max_delay = max_delay
        self.last_time = 0

    async def wait(self):
        now = time.time()
        delay = random.uniform(self.min_delay, self.max_delay)
        wait_time = max(0, delay - (now - self.last_time))
        await asyncio.sleep(wait_time)
        self.last_time = time.time()