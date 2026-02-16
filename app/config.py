from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Union


class ConfigError(ValueError):
    pass


def _required_env(key: str) -> str:
    value = os.getenv(key)
    if value is None or value.strip() == "":
        raise ConfigError(f"Missing required environment variable: {key}")
    return value.strip()


def _as_bool(value: str, default: bool = False) -> bool:
    raw = value.strip().lower()
    if raw in {"1", "true", "yes", "on"}:
        return True
    if raw in {"0", "false", "no", "off"}:
        return False
    return default


def _as_chat(value: str) -> Union[int, str]:
    stripped = value.strip()
    if stripped.startswith("-") and stripped[1:].isdigit():
        return int(stripped)
    if stripped.isdigit():
        return int(stripped)
    return stripped


@dataclass(frozen=True)
class Settings:
    tg_api_id: int
    tg_api_hash: str
    tg_session_string: str
    tg_target_chat: Union[int, str]

    mq_url: str
    mq_exchange: str
    mq_queue: str
    mq_routing_key: str
    mq_persistent: bool

    service_name: str

    @classmethod
    def from_env(cls) -> "Settings":
        tg_api_id = int(_required_env("TG_API_ID"))
        tg_api_hash = _required_env("TG_API_HASH")
        tg_session_string = _required_env("TG_SESSION_STRING")
        tg_target_chat = _as_chat(_required_env("TG_TARGET_CHAT"))

        mq_url = os.getenv("MQ_URL", "amqp://guest:guest@rabbitmq:5672/").strip()
        mq_exchange = os.getenv("MQ_EXCHANGE", "telegram.messages").strip()
        mq_queue = os.getenv("MQ_QUEUE", "telegram.messages.raw").strip()
        mq_routing_key = os.getenv("MQ_ROUTING_KEY", "telegram.message").strip()
        mq_persistent = _as_bool(os.getenv("MQ_PERSISTENT", "true"), default=True)

        service_name = os.getenv("SERVICE_NAME", "telegram-userbot-listener").strip()

        return cls(
            tg_api_id=tg_api_id,
            tg_api_hash=tg_api_hash,
            tg_session_string=tg_session_string,
            tg_target_chat=tg_target_chat,
            mq_url=mq_url,
            mq_exchange=mq_exchange,
            mq_queue=mq_queue,
            mq_routing_key=mq_routing_key,
            mq_persistent=mq_persistent,
            service_name=service_name,
        )
