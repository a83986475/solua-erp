"""Delivery-based billing queue; no invoice is saved or submitted here."""
from importlib import import_module
from importlib.util import find_spec

import frappe
from frappe.utils import flt, date_diff, nowdate
from solua_home.api.home import _can_read, _can_create, _list


def billing_module():
    path = "erpnext.stock.doctype.delivery_note.mapper"
    return import_module(path if find_spec(path) else "erpnext.stock.doctype.delivery_note.delivery_note")


def pending_qty(row, invoiced_qty=0, returned_qty=0):
    if row.get("si_detail"):
        return 0
    return max(0, flt(row.get("qty")) - flt(invoiced_qty) - flt(returned_qty))


def price_adjustment(row, returned_qty=0, covered_qty=0):
    """Return a net rate/credit difference only after the physical quantity is covered."""
    qty = flt(row.get("qty"))
    returned_qty = flt(returned_qty)
    if covered_qty + returned_qty + 0.000001 < qty:
        return 0
    billed = flt(row.get("billed_amt"))
    if abs(billed - qty * flt(row.get("rate"))) <= 0.005:
        return 0
    expected = max(0, qty - returned_qty) * flt(row.get("rate"))
    return expected - billed


def allocate_sales_order_qty(delivery_rows, invoiced_qty):
    """Allocate SO invoice quantity to delivery rows in ERPNext's FIFO order."""
    result = {}
    remaining = flt(invoiced_qty)
    for row in sorted(delivery_rows, key=lambda item: (
        str(item.get("posting_date") or ""), str(item.get("posting_time") or ""), str(item.get("parent") or "")
    )):
        capacity = max(0, flt(row.get("qty")) - flt(row.get("direct_invoiced_qty")))
        result[row.get("name")] = min(capacity, max(0, remaining))
        remaining = max(0, remaining - result[row.get("name")])
    return result


def _submitted_invoice_rows(company):
    if not _can_read("Sales Invoice"):
        return []
    return frappe.db.sql(
        """SELECT sii.dn_detail, sii.delivery_note, sii.sales_order, sii.so_detail,
                   sii.qty, sii.amount, si.is_return
             FROM `tabSales Invoice Item` sii
             JOIN `tabSales Invoice` si ON si.name = sii.parent
            WHERE si.company = %(company)s AND si.docstatus = 1""",
        {"company": company},
        as_dict=True,
    )


def _delivery_rows_by_so_detail(company, so_details):
    if not so_details or not _can_read("Delivery Note"):
        return {}
    rows = frappe.db.sql(
        """SELECT dni.name, dni.parent, dni.so_detail, dni.qty,
                   dn.posting_date, dn.posting_time
             FROM `tabDelivery Note Item` dni
             JOIN `tabDelivery Note` dn ON dn.name = dni.parent
            WHERE dn.company = %(company)s AND dn.docstatus = 1 AND dn.is_return = 0
              AND dni.so_detail IN %(so_details)s
            ORDER BY dn.posting_date, dn.posting_time, dn.name""",
        {"company": company, "so_details": tuple(so_details)},
        as_dict=True,
    )
    result = {}
    for row in rows:
        result.setdefault(row.get("so_detail"), []).append(row)
    return result


def invoice_qty_map(company, docs):
    """Map each delivery row to submitted, non-credit-note invoice quantity."""
    invoice_rows = _submitted_invoice_rows(company)
    direct = {}
    so_totals = {}
    for row in invoice_rows:
        if row.get("is_return"):
            continue
        if row.get("dn_detail"):
            direct[row.get("dn_detail")] = direct.get(row.get("dn_detail"), 0) + flt(row.get("qty"))
        elif row.get("so_detail"):
            so_totals[row.get("so_detail")] = so_totals.get(row.get("so_detail"), 0) + flt(row.get("qty"))

    so_details = set(so_totals)
    delivery_rows = _delivery_rows_by_so_detail(company, so_details)
    so_allocated = {}
    for detail, rows in delivery_rows.items():
        so_allocated.update(allocate_sales_order_qty(
            [dict(row, direct_invoiced_qty=direct.get(row.get("name"), 0)) for row in rows],
            so_totals.get(detail, 0),
        ))

    result = {}
    for doc in docs:
        result[doc.name] = {
            row.name: direct.get(row.name, 0) + so_allocated.get(row.name, 0)
            for row in doc.items
        }
    return result


def linked_drafts(company, notes, so_note_map=None):
    result = {}
    if not _can_read("Sales Invoice"):
        return result
    for invoice in _list("Sales Invoice", {"company": company, "docstatus": 0}, ["name"]):
        doc = frappe.get_doc("Sales Invoice", invoice.name)
        names = {row.delivery_note for row in doc.items if row.delivery_note in notes}
        if so_note_map:
            for row in doc.items:
                names.update(so_note_map.get(row.so_detail, ()))
        for name in names:
            result.setdefault(name, []).append(doc.name)
    return result


def get_rows(company, start, end, customer=None):
    billing = billing_module()
    filters = {"company": company, "docstatus": 1, "is_return": 0,
               "posting_date": ["between", [start, end]],
               "status": ["not in", ["Closed"]]}
    if customer:
        filters["customer"] = customer
    notes = _list("Delivery Note", filters, ["name"], order_by="customer asc, posting_date asc, name asc")
    docs = [frappe.get_doc("Delivery Note", note.name) for note in notes]
    so_note_map = {}
    for doc in docs:
        for row in doc.items:
            if row.so_detail:
                so_note_map.setdefault(row.so_detail, []).append(doc.name)
    drafts = linked_drafts(company, {doc.name for doc in docs}, so_note_map)
    invoiced_qty = invoice_qty_map(company, docs)
    rows = []
    for doc in docs:
        returned = billing.get_returned_qty_map(doc.name)
        quantities = {row.name: pending_qty(row, invoiced_qty[doc.name].get(row.name, 0), returned.get(row.name, 0))
                      for row in doc.items}
        qty_amount = sum(quantities[row.name] * flt(row.base_rate) for row in doc.items)
        adjustment = sum(price_adjustment(row, returned.get(row.name, 0),
                                          flt(row.qty) - quantities[row.name] - flt(returned.get(row.name, 0)))
                          for row in doc.items)
        amount = qty_amount + adjustment
        if amount <= 0.005 and abs(adjustment) <= 0.005:
            continue
        draft_names = drafts.get(doc.name, [])
        state = "已有草稿" if draft_names else ("部分开票" if qty_amount > 0 and any(invoiced_qty[doc.name].get(row.name, 0) for row in doc.items) else "待开票")
        if qty_amount <= 0.005 and abs(adjustment) > 0.005:
            state = "价格调整"
        rows.append({"doctype": "Delivery Note", "name": doc.name, "date": str(doc.posting_date),
                     "customer": doc.customer, "currency": frappe.get_cached_value("Company", company, "default_currency"),
                     "amount": flt(amount, 2), "price_adjustment": flt(adjustment, 2),
                     "invoice_plan": doc.get("custom_invoice_plan") or "未维护",
                     "waiting_days": max(0, date_diff(nowdate(), doc.posting_date)),
                     "billing_state": state,
                     "draft_invoices": draft_names,
                     "action": "查看草稿" if draft_names else ("生成发票草稿" if qty_amount > 0.005 else "不生成发票"),
                     "can_invoice": bool(qty_amount > 0.005 and _can_create("Sales Invoice"))})
    return rows


@frappe.whitelist()
@frappe.read_only()
def prepare_invoice(delivery_note):
    billing = billing_module()
    make_sales_invoice = billing.make_sales_invoice
    source = frappe.get_doc("Delivery Note", delivery_note)
    source.check_permission("read")
    if source.docstatus != 1 or source.is_return or source.status in ("Closed", "Completed"):
        frappe.throw("此交货单当前不能开票")
    so_note_map = {row.so_detail: [source.name] for row in source.items if row.so_detail}
    drafts = linked_drafts(source.company, {source.name}, so_note_map).get(source.name, [])
    if drafts:
        return {"draft_invoices": drafts}
    if not _can_create("Sales Invoice"):
        frappe.throw("没有创建销售发票的权限", frappe.PermissionError)
    invoiced = invoice_qty_map(source.company, [source])[source.name]
    returned = billing.get_returned_qty_map(source.name)
    quantities = {row.name: pending_qty(row, invoiced.get(row.name, 0), returned.get(row.name, 0)) for row in source.items}
    if not any(qty > 0 for qty in quantities.values()):
        frappe.throw("此交货单已全部开票或退货，请刷新报表")
    invoice = make_sales_invoice(source.name, args={"filtered_children": [name for name, qty in quantities.items() if qty > 0]})
    for row in invoice.items:
        row.qty = min(flt(row.qty), quantities[row.dn_detail])
    invoice.run_method("calculate_taxes_and_totals")
    return {"invoice": invoice.as_dict()}
