from hmac import compare_digest

import frappe

PDF_DOCTYPES = {"Sales Order", "Stock Entry", "Purchase Receipt", "Delivery Note", "Sales Invoice", "Payment Entry"}

def _safe(value):
    from solua_home.api.export import _safe_sales_order_filename
    return _safe_sales_order_filename(value)

def _telegram_pdf_filename(doc):
    from solua_home.api.export import _document_date, _sales_order_customer_pdf_filename
    if doc.doctype == "Sales Order":
        return _sales_order_customer_pdf_filename(doc)
    labels = {"Delivery Note": "\u4ea4\u8d27\u5355", "Sales Invoice": "\u9500\u552e\u53d1\u7968", "Purchase Receipt": "\u91c7\u8d2d\u5165\u5e93", "Stock Entry": "\u5e93\u5b58\u4e8b\u52a1", "Payment Entry": "\u4ed8\u6b3e\u767b\u8bb0"}
    date = _document_date(doc, "posting_date")
    party = doc.get("customer_name") or doc.get("customer") or doc.get("supplier_name") or doc.get("supplier") or doc.get("party_name") or doc.get("party")
    parts = [date, _safe(doc.name)]
    if party:
        parts.append(_safe(party))
    parts.append(labels.get(doc.doctype, _safe(doc.doctype)))
    return "_".join(parts) + ".pdf"

def _config():
    token = (frappe.conf.get("solua_telegram_bot_token") or "").strip()
    chat_id = (frappe.conf.get("solua_telegram_chat_id") or "").strip()
    if not token or not chat_id:
        frappe.throw("Telegram bot is not configured")
    return token, chat_id

def _render_pdf(doctype, name):
    from solua_home.api.a4_designer import DOCTYPE_CONFIG, _active_print_format
    from solua_home.api.export import _render_document_pdf

    doc = frappe.get_doc(doctype, name)
    if doc.docstatus != 1:
        frappe.throw("Only submitted documents can be sent to Telegram")
    if doctype not in DOCTYPE_CONFIG:
        print_format = frappe.get_meta(doctype).default_print_format or "Standard"
        return doc, frappe.get_print(doctype, name, print_format, doc=doc, as_pdf=True)
    print_format = _active_print_format(doctype) or "Standard"
    return doc, _render_document_pdf(doc, print_format, merge_customer=doctype in {"Sales Order", "Delivery Note"}, doctype=doctype)

def send_document_pdf(doctype, name):
    import requests
    frappe.set_user("Administrator")
    if doctype not in PDF_DOCTYPES:
        return {"status": "skipped", "reason": "doctype not supported"}
    doc, pdf = _render_pdf(doctype, name)
    token, chat_id = _config()
    filename = _telegram_pdf_filename(doc)
    try:
        response = requests.post(
            f"https://api.telegram.org/bot{token}/sendDocument",
            data={"chat_id": chat_id, "caption": f"{doctype} {name}"},
            files={"document": (filename, pdf, "application/pdf")},
            timeout=60,
        )
        payload = response.json()
    except (requests.RequestException, ValueError) as exc:
        raise RuntimeError(f"Telegram sendDocument failed ({type(exc).__name__})") from None
    if response.status_code >= 400 or not payload.get("ok"):
        raise RuntimeError(f"Telegram sendDocument failed (HTTP {response.status_code})")
    message = payload["result"]
    if str(message["chat"]["id"]) != chat_id or not message.get("document"):
        raise RuntimeError("Telegram did not confirm a document in the configured chat")
    return {"status": "sent", "doctype": doctype, "name": name, "filename": filename, "message_id": message["message_id"]}

def _webhook_secret():
    return (frappe.conf.get("solua_telegram_webhook_secret") or "").strip()

@frappe.whitelist(allow_guest=True, methods=["POST"])
def webhook(secret=None):
    secret = secret or frappe.request.args.get("secret")
    configured_secret = _webhook_secret()
    if not configured_secret or not isinstance(secret, str) or not compare_digest(secret.encode(), configured_secret.encode()):
        frappe.local.response.http_status_code = 403
        return {"ok": False, "error": "invalid secret"}
    # Frappe Webhooks can send JSON without a Content-Type header.
    payload = frappe.request.get_json(force=True, silent=True)
    if not isinstance(payload, dict):
        frappe.local.response.http_status_code = 400
        return {"ok": False, "queued": False}
    doctype, name = payload.get("doctype"), payload.get("name")
    if not isinstance(doctype, str) or doctype not in PDF_DOCTYPES or not isinstance(name, str) or not name.strip():
        frappe.local.response.http_status_code = 400
        return {"ok": False, "queued": False}
    frappe.enqueue("solua_home.api.telegram.send_document_pdf", queue="short", enqueue_after_commit=True, job_id=f"telegram-pdf:{doctype}:{name}", deduplicate=True, doctype=doctype, name=name)
    return {"ok": True, "queued": True, "doctype": doctype, "name": name}


def send_weekly_reports():
    """Send all enabled weekly Auto Email Reports to the Telegram management group."""
    import requests
    from frappe.utils import nowdate
    from frappe.utils.pdf import get_pdf
    frappe.set_user("Administrator")
    token, chat_id = _config()
    results = []
    reports = frappe.get_all("Auto Email Report", filters={"enabled": 1, "frequency": "Weekly"}, pluck="name", order_by="name asc")
    for report_name in reports:
        report = frappe.get_doc("Auto Email Report", report_name)
        html = report.get_report_content()
        if not html:
            continue
        pdf = get_pdf(f"<html><head><meta charset='utf-8'></head><body>{html}</body></html>")
        filename = f"\u5468\u62a5_{_safe(report_name)}_{nowdate().replace('-', '')}.pdf"
        response = requests.post(f"https://api.telegram.org/bot{token}/sendDocument", data={"chat_id": chat_id, "caption": f"\u5468\u62a5 {report_name}"}, files={"document": (filename, pdf, "application/pdf")}, timeout=90)
        payload = response.json()
        if response.status_code >= 400 or not payload.get("ok"):
            raise RuntimeError(f"Telegram weekly report failed: {payload}")
        results.append(filename)
    return {"status": "sent", "files": results}


def send_weekly_reports():
    """Send enabled weekly Auto Email Reports as Excel tables to Telegram."""
    import requests
    from frappe.utils import nowdate
    frappe.set_user("Administrator")
    token, chat_id = _config()
    results = []
    reports = frappe.get_all("Auto Email Report", filters={"enabled": 1, "frequency": "Weekly"}, pluck="name", order_by="name asc")
    for report_name in reports:
        report = frappe.get_doc("Auto Email Report", report_name)
        report.format = "XLSX"
        content = report.get_report_content()
        if not content:
            continue
        filename = f"\u5468\u62a5_{_safe(report_name)}_{nowdate().replace('-', '')}.xlsx"
        response = requests.post(f"https://api.telegram.org/bot{token}/sendDocument", data={"chat_id": chat_id, "caption": f"\u5468\u62a5 {report_name}"}, files={"document": (filename, content, "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")}, timeout=90)
        payload = response.json()
        if response.status_code >= 400 or not payload.get("ok"):
            raise RuntimeError(f"Telegram weekly report failed: {payload}")
        results.append(filename)
    return {"status": "sent", "files": results}


def enqueue_payment_margin_check(doc, method=None):
    if doc.doctype != "Payment Entry" or doc.get("payment_type") != "Receive":
        return
    frappe.enqueue("solua_home.api.telegram.send_payment_margin_check", queue="short", enqueue_after_commit=True, job_id=f"telegram-payment-margin:{doc.name}", deduplicate=True, payment_entry=doc.name)

def send_payment_margin_check(payment_entry):
    import requests
    from frappe.utils import flt
    frappe.set_user("Administrator")
    doc = frappe.get_doc("Payment Entry", payment_entry)
    discount_account = "Discount Allowed - SH"
    discount = sum(abs(flt(row.amount)) for row in doc.get("deductions") or [] if row.account == discount_account)
    if not discount:
        return {"status": "skipped", "reason": "no cash discount"}
    refs = [row for row in doc.get("references") or [] if row.reference_doctype == "Sales Invoice" and row.reference_name]
    if not refs:
        return {"status": "skipped", "reason": "no invoice reference"}
    total_allocated = sum(abs(flt(row.allocated_amount)) for row in refs) or 1
    lines = [f"\u73b0\u4ed8\u6298\u6263\u540e\u6bdb\u5229\u590d\u6838: {doc.name}", f"\u73b0\u91d1\u6298\u6263: {discount:.2f}"]
    for ref in refs:
        invoice = frappe.get_doc("Sales Invoice", ref.reference_name)
        groups = {}
        invoice_sales = 0
        for item in invoice.items:
            sales = flt(item.base_net_amount or item.base_amount)
            cost_rate = flt(item.incoming_rate or item.valuation_rate)
            cost = cost_rate * abs(flt(item.stock_qty or item.qty))
            order = item.sales_order or invoice.name
            group = groups.setdefault(order, {"sales": 0, "cost": 0})
            group["sales"] += sales
            group["cost"] += cost
            invoice_sales += sales
        ref_discount = discount * abs(flt(ref.allocated_amount)) / total_allocated
        for order, values in groups.items():
            order_discount = ref_discount * values["sales"] / invoice_sales if invoice_sales else 0
            adjusted_sales = values["sales"] - order_discount
            margin = (adjusted_sales - values["cost"]) / adjusted_sales * 100 if adjusted_sales else 0
            lines.append(f"{order} | {invoice.name} | \u6298\u540e\u9500\u552e {adjusted_sales:.2f} | \u6bdb\u5229\u7387 {margin:.2f}%")
    token, chat_id = _config()
    response = requests.post(f"https://api.telegram.org/bot{token}/sendMessage", data={"chat_id": chat_id, "text": "\n".join(lines)}, timeout=30)
    payload = response.json()
    if response.status_code >= 400 or not payload.get("ok"):
        raise RuntimeError(f"Telegram payment margin check failed: {payload}")
    return {"status": "sent", "payment_entry": payment_entry}


def _send_xlsx_to_telegram(filename, content, caption):
    import requests
    token, chat_id = _config()
    response = requests.post(f"https://api.telegram.org/bot{token}/sendDocument", data={"chat_id": chat_id, "caption": caption}, files={"document": (filename, content, "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")}, timeout=90)
    payload = response.json()
    if response.status_code >= 400 or not payload.get("ok"):
        raise RuntimeError(f"Telegram XLSX report failed: {payload}")

def send_weekly_financial_reports():
    from frappe.utils import add_days, nowdate, flt
    from frappe.utils.xlsxutils import make_xlsx
    frappe.set_user("Administrator")
    start, end = add_days(nowdate(), -7), nowdate()
    turnover = frappe.db.sql("""SELECT posting_date, name, customer_name, base_net_total, discount_amount, base_grand_total FROM `tabSales Invoice` WHERE docstatus=1 AND posting_date BETWEEN %s AND %s ORDER BY posting_date, name""", (start, end), as_dict=True)
    turnover_rows = [["Date", "Invoice", "Customer", "Net Sales", "Discount", "Grand Total"]] + [[r.posting_date, r.name, r.customer_name, flt(r.base_net_total), flt(r.discount_amount), flt(r.base_grand_total)] for r in turnover]
    date_tag = nowdate().replace("-", "")
    _send_xlsx_to_telegram(f"\u6bcf\u5468\u8425\u4e1a\u989d_{date_tag}.xlsx", make_xlsx(turnover_rows, "Weekly Turnover").getvalue(), "\u6bcf\u5468\u8425\u4e1a\u989d")
    margins = frappe.db.sql("""SELECT si.posting_date, COALESCE(sii.sales_order, si.name) AS order_name, si.name AS invoice, si.customer_name, SUM(sii.base_net_amount) AS sales, SUM(COALESCE(sii.incoming_rate, 0) * ABS(COALESCE(sii.stock_qty, sii.qty))) AS cost FROM `tabSales Invoice` si JOIN `tabSales Invoice Item` sii ON sii.parent=si.name WHERE si.docstatus=1 AND si.posting_date BETWEEN %s AND %s GROUP BY si.posting_date, order_name, si.name, si.customer_name ORDER BY si.posting_date, order_name""", (start, end), as_dict=True)
    margin_rows = [["Date", "Sales Order", "Invoice", "Customer", "Sales", "Cost", "Gross Profit", "Margin %"]]
    for r in margins:
        sales, cost = flt(r.sales), flt(r.cost)
        profit = sales - cost
        margin_rows.append([r.posting_date, r.order_name, r.invoice, r.customer_name, sales, cost, profit, flt(profit / sales * 100, 2) if sales else 0])
    _send_xlsx_to_telegram(f"\u6bcf\u5468\u8ba2\u5355\u6bdb\u5229\u7387_{date_tag}.xlsx", make_xlsx(margin_rows, "Order Gross Margin").getvalue(), "\u6bcf\u5468\u8ba2\u5355\u6bdb\u5229\u7387")
    return {"status": "sent", "turnover_rows": len(turnover), "margin_rows": len(margins)}


def send_weekly_financial_reports():
    from frappe.utils import add_days, nowdate, flt
    from frappe.utils.xlsxutils import make_xlsx
    from frappe.desk.query_report import run
    frappe.set_user("Administrator")
    start, end = add_days(nowdate(), -7), nowdate()
    turnover = frappe.get_all("Sales Invoice", filters={"docstatus": 1, "posting_date": ["between", [start, end]]}, fields=["posting_date", "name", "customer_name", "base_net_total", "discount_amount", "base_grand_total"], order_by="posting_date asc, name asc", limit_page_length=0)
    turnover_rows = [["Date", "Invoice", "Customer", "Net Sales", "Discount", "Grand Total"]] + [[r.posting_date, r.name, r.customer_name, flt(r.base_net_total), flt(r.discount_amount), flt(r.base_grand_total)] for r in turnover]
    date_tag = nowdate().replace("-", "")
    _send_xlsx_to_telegram(f"\u6bcf\u5468\u8425\u4e1a\u989d_{date_tag}.xlsx", make_xlsx(turnover_rows, "Weekly Turnover").getvalue(), "\u6bcf\u5468\u8425\u4e1a\u989d")
    result = run("Gross Profit", filters={"company": "Solua Home, Lda", "from_date": start, "to_date": end, "group_by": "Invoice"}, are_default_filters=False)
    margin_rows = [["Date", "Sales Order", "Invoice", "Customer", "Sales", "Cost", "Gross Profit", "Margin %"]]
    for row in result.get("result") or []:
        if row.get("indent") != 0 or not row.get("sales_invoice") or row.get("sales_invoice") == "Total":
            continue
        invoice = row.get("sales_invoice")
        order = frappe.db.get_value("Sales Invoice Item", {"parent": invoice}, "sales_order") or invoice
        margin_rows.append([row.get("posting_date"), order, invoice, row.get("customer_name") or row.get("customer"), flt(row.get("selling_amount")), flt(row.get("buying_amount")), flt(row.get("gross_profit")), flt(row.get("gross_profit_%"))])
    _send_xlsx_to_telegram(f"\u6bcf\u5468\u8ba2\u5355\u6bdb\u5229\u7387_{date_tag}.xlsx", make_xlsx(margin_rows, "Order Gross Margin").getvalue(), "\u6bcf\u5468\u8ba2\u5355\u6bdb\u5229\u7387")
    return {"status": "sent", "turnover_rows": len(turnover), "margin_rows": len(margin_rows) - 1}

def send_payment_margin_check(payment_entry):
    import requests
    from frappe.utils import flt
    from frappe.desk.query_report import run
    frappe.set_user("Administrator")
    doc = frappe.get_doc("Payment Entry", payment_entry)
    discount = sum(abs(flt(row.amount)) for row in doc.get("deductions") or [] if row.account == "Discount Allowed - SH")
    if not discount:
        return {"status": "skipped", "reason": "no cash discount"}
    refs = [row for row in doc.get("references") or [] if row.reference_doctype == "Sales Invoice" and row.reference_name]
    if not refs:
        return {"status": "skipped", "reason": "no invoice reference"}
    total_allocated = sum(abs(flt(row.allocated_amount)) for row in refs) or 1
    lines = [f"\u73b0\u4ed8\u6298\u6263\u540e\u6bdb\u5229\u590d\u6838: {doc.name}", f"\u73b0\u91d1\u6298\u6263: {discount:.2f}"]
    for ref in refs:
        invoice = frappe.get_doc("Sales Invoice", ref.reference_name)
        result = run("Gross Profit", filters={"company": invoice.company, "from_date": invoice.posting_date, "to_date": invoice.posting_date, "group_by": "Invoice"}, are_default_filters=False)
        row = next((x for x in result.get("result") or [] if x.get("indent") == 0 and x.get("sales_invoice") == invoice.name), None)
        if not row:
            continue
        sales, cost = flt(row.get("selling_amount")), flt(row.get("buying_amount"))
        ref_discount = discount * abs(flt(ref.allocated_amount)) / total_allocated
        adjusted = sales - ref_discount
        margin = (adjusted - cost) / adjusted * 100 if adjusted else 0
        order = frappe.db.get_value("Sales Invoice Item", {"parent": invoice.name}, "sales_order") or invoice.name
        lines.append(f"{order} | {invoice.name} | \u6298\u540e\u9500\u552e {adjusted:.2f} | \u5b9e\u9645\u6210\u672c {cost:.2f} | \u6bdb\u5229\u7387 {margin:.2f}%")
    token, chat_id = _config()
    response = requests.post(f"https://api.telegram.org/bot{token}/sendMessage", data={"chat_id": chat_id, "text": "\n".join(lines)}, timeout=30)
    payload = response.json()
    if response.status_code >= 400 or not payload.get("ok"):
        raise RuntimeError(f"Telegram payment margin check failed: {payload}")
    return {"status": "sent", "payment_entry": payment_entry}


def _autosize_xlsx(content):
    from io import BytesIO
    from openpyxl import load_workbook
    from openpyxl.styles import Alignment
    import unicodedata
    workbook = load_workbook(BytesIO(content))
    for sheet in workbook.worksheets:
        sheet.freeze_panes = "A2"
        sheet.auto_filter.ref = sheet.dimensions
        for column in sheet.columns:
            letter = column[0].column_letter
            max_width = 0
            has_long_text = False
            for cell in column:
                value = "" if cell.value is None else str(cell.value)
                width = sum(2 if unicodedata.east_asian_width(ch) in "WFA" else 1 for ch in value)
                max_width = max(max_width, width)
                has_long_text = has_long_text or width > 60
                cell.alignment = Alignment(horizontal="left", vertical="top", wrap_text=False)
            sheet.column_dimensions[letter].width = min(max(max_width + 2, 10), 45)
            if has_long_text and any("description" in str(c.value).lower() or "\u63cf\u8ff0" in str(c.value) for c in column[:1]):
                sheet.column_dimensions[letter].width = 45
                for cell in column:
                    cell.alignment = Alignment(horizontal="left", vertical="top", wrap_text=True)
    output = BytesIO()
    workbook.save(output)
    return output.getvalue()

def _send_xlsx_to_telegram(filename, content, caption):
    import requests
    token, chat_id = _config()
    content = _autosize_xlsx(content)
    response = requests.post(f"https://api.telegram.org/bot{token}/sendDocument", data={"chat_id": chat_id, "caption": caption}, files={"document": (filename, content, "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")}, timeout=90)
    payload = response.json()
    if response.status_code >= 400 or not payload.get("ok"):
        raise RuntimeError(f"Telegram XLSX report failed: {payload}")


def send_weekly_reports():
    from frappe.utils import nowdate
    frappe.set_user("Administrator")
    results = []
    reports = frappe.get_all("Auto Email Report", filters={"enabled": 1, "frequency": "Weekly"}, pluck="name", order_by="name asc")
    for report_name in reports:
        report = frappe.get_doc("Auto Email Report", report_name)
        report.format = "XLSX"
        content = report.get_report_content()
        if not content:
            continue
        filename = f"\u5468\u62a5_{_safe(report_name)}_{nowdate().replace('-', '')}.xlsx"
        _send_xlsx_to_telegram(filename, content, f"\u5468\u62a5 {report_name}")
        results.append(filename)
    return {"status": "sent", "files": results}
