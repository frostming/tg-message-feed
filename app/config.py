from __future__ import annotations

import os
from dataclasses import dataclass
from urllib.parse import unquote, urlparse


class ConfigError(ValueError):
    pass


def _env_get(key: str) -> str | None:
    value = os.getenv(key)
    if value is not None:
        return value
    return os.getenv(key.lower())


def proxy_from_env() -> object | None:
    # Precedence:
    # - TG_PROXY if present (even empty -> disables proxy)
    # - then standard proxy env vars
    if "TG_PROXY" in os.environ or "tg_proxy" in os.environ:
        return parse_proxy(_env_get("TG_PROXY"))

    return parse_proxy(
        _env_get("ALL_PROXY") or _env_get("HTTPS_PROXY") or _env_get("HTTP_PROXY")
    )


def parse_proxy(value: str | None) -> object | None:
    raw = (value or "").strip()
    if raw == "":
        return None

    # Accept both URL forms (e.g. socks5://user:pass@host:1080)
    # and host:port shorthand (assumed http).
    if "://" not in raw:
        raw = f"http://{raw}"

    parsed = urlparse(raw)
    scheme = (parsed.scheme or "").lower()
    if scheme in {"http", "https"}:
        proxy_scheme = "http"
        rdns = False
    elif scheme in {"socks5", "socks5h"}:
        proxy_scheme = "socks5"
        rdns = scheme == "socks5h"
    elif scheme in {"socks4", "socks4a"}:
        proxy_scheme = "socks4"
        rdns = scheme == "socks4a"
    else:
        raise ConfigError(
            "Unsupported proxy scheme in TG_PROXY. "
            "Use http(s)://, socks5(h)://, or socks4(a)://"
        )

    host = parsed.hostname
    port = parsed.port
    if not host or port is None:
        raise ConfigError(
            "Invalid TG_PROXY. Expected a URL like http://host:port or socks5://host:port"
        )

    username = unquote(parsed.username) if parsed.username else None
    password = unquote(parsed.password) if parsed.password else None

    try:
        import socks  # type: ignore

        proxy_type: object
        if proxy_scheme == "http":
            proxy_type = socks.HTTP
        elif proxy_scheme == "socks4":
            proxy_type = socks.SOCKS4
        else:
            proxy_type = socks.SOCKS5
    except Exception:
        # Telethon can work with PySocks constants if installed, but we keep a
        # string proxy type for compatibility with environments without it.
        proxy_type = proxy_scheme

    parts: list[object] = [proxy_type, host, int(port)]
    if rdns or username or password:
        parts.append(rdns)
    if username or password:
        parts.append(username or "")
        parts.append(password or "")
    return tuple(parts)


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


def _as_chat(value: str) -> list[int]:
    parts = value.strip().split(",")
    result = []
    for part in parts:
        stripped = part.strip()
        if stripped.startswith("-") and stripped[1:].isdigit():
            result.append(int(stripped))
        elif stripped.isdigit():
            result.append(int(stripped))
    return result


@dataclass(frozen=True)
class Settings:
    tg_api_id: int
    tg_api_hash: str
    tg_session_string: str
    tg_target_chat: list[int]
    tg_proxy: object | None

    mq_url: str
    mq_exchange: str
    mq_persistent: bool

    service_name: str

    @classmethod
    def from_env(cls) -> "Settings":
        tg_api_id = int(_required_env("TG_API_ID"))
        tg_api_hash = _required_env("TG_API_HASH")
        tg_session_string = _required_env("TG_SESSION_STRING")
        tg_target_chat = _as_chat(_required_env("TG_TARGET_CHAT"))
        tg_proxy = proxy_from_env()

        mq_url = os.getenv("MQ_URL", "amqp://guest:guest@rabbitmq:5672/").strip()
        mq_exchange = os.getenv("MQ_EXCHANGE", "telegram.messages").strip()
        mq_persistent = _as_bool(os.getenv("MQ_PERSISTENT", "true"), default=True)

        service_name = os.getenv("SERVICE_NAME", "telegram-userbot-listener").strip()

        return cls(
            tg_api_id=tg_api_id,
            tg_api_hash=tg_api_hash,
            tg_session_string=tg_session_string,
            tg_target_chat=tg_target_chat,
            tg_proxy=tg_proxy,
            mq_url=mq_url,
            mq_exchange=mq_exchange,
            mq_persistent=mq_persistent,
            service_name=service_name,
        )
