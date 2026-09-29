"""WhatsApp Business Cloud API and internal shared inbox endpoints."""

from __future__ import annotations

import hashlib
import hmac
import json
import urllib.error
import urllib.request
from datetime import datetime, timezone

import frappe
from frappe import _
from frappe.utils import add_to_date, get_datetime, now_datetime

from solua_home.api.whatsapp_core import (
    mask_phone,
    parse_status_events,
    parse_webhook_events,
    service_window_open,
)


SUPPORT_ROLES = {"WhatsApp Support", "WhatsApp Supervisor"}
SUPERVISOR_ROLES = {"WhatsApp Supervisor", "System Manager"}
CONVERSATION_FIELDS = [
    "name",
    "wa_id",
    "display_name",
    "customer",
    "status",
    "assigned_to",
    "priority",
    "last_inbound_at",
    "last_message_at",
    "service_window_until",
    "last_message_preview",
    "unread_count",
    "next_reminder_at",
    "reminder_note",
]


def _roles(user=None):
    user = user or frappe.session.user
    return set(frappe.get_roles(user) or [])


def _is_support(user=None):
    user = user or frappe.session.user
    return user != "Guest" and bool(_roles(user) & (SUPPORT_ROLES | SUPERVISOR_ROLES))


def _is_supervisor(user=None):
    user = user or frappe.session.user
    return user != "Guest" and bool(_roles(user) & SUPERVISOR_ROLES)


def _require_support():
    if not _is_support():
        frappe.throw(_("没有 WhatsApp 客服权限"), frappe.PermissionError)


def _require_conversation(name):
    conversation = frappe.db.get_value(
        "WhatsApp Conversation", name, CONVERSATION_FIELDS, as_dict=True
    )
    if not conversation:
        frappe.throw(_("会话不存在"), frappe.DoesNotExistError)
    return conversation


def _can_view_full(conversation, user=None):
    user = user or frappe.session.user
    return _is_supervisor(user) or conversation.assigned_to == user


def _require_full_access(conversation):
    if not _can_view_full(conversation):
        frappe.throw(_("请先领取或等待主管分配此会话"), frappe.PermissionError)


def _config():
    config = frappe.conf
    return {
        "token": config.get("whatsapp_cloud_api_token"),
        "phone_number_id": config.get("whatsapp_cloud_api_phone_number_id"),
        "api_version": config.get("whatsapp_cloud_api_version"),
        "api_base_url": config.get("whatsapp_cloud_api_base_url")
        or "https://graph.facebook.com",
        "verify_token": config.get("whatsapp_cloud_api_verify_token"),
        "app_secret": config.get("whatsapp_cloud_api_app_secret"),
    }


def _json_request(url, payload, token):
    request = urllib.request.Request(
        url,
        data=json.dumps(payload).encode("utf-8"),
        headers={
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
            "Accept": "application/json",
        },
        method="POST",
    )
    try:
        with urllib.request.urlopen(request, timeout=20) as response:
            raw = response.read().decode("utf-8")
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace")[:500]
        raise RuntimeError(f"WhatsApp API HTTP {exc.code}: {detail}") from exc
    except urllib.error.URLError as exc:
        raise RuntimeError(f"WhatsApp API network error: {exc.reason}") from exc
    try:
        return json.loads(raw) if raw else {}
    except json.JSONDecodeError as exc:
        raise RuntimeError("WhatsApp API returned invalid JSON") from exc


def _send_text(wa_id, body):
    config = _config()
    missing = [
        key
        for key in ("token", "phone_number_id", "api_version")
        if not config.get(key)
    ]
    if missing:
        raise RuntimeError("WhatsApp Cloud API 未配置: " + ", ".join(missing))
    url = (
        f"{config['api_base_url'].rstrip('/')}/"
        f"{config['api_version'].strip('/')}/{config['phone_number_id']}/messages"
    )
    return _json_request(
        url,
        {
            "messaging_product": "whatsapp",
            "to": wa_id,
            "type": "text",
            "text": {"preview_url": False, "body": body},
        },
        config["token"],
    )


def _provider_datetime(timestamp):
    try:
        return datetime.fromtimestamp(int(timestamp), tz=timezone.utc).replace(tzinfo=None)
    except (TypeError, ValueError, OverflowError):
        return now_datetime()


def _find_customer(wa_id):
    for field in ("mobile_no", "phone"):
        rows = frappe.get_all(
            "Customer",
            filters={field: wa_id},
            fields=["name"],
            limit_page_length=2,
        )
        if len(rows) == 1:
            return rows[0].name
    return None


def _upsert_inbound(event):
    message_id = event["message_id"]
    existing = frappe.db.exists(
        "WhatsApp Message", {"provider_message_id": message_id}
    )
    if existing:
        return existing

    conversation_name = frappe.db.get_value(
        "WhatsApp Conversation", {"wa_id": event["wa_id"]}, "name"
    )
    if conversation_name:
        conversation = frappe.get_doc("WhatsApp Conversation", conversation_name)
    else:
        conversation = frappe.get_doc(
            {
                "doctype": "WhatsApp Conversation",
                "owner": "Administrator",
                "wa_id": event["wa_id"],
                "display_name": event.get("display_name") or event["wa_id"],
                "customer": _find_customer(event["wa_id"]),
                "status": "未分配",
                "priority": "普通",
                "unread_count": 0,
            }
        )
        conversation.insert(ignore_permissions=True)

    now = now_datetime()
    message = frappe.get_doc(
        {
            "doctype": "WhatsApp Message",
            "owner": "Administrator",
            "conversation": conversation.name,
            "direction": "客户消息",
            "message_type": event.get("message_type") or "text",
            "body": event.get("body") or "",
            "provider_message_id": message_id,
            "status": "已接收",
            "provider_timestamp": _provider_datetime(event.get("timestamp")),
        }
    )
    message.insert(ignore_permissions=True)

    conversation.display_name = event.get("display_name") or conversation.display_name
    conversation.last_inbound_at = now
    conversation.last_message_at = now
    conversation.last_message_preview = event.get("body") or f"[{event.get('message_type')}]"
    conversation.service_window_until = add_to_date(now, hours=24)
    conversation.unread_count = int(conversation.unread_count or 0) + 1
    conversation.save(ignore_permissions=True)
    frappe.publish_realtime(
        "whatsapp_inbox_updated",
        {"conversation": conversation.name},
        after_commit=True,
    )
    return message.name


def _apply_status(event):
    message_name = frappe.db.get_value(
        "WhatsApp Message",
        {"provider_message_id": event["message_id"]},
        "name",
    )
    if not message_name:
        return False
    message = frappe.get_doc("WhatsApp Message", message_name)
    message.status = event["status"]
    message.status_at = _provider_datetime(event.get("timestamp"))
    if event.get("errors"):
        message.error_message = json.dumps(event["errors"], ensure_ascii=False)[:500]
    message.save(ignore_permissions=True)
    return True


def _raw_request():
    request = getattr(frappe.local, "request", None)
    return request.get_data(cache=True) if request else b""


def _request_json():
    raw = _raw_request()
    try:
        return json.loads(raw.decode("utf-8")) if raw else {}
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        frappe.throw(_("Webhook JSON 无效"), frappe.ValidationError)
        raise exc


def _valid_signature(raw):
    secret = _config().get("app_secret")
    request = getattr(frappe.local, "request", None)
    received = request.headers.get("X-Hub-Signature-256", "") if request else ""
    if not secret or not received.startswith("sha256="):
        return False
    expected = hmac.new(secret.encode("utf-8"), raw, hashlib.sha256).hexdigest()
    return hmac.compare_digest(received[7:], expected)


@frappe.whitelist(allow_guest=True)
def verify_webhook():
    mode = frappe.form_dict.get("hub.mode")
    token = frappe.form_dict.get("hub.verify_token")
    challenge = frappe.form_dict.get("hub.challenge")
    if mode == "subscribe" and token and token == _config().get("verify_token"):
        frappe.local.response["type"] = "txt"
        frappe.local.response["doctype"] = "WhatsApp Webhook"
        frappe.local.response["result"] = challenge or ""
        return challenge or ""
    frappe.local.response["http_status_code"] = 403
    return "Forbidden"


@frappe.whitelist(allow_guest=True)
def webhook():
    request = getattr(frappe.local, "request", None)
    if request and request.method == "GET":
        return verify_webhook()
    raw = _raw_request()
    if not _valid_signature(raw):
        frappe.local.response["http_status_code"] = 401
        return {"ok": False, "error": "invalid signature"}
    payload = _request_json()
    received = 0
    for event in parse_webhook_events(payload):
        _upsert_inbound(event)
        received += 1
    for event in parse_status_events(payload):
        _apply_status(event)
    return {"ok": True, "received": received}


def _conversation_row(row, full=False):
    result = {key: row.get(key) for key in CONVERSATION_FIELDS if key != "wa_id"}
    result["phone"] = mask_phone(row.get("wa_id"))
    result["full_access"] = bool(full)
    if not full:
        result["last_message_preview"] = "有新客户消息" if row.get("unread_count") else "等待处理"
        result["display_name"] = "客户待分配"
        result["customer"] = None
    return result


@frappe.whitelist()
def get_inbox(status=None, limit=50):
    _require_support()
    limit = max(1, min(int(limit or 50), 100))
    filters = {"status": status} if status else {}
    if _is_supervisor():
        rows = frappe.get_all(
            "WhatsApp Conversation",
            filters=filters,
            fields=CONVERSATION_FIELDS,
            order_by="last_message_at desc",
            limit_page_length=limit,
        )
    else:
        rows = frappe.get_all(
            "WhatsApp Conversation",
            filters=filters,
            or_filters=[
                ["assigned_to", "=", frappe.session.user],
                ["assigned_to", "is", "not set"],
                ["assigned_to", "=", ""],
            ],
            fields=CONVERSATION_FIELDS,
            order_by="last_message_at desc",
            limit_page_length=limit,
        )
    return {
        "items": [
            _conversation_row(row, full=_can_view_full(row)) for row in rows
        ],
        "is_supervisor": _is_supervisor(),
    }


@frappe.whitelist()
def get_conversation(name):
    _require_support()
    conversation = _require_conversation(name)
    _require_full_access(conversation)
    messages = frappe.get_all(
        "WhatsApp Message",
        filters={"conversation": name},
        fields=[
            "name",
            "direction",
            "message_type",
            "body",
            "status",
            "error_message",
            "sender_user",
            "creation",
        ],
        order_by="creation asc",
        limit_page_length=200,
    )
    frappe.db.set_value("WhatsApp Conversation", name, "unread_count", 0)
    result = _conversation_row(conversation, full=True)
    result["messages"] = messages
    return result


@frappe.whitelist()
def claim_conversation(name):
    _require_support()
    conversation = _require_conversation(name)
    if conversation.assigned_to and conversation.assigned_to != frappe.session.user:
        frappe.throw(_("此会话已被其他员工领取"), frappe.PermissionError)
    frappe.db.set_value(
        "WhatsApp Conversation",
        name,
        {"assigned_to": frappe.session.user, "status": "处理中"},
    )
    return get_conversation(name)


@frappe.whitelist()
def list_support_users():
    _require_support()
    if not _is_supervisor():
        return {"items": []}
    rows = frappe.get_all(
        "User",
        filters={"enabled": 1, "user_type": "System User"},
        fields=["name", "full_name"],
        order_by="full_name asc",
        limit_page_length=0,
    )
    return {
        "items": [
            row
            for row in rows
            if _roles(row.name) & (SUPPORT_ROLES | SUPERVISOR_ROLES)
        ]
    }


@frappe.whitelist()
def assign_conversation(name, assigned_to=None):
    _require_support()
    if not _is_supervisor():
        frappe.throw(_("只有主管可以转交会话"), frappe.PermissionError)
    assigned_to = (assigned_to or "").strip()
    if assigned_to and not _is_support(assigned_to):
        frappe.throw(_("目标员工没有 WhatsApp 客服角色"), frappe.ValidationError)
    conversation = _require_conversation(name)
    conversation.assigned_to = assigned_to or None
    conversation.status = "未分配" if not assigned_to else "处理中"
    conversation.save(ignore_permissions=True)
    if assigned_to == frappe.session.user:
        return get_conversation(name)
    return _conversation_row(conversation, full=False)


@frappe.whitelist()
def add_internal_note(name, body):
    _require_support()
    conversation = _require_conversation(name)
    _require_full_access(conversation)
    body = str(body or "").strip()
    if not body or len(body) > 4000:
        frappe.throw(_("内部备注不能为空且不能超过 4000 个字符"), frappe.ValidationError)
    message = frappe.get_doc(
        {
            "doctype": "WhatsApp Message",
            "conversation": name,
            "direction": "内部备注",
            "message_type": "text",
            "body": body,
            "sender_user": frappe.session.user,
            "status": "已记录",
        }
    )
    message.insert(ignore_permissions=True)
    return get_conversation(name)


@frappe.whitelist()
def set_reminder(name, reminder_at, note=None):
    _require_support()
    conversation = _require_conversation(name)
    _require_full_access(conversation)
    try:
        reminder_at = get_datetime(reminder_at)
    except (TypeError, ValueError, OverflowError):
        reminder_at = None
    if not reminder_at or reminder_at <= now_datetime():
        frappe.throw(_("提醒时间必须晚于当前时间"), frappe.ValidationError)
    conversation.next_reminder_at = reminder_at
    conversation.reminder_note = str(note or "").strip()[:500]
    conversation.reminder_notified_at = None
    conversation.save(ignore_permissions=True)
    todo = frappe.get_doc(
        {
            "doctype": "ToDo",
            "allocated_to": conversation.assigned_to or frappe.session.user,
            "reference_type": "WhatsApp Conversation",
            "reference_name": name,
            "description": conversation.reminder_note or "WhatsApp 客户跟进提醒",
            "date": reminder_at.date(),
            "priority": "Medium",
        }
    )
    todo.insert(ignore_permissions=True)
    return _conversation_row(conversation, full=True)


@frappe.whitelist()
def send_message(name, body, client_message_id=None):
    _require_support()
    conversation = _require_conversation(name)
    _require_full_access(conversation)
    body = str(body or "").strip()
    if not body or len(body) > 4096:
        frappe.throw(_("消息不能为空且不能超过 4096 个字符"), frappe.ValidationError)
    if not service_window_open(get_datetime(conversation.service_window_until)):
        frappe.throw(_("客户服务窗口已结束，第一版暂不支持模板消息"), frappe.ValidationError)

    client_message_id = str(client_message_id or "").strip()[:100]
    if client_message_id:
        existing = frappe.db.get_value(
            "WhatsApp Message",
            {"conversation": name, "client_message_id": client_message_id},
            "name",
        )
        if existing:
            return {"state": "queued", "message": existing}

    message = frappe.get_doc(
        {
            "doctype": "WhatsApp Message",
            "conversation": name,
            "direction": "员工消息",
            "message_type": "text",
            "body": body,
            "sender_user": frappe.session.user,
            "client_message_id": client_message_id,
            "status": "排队中",
        }
    )
    message.insert(ignore_permissions=True)
    frappe.enqueue(
        "solua_home.api.whatsapp._send_queued_message",
        queue="short",
        message_name=message.name,
    )
    return {"state": "queued", "message": message.name}


def _send_queued_message(message_name):
    message = frappe.get_doc("WhatsApp Message", message_name)
    conversation = frappe.get_doc("WhatsApp Conversation", message.conversation)
    try:
        response = _send_text(conversation.wa_id, message.body)
        provider_message_id = ((response.get("messages") or [{}])[0]).get("id")
        message.provider_message_id = provider_message_id or ""
        message.status = "已发送"
        message.status_at = now_datetime()
        message.error_message = ""
    except Exception as exc:
        message.status = "失败"
        message.status_at = now_datetime()
        message.error_message = str(exc)[:500]
    message.save(ignore_permissions=True)
    conversation.last_message_at = now_datetime()
    conversation.last_message_preview = message.body
    conversation.save(ignore_permissions=True)


def notify_due_reminders():
    now = now_datetime()
    rows = frappe.get_all(
        "WhatsApp Conversation",
        filters={
            "next_reminder_at": ["<=", now],
            "reminder_notified_at": ["is", "not set"],
            "assigned_to": ["is", "set"],
        },
        fields=["name", "assigned_to", "reminder_note"],
        limit_page_length=200,
    )
    for row in rows:
        frappe.publish_realtime(
            "whatsapp_reminder_due",
            {"conversation": row.name, "note": row.reminder_note or ""},
            user=row.assigned_to,
        )
        frappe.db.set_value(
            "WhatsApp Conversation", row.name, "reminder_notified_at", now
        )
    return len(rows)
