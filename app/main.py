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


def _build_fullname(entity: Any) -> str | None:
    first_name = getattr(entity, "first_name", None)
    last_name = getattr(entity, "last_name", None)
    if first_name and last_name:
        return f"{first_name} {last_name}"
    return first_name or last_name


def _build_routing_key(chat_id: Any, fallback: str) -> str:
    if chat_id is None:
        return fallback
    return f"chat:{chat_id}"


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


def _extract_reply_payload(reply_message: Any | None) -> Dict[str, Any] | None:
    if reply_message is None:
        return None

    reply_sender = getattr(reply_message, "sender", None)
    return {
        "message_id": reply_message.id,
        "sender_id": getattr(reply_message, "sender_id", None),
        "sender_username": getattr(reply_sender, "username", None),
        "sender_fullname": _build_fullname(reply_sender),
        "text": reply_message.message,
    }


def _build_payload(
    event: events.NewMessage.Event,
    service_name: str,
    reply_to: Dict[str, Any] | None,
) -> Dict[str, Any]:
    message = event.message
    sender = event.sender
    return {
        "service": service_name,
        "event": "telegram.new_message",
        "chat_id": message.chat_id,
        "message_id": message.id,
        "sender_id": event.sender_id,
        "is_bot": bool(getattr(sender, "bot", None)),
        "sender_username": getattr(sender, "username", None),
        "sender_fullname": _build_fullname(sender),
        "text": message.message,
        "date": message.date.astimezone(UTC).isoformat() if message.date else None,
        "is_reply": message.is_reply,
        "reply_to": reply_to,
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
        reply_message = await event.get_reply_message() if event.message.is_reply else None
        if reply_message is not None and getattr(reply_message, "sender", None) is None:
            await reply_message.get_sender()

        payload = _build_payload(
            event,
            service_name=settings.service_name,
            reply_to=_extract_reply_payload(reply_message),
        )
        routing_key = _build_routing_key(
            payload["chat_id"],
            fallback=settings.mq_routing_key,
        )
        await publisher.publish(payload, routing_key=routing_key)
        logger.info(
            "Published message chat_id=%s message_id=%s routing_key=%s payload=%s",
            payload["chat_id"],
            payload["message_id"],
            routing_key,
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
