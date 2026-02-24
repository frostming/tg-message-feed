import os

from telethon import TelegramClient
from telethon.sessions import StringSession

from app.config import proxy_from_env

api_id = int(os.environ["TG_API_ID"])
api_hash = os.environ["TG_API_HASH"]


async def main():
    proxy = proxy_from_env()

    client_kwargs: dict[str, object] = {}
    if proxy is not None:
        client_kwargs["proxy"] = proxy

    async with TelegramClient(
        StringSession(), api_id, api_hash, **client_kwargs
    ) as client:
        session = client.session.save()
        print("\nTG_SESSION_STRING=")
        print(session)


if __name__ == "__main__":
    import asyncio

    asyncio.run(main())
