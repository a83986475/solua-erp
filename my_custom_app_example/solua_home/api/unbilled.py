"""Delivery-based billing queue; no invoice is saved or submitted here."""
import frappe
from frappe.utils import flt, date_diff, nowdate
from solua_home.api.home import _can_read, _can_create, _list


def pending_qty(row, invoiced_qty=0, returned_qty=0):
    if row.get("si_detail"):
        return 0
    billed_qty = flt(row.get("billed_amt")) / flt(row.get("rate")) if flt(row.get("rate")) else 0
    return max(0, flt(row.get("qty")) - max(billed_qty, flt(invoiced_qty)) - flt(returned_qty))


def linked_drafts(company, notes):
    result = {}
    if not _can_read("Sales Invoice"):
        return result
    for invoice in _list("Sales Invoice", {"company": company, "docstatus": 0}, ["name"]):
        doc = frappe.get_doc("Sales Invoice", invoice.name)
        for name in {row.delivery_note for row in doc.items if row.delivery_note in notes}:
            result.setdefault(name, []).append(doc.name)
    return result


def get_rows(company, start, end, customer=None):
    from erpnext.stock.doctype.delivery_note.mapper import get_invoiced_qty_map, get_returned_qty_map
    filters = {"company": company, "docstatus": 1, "is_return": 0,
               "posting_date": ["between", [start, end]], "per_billed": ["<", 100],
               "status": ["not in", ["Closed", "Completed"]]}
    if customer:
        filters["customer"] = customer
    notes = _list("Delivery Note", filters, ["name"], order_by="customer asc, posting_date asc, name asc")
    drafts = linked_drafts(company, {row.name for row in notes})
    rows = []
    for note in notes:
        doc = frappe.get_doc("Delivery Note", note.name)
        invoiced, returned = get_invoiced_qty_map(doc.name), get_returned_qty_map(doc.name)
        amount = sum(pending_qty(row, invoiced.get(row.name, 0), returned.get(row.name, 0)) * flt(row.base_rate) for row in doc.items)
        if amount <= 0.005:
            continue
        draft_names = drafts.get(doc.name, [])
        rows.append({"doctype": "Delivery Note", "name": doc.name, "date": str(doc.posting_date),
                     "customer": doc.customer, "currency": frappe.get_cached_value("Company", company, "default_currency"),
                     "amount": flt(amount, 2), "invoice_plan": doc.get("custom_invoice_plan") or "未维护",
                     "waiting_days": max(0, date_diff(nowdate(), doc.posting_date)),
                     "billing_state": "已有草稿" if draft_names else ("部分开票" if doc.per_billed else "待开票"),
                     "draft_invoices": draft_names, "action": "查看草稿" if draft_names else "生成发票草稿",
                     "can_invoice": _can_create("Sales Invoice")})
    return rows


@frappe.whitelist()
@frappe.read_only()
def prepare_invoice(delivery_note):
    from erpnext.stock.doctype.delivery_note.mapper import make_sales_invoice, get_invoiced_qty_map, get_returned_qty_map
    source = frappe.get_doc("Delivery Note", delivery_note)
    source.check_permission("read")
    if source.docstatus != 1 or source.is_return or source.status in ("Closed", "Completed"):
        frappe.throw("此交货单当前不能开票")
    drafts = linked_drafts(source.company, {source.name}).get(source.name, [])
    if drafts:
        return {"draft_invoices": drafts}
    if not _can_create("Sales Invoice"):
        frappe.throw("没有创建销售发票的权限", frappe.PermissionError)
    invoiced, returned = get_invoiced_qty_map(source.name), get_returned_qty_map(source.name)
    quantities = {row.name: pending_qty(row, invoiced.get(row.name, 0), returned.get(row.name, 0)) for row in source.items}
    if not any(qty > 0 for qty in quantities.values()):
        frappe.throw("此交货单已全部开票或退货，请刷新报表")
    invoice = make_sales_invoice(source.name, args={"filtered_children": [name for name, qty in quantities.items() if qty > 0]})
    for row in invoice.items:
        row.qty = min(flt(row.qty), quantities[row.dn_detail])
    invoice.run_method("calculate_taxes_and_totals")
    return {"invoice": invoice.as_dict()}
