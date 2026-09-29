"""Pure helpers for the WhatsApp inbox.

Keep parsing and redaction independent from Frappe so they can be checked
without a running site.
"""

from __future__ import annotations

import re
from datetime import datetime, timezone


def normalize_phone(value: object) -> str:
    return re.sub(r"\D+", "", str(value or ""))


def mask_phone(value: object) -> str:
    digits = normalize_phone(value)
    if len(digits) <= 4:
        return "****"
    return "*" * (len(digits) - 4) + digits[-4:]


def service_window_open(until: datetime | None, now: datetime | None = None) -> bool:
    if not until:
        return False
    now = now or datetime.now(timezone.utc)
    if until.tzinfo is None:
        until = until.replace(tzinfo=timezone.utc)
    if now.tzinfo is None:
        now = now.replace(tzinfo=timezone.utc)
    return until > now


def _message_body(message: dict) -> str:
    message_type = message.get("type") or "text"
    if message_type == "text":
        return str((message.get("text") or {}).get("body") or "")
    if message_type == "interactive":
        interactive = message.get("interactive") or {}
        reply = interactive.get("button_reply") or interactive.get("list_reply") or {}
        return str(reply.get("title") or reply.get("description") or "")
    return str((message.get(message_type) or {}).get("caption") or "")


def parse_webhook_events(payload: dict) -> list[dict]:
    """Extract inbound customer messages from a Meta webhook payload."""
    events = []
    for entry in payload.get("entry") or []:
        for change in entry.get("changes") or []:
            value = change.get("value") or {}
            contacts = {
                str(contact.get("wa_id")): contact
                for contact in value.get("contacts") or []
                if contact.get("wa_id")
            }
            metadata = value.get("metadata") or {}
            for message in value.get("messages") or []:
                wa_id = str(message.get("from") or "").strip()
                if not wa_id or not message.get("id"):
                    continue
                contact = contacts.get(wa_id) or {}
                profile = contact.get("profile") or {}
                events.append(
                    {
                        "message_id": str(message["id"]),
                        "wa_id": wa_id,
                        "display_name": str(profile.get("name") or "").strip(),
                        "message_type": str(message.get("type") or "text"),
                        "body": _message_body(message).strip(),
                        "timestamp": message.get("timestamp"),
                        "phone_number_id": metadata.get("phone_number_id"),
                    }
                )
    return events


def parse_status_events(payload: dict) -> list[dict]:
    events = []
    for entry in payload.get("entry") or []:
        for change in entry.get("changes") or []:
            value = change.get("value") or {}
            for status in value.get("statuses") or []:
                message_id = status.get("id")
                if not message_id or not status.get("status"):
                    continue
                events.append(
                    {
                        "message_id": str(message_id),
                        "status": str(status["status"]),
                        "timestamp": status.get("timestamp"),
                        "recipient_id": str(status.get("recipient_id") or ""),
                        "errors": status.get("errors") or [],
                    }
                )
    return events
