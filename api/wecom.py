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


def apply_customer_print_preference(doc, method=None):
    """Copy the customer's default merge choice into a new or reassigned Sales Order."""
    if doc.doctype != "Sales Order" or not doc.get("customer"):
        return
    if not (doc.is_new() or doc.has_value_changed("customer")):
        return
    if not frappe.get_meta("Sales Order").has_field("custom_print_merge_order_code"):
        return
    if not frappe.get_meta("Customer").has_field("custom_print_merge_order_code_default"):
        return
    preference = frappe.db.get_value("Customer", doc.customer, "custom_print_merge_order_code_default")
    doc.custom_print_merge_order_code = 0 if preference == "不合并货号" else 1


def enqueue_sales_order_submit_send(doc, method=None):
    """Queue both customer files after a Sales Order transaction commits."""
    if doc.doctype != "Sales Order" or int(doc.docstatus or 0) != 1:
        return
    frappe.enqueue(
        "solua_home.api.wecom.send_submitted_sales_order_to_wechat",
        queue="short",
        enqueue_after_commit=True,
        job_id=f"wecom-sales-order-submit:{doc.name}",
        deduplicate=True,
        sales_order=doc.name,
    )


def _set_sales_order_wecom_status(name, status, error="", sent_at=None):
    frappe.db.set_value(
        "Sales Order",
        name,
        {
            "custom_wecom_send_status": status,
            "custom_wecom_send_error": error or "",
            "custom_wecom_sent_at": sent_at,
        },
        update_modified=False,
    )
    frappe.db.commit()


def _send_with_retries(sender, name):
    import time

    last_error = None
    for attempt in range(3):
        try:
            return sender(name)
        except Exception as error:
            last_error = error
            if attempt < 2:
                time.sleep(2 ** attempt)
    raise last_error


def send_submitted_sales_order_to_wechat(sales_order):
    """Send submitted Sales Order PDF and XLSX without affecting order submission."""
    doc = frappe.get_doc("Sales Order", sales_order)
    if int(doc.docstatus or 0) != 1:
        return {"status": "skipped", "reason": "not submitted"}
    if doc.get("custom_wecom_send_status") == "已发送":
        return {"status": "already sent"}

    _set_sales_order_wecom_status(sales_order, "发送中")
    results = {}
    errors = []
    for label, sender in (
        ("PDF", send_sales_order_customer_pdf_to_wechat),
        ("XLSX", send_sales_order_customer_xlsx_to_wechat),
    ):
        try:
            results[label] = _send_with_retries(sender, sales_order)
        except Exception as error:
            errors.append(f"{label}: {error}")

    if errors:
        status = "部分成功" if results else "失败"
        message = "; ".join(errors)[:2000]
        _set_sales_order_wecom_status(sales_order, status, message)
        frappe.log_error(message, f"Sales Order WeCom send failed: {sales_order}")
        return {"status": status, "results": results, "errors": errors}

    _set_sales_order_wecom_status(sales_order, "已发送", sent_at=frappe.utils.now_datetime())
    return {"status": "sent", "results": results}


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
    merge_customer = bool(int(doc.get("custom_print_merge_order_code") or 0))
    pdf = _render_document_pdf(doc, print_format, merge_customer=merge_customer)
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
    merge_customer = bool(int(doc.get("custom_print_merge_order_code") or 0))
    xlsx = _xlsx_bytes(_customer_sales_order_table(doc, merge_customer=merge_customer), "客户表格")
    return _send_file(
        webhook_url,
        key,
        filename,
        xlsx,
        "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    )


@frappe.whitelist()
def send_document_pdf_to_wechat(doctype, name):
    """Send a Delivery Note, Pick List, or Sales Invoice PDF to the group bot."""
    if doctype not in ("Delivery Note", "Pick List", "Sales Invoice"):
        frappe.throw("只支持发送交货单、拣货单和销售发票")
    webhook_url, key = _webhook_config()

    from solua_home.api.a4_designer import _active_print_format
    from solua_home.api.export import _render_document_pdf, get_export_document

    doc = get_export_document(doctype, name)
    print_format = _active_print_format(doctype)
    if not print_format:
        frappe.throw(f"{doctype}没有可用的打印格式")
    pdf = _render_document_pdf(
        doc,
        print_format,
        merge_customer=doctype == "Delivery Note",
        doctype=doctype,
    )
    return _send_file(webhook_url, key, f"{name}.pdf", pdf, "application/pdf")


@frappe.whitelist()
def send_document_xlsx_to_wechat(doctype, name):
    """Send the standard item table for a Delivery Note, Pick List, or invoice."""
    if doctype not in ("Delivery Note", "Pick List", "Sales Invoice"):
        frappe.throw("只支持发送交货单、拣货单和销售发票")
    webhook_url, key = _webhook_config()

    from solua_home.api.export import _xlsx_bytes, build_table, get_export_document

    doc = get_export_document(doctype, name)
    xlsx = _xlsx_bytes(build_table(doc), "单据表格")
    return _send_file(
        webhook_url,
        key,
        f"{name}.xlsx",
        xlsx,
        "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    )
