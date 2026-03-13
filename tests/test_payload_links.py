from __future__ import annotations

import sys
from datetime import UTC, datetime
from types import ModuleType
from types import SimpleNamespace
from unittest import TestCase

telethon_module = ModuleType("telethon")
telethon_module.TelegramClient = object
telethon_module.events = SimpleNamespace(NewMessage=SimpleNamespace(Event=object))
telethon_sessions_module = ModuleType("telethon.sessions")
telethon_sessions_module.StringSession = object
sys.modules.setdefault("telethon", telethon_module)
sys.modules.setdefault("telethon.sessions", telethon_sessions_module)

from app.main import _build_payload, _extract_reply_payload


class PayloadLinksTests(TestCase):
    def test_build_payload_extracts_links(self) -> None:
        sender = SimpleNamespace(bot=False, username="alice", first_name="Alice")
        message = SimpleNamespace(
            chat_id=-100123,
            id=42,
            message="Alice",
            text_html='<a href="tg://user?id=123456">Alice</a>',
            date=datetime(2026, 3, 13, tzinfo=UTC),
            is_reply=False,
            media=None,
            out=False,
        )
        event = SimpleNamespace(message=message, sender=sender, sender_id=123456)

        payload = _build_payload(event, service_name="test-service", reply_to=None)

        self.assertEqual(payload["links"], ["tg://user?id=123456"])

    def test_extract_reply_payload_extracts_links(self) -> None:
        reply_sender = SimpleNamespace(username="bob", first_name="Bob")
        reply_message = SimpleNamespace(
            id=41,
            sender_id=654321,
            sender=reply_sender,
            message="Bob",
            text_html='<a href="tg://user?id=654321">Bob</a>',
        )

        payload = _extract_reply_payload(reply_message)

        self.assertEqual(payload["links"], ["tg://user?id=654321"])
