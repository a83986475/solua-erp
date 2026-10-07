"""Explicit live-data refresh for customer-facing document prints."""

import json

import frappe
from frappe import _


ALLOWED_DOCTYPES = {"Sales Order", "Delivery Note", "Sales Invoice", "Pick List"}


@frappe.whitelist()
def refresh_latest(doctype, name):
    if doctype not in ALLOWED_DOCTYPES:
        frappe.throw(_("Unsupported document type"))
    doc = frappe.get_doc(doctype, name)
    if not frappe.has_permission(doctype, ptype="read"):
        frappe.throw(_("Not permitted"), frappe.PermissionError)

    from solua_home.printing.a4_designer import get_a4_print_data
    from solua_home.printing.wholesale import get_wholesale_print_data

    data = get_a4_print_data(doc, live=True)
    persisted = False
    if doctype in {"Sales Order", "Delivery Note"} and frappe.get_meta(doctype).has_field("custom_wholesale_snapshot"):
        doc.check_permission("write")
        snapshot = get_wholesale_print_data(doc, live=True)
        doc.db_set("custom_wholesale_snapshot", json.dumps(snapshot, ensure_ascii=False, default=str), update_modified=True)
        persisted = True
    return {
        "doctype": doctype,
        "name": name,
        "data_source": "live",
        "persisted": persisted,
        "rows": len(data.get("items") or []),
        "customer": (data.get("customer") or {}).get("name") if isinstance(data.get("customer"), dict) else "",
    }
