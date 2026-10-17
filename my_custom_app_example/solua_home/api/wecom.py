"""Enterprise WeChat group-bot delivery for customer-facing documents."""

from urllib.parse import parse_qs, urlparse

import frappe


def _response_json(response, action):
    try:
        payload = response.json()
    except Exception:
        frappe.throw(f"企业微信{action}返回了无效响应")
    if response.status_code >= 400 or payload.get("errcode") not in (0, "0", None):
        frappe.throw(f"企业微信{action}失败：{payload.get('errmsg') or response.status_code}")
    return payload


def _webhook_config():
    webhook_url = (frappe.conf.get("solua_wecom_webhook_url") or "").strip()
    parsed = urlparse(webhook_url)
    if parsed.scheme != "https" or parsed.netloc != "qyapi.weixin.qq.com" or parsed.path != "/cgi-bin/webhook/send":
        frappe.throw("未配置有效的企业微信群机器人 webhook")
    key = parse_qs(parsed.query).get("key", [""])[0]
    if not key:
        frappe.throw("企业微信群机器人 webhook 缺少 key")
    return webhook_url, key


def _send_file(webhook_url, key, filename, content, content_type):
    import requests

    upload = requests.post(
        "https://qyapi.weixin.qq.com/cgi-bin/webhook/upload_media",
        params={"key": key, "type": "file"},
        files={"media": (filename, content, content_type)},
        timeout=30,
    )
    upload_payload = _response_json(upload, "文件上传")
    media_id = upload_payload.get("media_id")
    if not media_id:
        frappe.throw("企业微信文件上传未返回 media_id")

    sent = requests.post(
        webhook_url,
        json={"msgtype": "file", "file": {"media_id": media_id}},
        timeout=30,
    )
    _response_json(sent, "消息发送")
    return {"filename": filename}


@frappe.whitelist()
def send_sales_order_customer_pdf_to_wechat(name):
    webhook_url, key = _webhook_config()

    from solua_home.api.a4_designer import _active_print_format
    from solua_home.api.export import (
        _render_document_pdf,
        _sales_order_customer_pdf_filename,
        get_export_document,
    )

    doc = get_export_document("Sales Order", name)
    print_format = _active_print_format("Sales Order")
    if not print_format:
        frappe.throw("销售订单没有可用的打印格式")
    pdf = _render_document_pdf(doc, print_format, merge_customer=True)
    filename = _sales_order_customer_pdf_filename(doc)
    return _send_file(webhook_url, key, filename, pdf, "application/pdf")


@frappe.whitelist()
def send_sales_order_customer_xlsx_to_wechat(name):
    webhook_url, key = _webhook_config()
    from solua_home.api.export import (
        _customer_sales_order_table,
        _sales_order_customer_pdf_filename,
        _xlsx_bytes,
        get_export_document,
    )

    doc = get_export_document("Sales Order", name)
    filename = f"{_sales_order_customer_pdf_filename(doc)[:-4]}.xlsx"
    xlsx = _xlsx_bytes(_customer_sales_order_table(doc), "客户表格")
    return _send_file(
        webhook_url,
        key,
        filename,
        xlsx,
        "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    )
