import os

from telethon import TelegramClient
from telethon.sessions import StringSession

api_id = int(os.environ["TG_API_ID"])
api_hash = os.environ["TG_API_HASH"]


async def main():
    async with TelegramClient(
        StringSession(), api_id, api_hash, proxy=("http", "127.0.0.1", 7890)
    ) as client:
        session = client.session.save()
        print("\nTG_SESSION_STRING=")
        print(session)


if __name__ == "__main__":
    import asyncio

    asyncio.run(main())
