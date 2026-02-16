from __future__ import annotations

import asyncio
import logging
from datetime import UTC
from typing import Any, Dict

from telethon import TelegramClient, events
from telethon.sessions import StringSession

from app.config import Settings
from app.mq import MQPublisher

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s [%(name)s] %(message)s",
)
logger = logging.getLogger("telegram_listener")


def _extract_media_payload(message: Any) -> Dict[str, Any] | None:
    if not message.media:
        return None

    file = message.file
    media_type = "unknown"
    if message.photo:
        media_type = "photo"
    elif message.video:
        media_type = "video"
    elif message.voice:
        media_type = "voice"
    elif message.audio:
        media_type = "audio"
    elif message.gif:
        media_type = "gif"
    elif message.sticker:
        media_type = "sticker"
    elif message.document:
        media_type = "document"

    return {
        "type": media_type,
        "class_name": message.media.__class__.__name__,
        "grouped_id": message.grouped_id,
        "file_id": getattr(file, "id", None) if file else None,
        "name": getattr(file, "name", None) if file else None,
        "ext": getattr(file, "ext", None) if file else None,
        "mime_type": getattr(file, "mime_type", None) if file else None,
        "size": getattr(file, "size", None) if file else None,
        "width": getattr(file, "width", None) if file else None,
        "height": getattr(file, "height", None) if file else None,
        "duration": getattr(file, "duration", None) if file else None,
    }


def _build_payload(event: events.NewMessage.Event, service_name: str) -> Dict[str, Any]:
    message = event.message
    sender = event.sender
    sender_first_name = getattr(sender, "first_name", None)
    sender_last_name = getattr(sender, "last_name", None)
    return {
        "service": service_name,
        "event": "telegram.new_message",
        "chat_id": message.chat_id,
        "message_id": message.id,
        "sender_id": event.sender_id,
        "is_bot": bool(getattr(sender, "bot", None)),
        "sender_username": getattr(sender, "username", None),
        "sender_fullname": (
            sender_first_name + (f" {sender_last_name}" if sender_last_name else "")
            if sender_first_name
            else None
        ),
        "text": message.message,
        "date": message.date.astimezone(UTC).isoformat() if message.date else None,
        "is_reply": message.is_reply,
        "reply_to_msg_id": message.reply_to.reply_to_msg_id
        if message.reply_to
        else None,
        "has_media": bool(message.media),
        "media": _extract_media_payload(message),
        "out": message.out,
    }


async def run() -> None:
    settings = Settings.from_env()
    publisher = MQPublisher(settings)

    await publisher.connect()
    logger.info(
        "Connected to MQ exchange=%s queue=%s routing_key=%s",
        settings.mq_exchange,
        settings.mq_queue,
        settings.mq_routing_key,
    )

    client = TelegramClient(
        StringSession(settings.tg_session_string),
        settings.tg_api_id,
        settings.tg_api_hash,
    )

    @client.on(events.NewMessage(chats=settings.tg_target_chat))
    async def on_new_message(event: events.NewMessage.Event) -> None:
        await event.get_sender()
        payload = _build_payload(event, service_name=settings.service_name)
        await publisher.publish(payload)
        logger.info(
            "Published message chat_id=%s message_id=%s payload=%s",
            payload["chat_id"],
            payload["message_id"],
            payload,
        )

    await client.connect()
    if not await client.is_user_authorized():
        raise RuntimeError(
            "Telegram session is not authorized. Generate a valid TG_SESSION_STRING first."
        )

    logger.info("Listening chat=%s", settings.tg_target_chat)

    try:
        await client.run_until_disconnected()
    finally:
        await publisher.close()


def main() -> None:
    asyncio.run(run())


if __name__ == "__main__":
    main()
