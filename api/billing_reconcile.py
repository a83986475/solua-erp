"""Keep native Sales Order and Delivery Note billing counters in sync."""

from collections import defaultdict

import frappe
from frappe.utils import flt


def _invoice_rows(so_details, dn_details):
    conditions = [
        "si.docstatus = 1",
        "sii.docstatus = 1",
        "si.is_return = 0",
        "sii.qty > 0",
    ]
    params = {"so_details": tuple(so_details), "dn_details": tuple(dn_details)}
    sources = []
    if so_details:
        sources.append("sii.so_detail IN %(so_details)s")
    if dn_details:
        sources.append("sii.dn_detail IN %(dn_details)s")
    if not sources:
        return []
    conditions.append("(" + " OR ".join(sources) + ")")
    return frappe.db.sql(
        """SELECT sii.so_detail, sii.dn_detail, sii.qty, sii.amount
             FROM `tabSales Invoice Item` sii
             JOIN `tabSales Invoice` si ON si.name = sii.parent
            WHERE """
        + " AND ".join(conditions),
        params,
        as_dict=True,
    )


def _delivery_rows(so_details, dn_details):
    conditions = ["dn.docstatus = 1", "dn.is_return = 0"]
    params = {"so_details": tuple(so_details), "dn_details": tuple(dn_details)}
    sources = []
    if so_details:
        sources.append("dni.so_detail IN %(so_details)s")
    if dn_details:
        sources.append("dni.name IN %(dn_details)s")
    if not sources:
        return []
    conditions.append("(" + " OR ".join(sources) + ")")
    return frappe.db.sql(
        """SELECT dni.name, dni.parent, dni.so_detail, dni.qty, dni.amount, dni.billed_amt,
                       dn.posting_date, dn.posting_time
                FROM `tabDelivery Note Item` dni
                JOIN `tabDelivery Note` dn ON dn.name = dni.parent
               WHERE """
        + " AND ".join(conditions),
        params,
        as_dict=True,
    )


def reconcile_linked_billing(so_details=None, dn_details=None):
    """Recompute only source rows affected by a Sales Invoice submit/cancel."""
    so_details = {value for value in (so_details or ()) if value}
    dn_details = {value for value in (dn_details or ()) if value}
    if not so_details and not dn_details:
        return {"sales_order_items": 0, "delivery_note_items": 0}

    delivery_rows = _delivery_rows(so_details, dn_details)
    so_details.update(row.so_detail for row in delivery_rows if row.so_detail)
    invoice_rows = _invoice_rows(so_details, dn_details)
    delivery_rows = _delivery_rows(so_details, dn_details)

    billed_by_so = defaultdict(float)
    direct_by_so = defaultdict(lambda: {"qty": 0.0, "amount": 0.0})
    billed_by_dn = defaultdict(lambda: {"qty": 0.0, "amount": 0.0})
    for row in invoice_rows:
        if row.so_detail:
            billed_by_so[row.so_detail] += flt(row.amount)
            if not row.dn_detail:
                direct_by_so[row.so_detail]["qty"] += flt(row.qty)
                direct_by_so[row.so_detail]["amount"] += flt(row.amount)
        if row.dn_detail:
            billed_by_dn[row.dn_detail]["qty"] += flt(row.qty)
            billed_by_dn[row.dn_detail]["amount"] += flt(row.amount)

    so_items = frappe.get_all(
        "Sales Order Item",
        filters={"name": ["in", list(so_details)]},
        fields=["name", "parent", "amount"],
        limit_page_length=0,
    )
    changed_so_parents = set()
    for row in so_items:
        frappe.db.set_value(
            "Sales Order Item",
            row.name,
            "billed_amt",
            flt(billed_by_so.get(row.name, 0), 6),
            update_modified=False,
        )
        changed_so_parents.add(row.parent)

    for parent in changed_so_parents:
        items = frappe.get_all(
            "Sales Order Item",
            filters={"parent": parent},
            fields=["amount", "billed_amt"],
            limit_page_length=0,
        )
        total = sum(abs(flt(row.amount)) for row in items)
        billed = sum(min(abs(flt(row.amount)), abs(flt(row.billed_amt))) for row in items)
        percentage = flt(billed / total * 100, 6) if total else 0
        frappe.db.set_value("Sales Order", parent, "per_billed", percentage, update_modified=False)
        doc = frappe.get_doc("Sales Order", parent)
        doc.update_status(doc.status)

    delivery_by_so = defaultdict(list)
    delivery_without_so = []
    for row in delivery_rows:
        if row.so_detail:
            delivery_by_so[row.so_detail].append(row)
        else:
            delivery_without_so.append(row)

    expected_by_dn = {}
    for so_detail, rows in delivery_by_so.items():
        rows.sort(key=lambda row: (str(row.posting_date or ""), str(row.posting_time or ""), str(row.parent or "")))
        direct = direct_by_so.get(so_detail, {"qty": 0.0, "amount": 0.0})
        remaining_qty = direct["qty"]
        rate = direct["amount"] / direct["qty"] if direct["qty"] else 0
        for row in rows:
            linked = billed_by_dn.get(row.name, {"qty": 0.0, "amount": 0.0})
            capacity = max(0, flt(row.qty) - linked["qty"])
            allocated = min(capacity, max(0, remaining_qty))
            expected_by_dn[row.name] = linked["amount"] + allocated * rate
            remaining_qty = max(0, remaining_qty - allocated)

    for row in delivery_without_so:
        expected_by_dn[row.name] = billed_by_dn.get(row.name, {"amount": 0.0})["amount"]

    changed_dn_parents = set()
    for row in delivery_rows:
        frappe.db.set_value(
            "Delivery Note Item",
            row.name,
            "billed_amt",
            flt(expected_by_dn.get(row.name, 0), 6),
            update_modified=False,
        )
        changed_dn_parents.add(row.parent)
    for parent in changed_dn_parents:
        frappe.get_doc("Delivery Note", parent).update_billing_percentage(update_modified=False)

    return {"sales_order_items": len(so_items), "delivery_note_items": len(delivery_rows)}
