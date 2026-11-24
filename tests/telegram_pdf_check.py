"""Regression check for Frappe's JSON webhook without a content type."""

import importlib.util
import json
import sys
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock


def check():
    frappe = SimpleNamespace(
        conf={"solua_telegram_webhook_secret": "test-secret"},
        local=SimpleNamespace(response=SimpleNamespace()),
        enqueue=Mock(),
        whitelist=lambda **kwargs: lambda method: method,
    )
    sys.modules["frappe"] = frappe
    path = Path(__file__).resolve().parents[1] / "api" / "telegram.py"
    spec = importlib.util.spec_from_file_location("telegram_pdf", path)
    telegram = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(telegram)

    def request(body, *, secret="test-secret"):
        def get_json(*, force=False, silent=False):
            assert silent
            return json.loads(body) if force else None

        frappe.request = SimpleNamespace(args={"secret": secret}, get_json=get_json)
        frappe.enqueue.reset_mock()
        return telegram.webhook()

    assert request('{"doctype":"Delivery Note","name":"DN-CHECK"}')["queued"]
    frappe.enqueue.assert_called_once_with(
        "solua_home.api.telegram.send_document_pdf",
        queue="short",
        enqueue_after_commit=True,
        job_id="telegram-pdf:Delivery Note:DN-CHECK",
        deduplicate=True,
        doctype="Delivery Note",
        name="DN-CHECK",
    )
    assert not request('{"doctype":"Delivery Note","name":"DN-CHECK"}', secret="bad")["ok"]
    assert frappe.local.response.http_status_code == 403
    frappe.enqueue.assert_not_called()
    for body in ('["invalid"]', '{"doctype":[]}', '{"doctype":"Sales Order","name":" "}'):
        assert not request(body)["ok"]
        assert frappe.local.response.http_status_code == 400
        frappe.enqueue.assert_not_called()


if __name__ == "__main__":
    check()
    print("Telegram PDF webhook checks passed")
