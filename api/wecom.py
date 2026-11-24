"""Enterprise WeChat group-bot delivery for customer-facing documents."""

import re
from urllib.parse import parse_qs, urlparse

import frappe
from frappe import _


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


def _invoice_30_day_digest(today):
    from frappe.utils import add_days

    posting_date = add_days(today, -30)
    invoices = frappe.get_all(
        "Sales Invoice",
        filters={
            "docstatus": 1,
            "is_return": 0,
            "posting_date": posting_date,
            "outstanding_amount": [">", 0],
        },
        fields=["name", "customer", "customer_name"],
        order_by="customer_name asc, name asc",
    )
    if not invoices:
        return None

    lines = [f"{today}｜开票满 30 天仍未结清：{len(invoices)} 张"]
    footer = f"余额请在 ERP 查看（开票日 {posting_date}）。"
    for index, invoice in enumerate(invoices):
        customer = " ".join((invoice.customer_name or invoice.customer).split())
        line = f"{customer}｜{invoice.name}"
        overflow = f"另有 {len(invoices) - index} 张。"
        if len("\n".join([*lines, line, overflow, footer]).encode("utf-8")) > 2000:
            lines.append(overflow)
            break
        lines.append(line)
    return "\n".join([*lines, footer])


def send_invoice_30_day_reminder():
    """Send one internal group digest when submitted invoices first reach day 30."""
    import requests
    from frappe.defaults import set_global_default
    from frappe.utils import nowdate
    from frappe.utils.synchronization import filelock

    today = nowdate()
    key = "solua_wecom_invoice_30_day_sent_on"
    with filelock(key):
        if frappe.db.get_value("DefaultValue", {"parent": "__default", "defkey": key}, "defvalue") == today:
            return
        content = _invoice_30_day_digest(today)
        if not content:
            return

        try:
            response = requests.post(
                _webhook_config()[0],
                json={"msgtype": "text", "text": {"content": content}},
                timeout=20,
            )
        except requests.RequestException:
            raise RuntimeError("企业微信群机器人请求失败") from None
        payload = _response_json(response, "发票提醒")
        if payload.get("errcode") not in (0, "0"):
            frappe.throw("企业微信群机器人未确认发送发票提醒")
        set_global_default(key, today)
        frappe.db.commit()


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


def _sales_order_export_values(doc):
    header_fields = {
        "customer", "customer_name", "company", "transaction_date", "delivery_date", "po_no", "po_date",
        "customer_address", "shipping_address_name", "address_display", "shipping_address", "contact_person",
        "contact_display", "contact_mobile", "currency", "grand_total", "net_total", "discount_amount",
        "payment_terms_template", "terms",
    }
    header_fields.update(
        field.fieldname for field in doc.meta.fields
        if field.allow_on_submit and field.fieldtype not in ("Table", "Table MultiSelect")
        and not field.fieldname.startswith("custom_wecom_")
    )
    row_fields = (
        "item_code", "item_name", "description", "qty", "uom", "conversion_factor", "warehouse",
        "delivery_date", "rate", "amount", "additional_notes", "pos_additional_notes", "custom_additional_notes",
    )
    return (
        {field: doc.get(field) for field in header_fields},
        [tuple(row.get(field) for field in row_fields) for row in doc.get("items", [])],
    )


def enqueue_sales_order_update_send(doc, method=None, previous=None):
    # The Update Items override writes notes after the parent save.
    if previous is None:
        if frappe.flags.get("_solua_stock_previous_doc"):
            return
        previous = doc.get_doc_before_save()
    if previous is not None and _sales_order_export_values(doc) == _sales_order_export_values(previous):
        return
    enqueue_sales_order_submit_send(doc, updated=True)


_SALES_ORDER_AUTO_SEND_KEY = "solua_wecom_sales_order_auto_send"


def _sales_order_auto_send_enabled():
    value = frappe.db.get_value(
        "DefaultValue", {"parent": "__default", "defkey": _SALES_ORDER_AUTO_SEND_KEY}, "defvalue"
    )
    return value != "0"


@frappe.whitelist()
def get_sales_order_auto_send():
    frappe.only_for("System Manager")
    return _sales_order_auto_send_enabled()


@frappe.whitelist(methods=["POST"])
def set_sales_order_auto_send(enabled):
    from frappe.defaults import set_global_default

    frappe.only_for("System Manager")
    value = str(enabled)
    if value not in ("0", "1"):
        frappe.throw(_("自动发送设置无效"))
    set_global_default(_SALES_ORDER_AUTO_SEND_KEY, value)
    return value == "1"


def enqueue_sales_order_submit_send(doc, method=None, *, updated=False):
    """Queue both customer files after a Sales Order transaction commits."""
    if doc.doctype != "Sales Order" or int(doc.docstatus or 0) != 1:
        return
    if not _sales_order_auto_send_enabled():
        return
    job_id = f"wecom-sales-order-submit:{doc.name}"
    if updated:
        job_id = f"wecom-sales-order-update:{doc.name}:{doc.modified}"
    frappe.enqueue(
        "solua_home.api.wecom.send_submitted_sales_order_to_wechat",
        queue="short",
        enqueue_after_commit=True,
        job_id=job_id,
        deduplicate=True,
        sales_order=doc.name,
        updated=updated,
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


def _send_with_retries(sender, doc, filename):
    import time

    last_error = None
    for attempt in range(3):
        try:
            return sender(doc, filename)
        except Exception as error:
            last_error = error
            if attempt < 2:
                time.sleep(2 ** attempt)
    raise last_error


def send_submitted_sales_order_to_wechat(sales_order, updated=False):
    """Send a PDF and XLSX from the same saved order version."""
    from frappe.utils.synchronization import filelock
    from solua_home.api.export import _sales_order_customer_pdf_filename

    with filelock(f"wecom-sales-order:{sales_order}", timeout=120):
        if not _sales_order_auto_send_enabled():
            return {"status": "skipped", "reason": "auto send disabled"}
        doc = frappe.get_doc("Sales Order", sales_order)
        if not updated and doc.get("custom_wecom_send_status") == "已发送":
            return {"status": "already sent"}
        if int(doc.docstatus or 0) != 1:
            return {"status": "skipped", "reason": "not submitted"}
        doc.check_permission("read")
        stem = _sales_order_customer_pdf_filename(doc)[:-4]
        if updated:
            from solua_home.printing.wholesale import _collect

            # Refresh the print snapshot in memory, including notes that were cleared.
            doc.custom_wholesale_snapshot = frappe.as_json(_collect(doc, use_snapshot=False))
        return _send_sales_order_files(doc, stem)


def _send_sales_order_files(doc, stem):
    sales_order = doc.name
    _set_sales_order_wecom_status(sales_order, "发送中")
    results, errors = _deliver_sales_order_files(doc, stem, retry=True)

    if errors:
        status = "部分成功" if results else "失败"
        message = "; ".join(errors)[:2000]
        _set_sales_order_wecom_status(sales_order, status, message)
        frappe.log_error(message, f"Sales Order WeCom send failed: {sales_order}")
        return {"status": status, "results": results, "errors": errors}

    _set_sales_order_wecom_status(sales_order, "已发送", sent_at=frappe.utils.now_datetime())
    return {"status": "sent", "results": results}


def _deliver_sales_order_files(doc, stem, *, retry=False):
    results = {}
    errors = []
    for label, sender in (("PDF", _send_sales_order_pdf), ("XLSX", _send_sales_order_xlsx)):
        filename = f"{stem}.{label.lower()}"
        try:
            results[label] = _send_with_retries(sender, doc, filename) if retry else sender(doc, filename)
        except Exception as error:
            if not retry:
                # Transport exceptions can contain the private webhook URL.
                error = type(error).__name__
            errors.append(f"{label}: {error}")
    return results, errors


@frappe.whitelist(methods=["POST"])
def send_sales_order_customer_files_to_wechat(name):
    from solua_home.api.export import _sales_order_customer_pdf_filename, get_export_document

    doc = get_export_document("Sales Order", name)
    results, errors = _deliver_sales_order_files(doc, _sales_order_customer_pdf_filename(doc)[:-4])
    if errors:
        frappe.log_error(", ".join(errors), f"Manual Sales Order WeCom send failed: {doc.name}")
    return {"results": results, "failed": [label for label in ("PDF", "XLSX") if label not in results]}


@frappe.whitelist()
def send_sales_order_customer_pdf_to_wechat(name):
    from solua_home.api.export import _sales_order_customer_pdf_filename, get_export_document

    doc = get_export_document("Sales Order", name)
    return _send_sales_order_pdf(doc, _sales_order_customer_pdf_filename(doc))


def _send_sales_order_pdf(doc, filename):
    webhook_url, key = _webhook_config()

    from solua_home.api.a4_designer import _active_print_format
    from solua_home.api.export import _render_document_pdf
    print_format = _active_print_format("Sales Order")
    if not print_format:
        frappe.throw("销售订单没有可用的打印格式")
    merge_customer = bool(int(doc.get("custom_print_merge_order_code") or 0))
    pdf = _render_document_pdf(doc, print_format, merge_customer=merge_customer)
    return _send_file(webhook_url, key, filename, pdf, "application/pdf")


@frappe.whitelist()
def send_sales_order_customer_xlsx_to_wechat(name):
    from solua_home.api.export import _sales_order_customer_pdf_filename, get_export_document

    doc = get_export_document("Sales Order", name)
    return _send_sales_order_xlsx(doc, f"{_sales_order_customer_pdf_filename(doc)[:-4]}.xlsx")


def _send_sales_order_xlsx(doc, filename):
    webhook_url, key = _webhook_config()
    from solua_home.api.export import _customer_sales_order_table, _xlsx_bytes
    merge_customer = bool(int(doc.get("custom_print_merge_order_code") or 0))
    xlsx = _xlsx_bytes(_customer_sales_order_table(doc, merge_customer=merge_customer), "客户表格", wrap_columns=(3,))
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

    from solua_home.api.export import _selected_columns, _xlsx_bytes, build_table, get_export_document

    doc = get_export_document(doctype, name)
    selected = _selected_columns(doctype, None)
    wrap_columns = (selected.index("description"),) if "description" in selected else ()
    xlsx = _xlsx_bytes(build_table(doc, selected), "单据表格", wrap_columns=wrap_columns)
    return _send_file(
        webhook_url,
        key,
        f"{name}.xlsx",
        xlsx,
        "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    )


def _template_stock_tree_table(filters):
    """Convert the current Template Stock Tree report result to an XLSX table."""
    from solua_home.solua_wholesale.report.template_stock_tree.template_stock_tree import execute
    from frappe.utils import flt

    columns, rows = execute(filters)
    fields = [column["fieldname"] for column in columns]
    numeric_fields = {
        column["fieldname"] for column in columns if column.get("fieldtype") == "Float"
    }
    table = [
        [_("公司"), filters.get("company") or ""],
        [_("仓库"), filters.get("warehouse") or _("全部有权限仓库")],
        [_("开始日期"), filters.get("from_date") or ""],
        [_("截止日期"), filters.get("to_date") or ""],
        [],
        [column.get("label") or field for column, field in zip(columns, fields)],
    ]
    for row in rows:
        values = []
        for field in fields:
            value = row.get(field)
            if field == "item_name" and value:
                value = f"{'  ' * int(row.get('indent') or 0)}{value}"
            elif field in numeric_fields:
                value = flt(value or 0)
                if float(value).is_integer():
                    value = int(value)
            values.append("" if value is None else value)
        table.append(values)
    return table


@frappe.whitelist()
def send_template_stock_tree_xlsx_to_wechat(filters=None):
    """Send the current, permission-filtered Template Stock Tree as an XLSX file."""
    if not any(role in frappe.get_roles() for role in ("Stock User", "Stock Manager", "System Manager")):
        frappe.throw("没有库存树报表权限", frappe.PermissionError)

    webhook_url, key = _webhook_config()
    filters = frappe.parse_json(filters) if isinstance(filters, str) else (filters or {})
    if not isinstance(filters, dict):
        frappe.throw("库存树报表筛选条件无效")

    from solua_home.api.export import _xlsx_bytes
    from frappe.utils import nowdate

    table = _template_stock_tree_table(frappe._dict(filters))
    filename = f"库存树_{nowdate().replace('-', '')}.xlsx"
    xlsx = _xlsx_bytes(table, "库存树报表")
    return _send_file(
        webhook_url,
        key,
        filename,
        xlsx,
        "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    )


QUERY_REPORT_WECHAT_ALLOWLIST = {
    "Stock Balance",
    "Stock Ledger",
    "Sales Order Analysis",
    "Sales Register",
    "Item-wise Sales Register",
    "Accounts Receivable",
    "Accounts Receivable Summary",
    "General Ledger",
    "Item-wise Sales History",
    "Profitability Analysis",
    "Solua Business Totals",
    "Solua Delivery Summary",
}


def _query_report_xlsx_table(report_name, filters):
    from frappe.desk.query_report import generate_report_result, get_report_doc
    from frappe.utils import flt, strip_html

    report = get_report_doc(report_name)
    result = generate_report_result(report, filters=filters, is_tree=bool(report.get("tree")))
    columns = result.get("columns") or []
    rows = result.get("result") or []
    fields = [column.get("fieldname") for column in columns]
    numeric_fields = {
        column.get("fieldname")
        for column in columns
        if column.get("fieldtype") in ("Int", "Float", "Currency", "Percent")
    }
    text_fields = [field for field in fields if field and field not in numeric_fields]
    table = [[_("报表"), report_name]]
    for key, value in filters.items():
        if value not in (None, ""):
            table.append([str(key), str(value)])
    table.extend([[], [column.get("label") or field for column, field in zip(columns, fields)]])
    for row in rows:
        if not isinstance(row, dict):
            row = dict(zip(fields, row))
        values = []
        for field in fields:
            value = row.get(field)
            if field == text_fields[0] and value and row.get("indent"):
                value = f"{'  ' * int(row.get('indent') or 0)}{value}"
            if isinstance(value, str) and "<" in value:
                value = strip_html(value)
            if field in numeric_fields:
                value = flt(value or 0)
                if float(value).is_integer():
                    value = int(value)
            values.append("" if value is None else value)
        table.append(values)
    return table


@frappe.whitelist()
def send_query_report_xlsx_to_wechat(report_name, filters=None):
    """Send an allowed report's current filtered result as an XLSX file."""
    if report_name not in QUERY_REPORT_WECHAT_ALLOWLIST:
        frappe.throw("该报表暂不支持发送到微信")
    webhook_url, key = _webhook_config()
    filters = frappe.parse_json(filters) if isinstance(filters, str) else (filters or {})
    if not isinstance(filters, dict):
        frappe.throw("报表筛选条件无效")

    from frappe.utils import nowdate
    from solua_home.api.export import _xlsx_bytes

    table = _query_report_xlsx_table(report_name, frappe._dict(filters))
    stem = re.sub(r'[<>:"/\\|?*\x00-\x1f]+', "_", report_name).strip(" .")
    filename = f"{stem}_{nowdate().replace('-', '')}.xlsx"
    xlsx = _xlsx_bytes(table, "报表")
    return _send_file(
        webhook_url,
        key,
        filename,
        xlsx,
        "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    )
