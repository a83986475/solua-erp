"""Small dependency-free checks for WhatsApp parsing and redaction."""

from datetime import datetime, timedelta, timezone

from solua_home.api.whatsapp_core import (
    mask_phone,
    parse_status_events,
    parse_webhook_events,
    service_window_open,
)


def demo():
    assert mask_phone("258 84 123 4567") == "********4567"
    now = datetime.now(timezone.utc)
    assert service_window_open(now + timedelta(hours=1), now)
    assert not service_window_open(now - timedelta(seconds=1), now)

    payload = {
        "entry": [
            {
                "changes": [
                    {
                        "value": {
                            "metadata": {"phone_number_id": "phone-1"},
                            "contacts": [{"wa_id": "258841234567", "profile": {"name": "客人"}}],
                            "messages": [
                                {
                                    "id": "wamid.1",
                                    "from": "258841234567",
                                    "timestamp": "1700000000",
                                    "type": "text",
                                    "text": {"body": "你好"},
                                }
                            ],
                            "statuses": [
                                {"id": "wamid.2", "status": "delivered", "timestamp": "1700000001"}
                            ],
                        }
                    }
                ]
            }
        ]
    }
    events = parse_webhook_events(payload)
    assert events[0]["wa_id"] == "258841234567"
    assert events[0]["body"] == "你好"
    statuses = parse_status_events(payload)
    assert statuses[0]["status"] == "delivered"
    return "whatsapp_core checks passed"


if __name__ == "__main__":
    print(demo())
