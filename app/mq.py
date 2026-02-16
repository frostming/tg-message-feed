from __future__ import annotations

import json
from datetime import UTC, datetime
from typing import Any, Dict, Optional

import aio_pika
from aio_pika import DeliveryMode, ExchangeType, Message
from aio_pika.abc import AbstractChannel, AbstractConnection, AbstractExchange

from app.config import Settings


class MQPublisher:
    def __init__(self, settings: Settings) -> None:
        self._settings = settings
        self._connection: Optional[AbstractConnection] = None
        self._channel: Optional[AbstractChannel] = None
        self._exchange: Optional[AbstractExchange] = None

    async def connect(self) -> None:
        self._connection = await aio_pika.connect_robust(self._settings.mq_url)
        self._channel = await self._connection.channel()
        self._exchange = await self._channel.declare_exchange(
            self._settings.mq_exchange,
            ExchangeType.TOPIC,
            durable=True,
        )

        queue = await self._channel.declare_queue(self._settings.mq_queue, durable=True)
        # Bind all routing keys so one queue can still consume messages from all chats.
        await queue.bind(self._exchange, routing_key="#")

    async def publish(self, payload: Dict[str, Any], routing_key: str) -> None:
        if self._exchange is None:
            raise RuntimeError("MQPublisher is not connected")

        message = Message(
            body=json.dumps(payload, ensure_ascii=False).encode("utf-8"),
            content_type="application/json",
            timestamp=datetime.now(tz=UTC),
            delivery_mode=(
                DeliveryMode.PERSISTENT
                if self._settings.mq_persistent
                else DeliveryMode.NOT_PERSISTENT
            ),
        )
        await self._exchange.publish(message, routing_key=routing_key)

    async def close(self) -> None:
        if self._channel is not None:
            await self._channel.close()
        if self._connection is not None:
            await self._connection.close()
