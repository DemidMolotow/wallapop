import asyncio
from messaging.mailing_worker import process_accounts

if __name__ == "__main__":
    asyncio.run(process_accounts())
