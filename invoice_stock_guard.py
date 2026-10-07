"""Keep delivery-backed invoices from posting stock a second time."""
import frappe
from frappe import _


def has_delivery_note(items):
    for row in items:
        if row.get("delivery_note") and frappe.db.exists(
            "Delivery Note", {"name": row.get("delivery_note"), "docstatus": 1}
        ):
            return True
        if row.get("sales_order") and row.get("item_code"):
            filters = {"against_sales_order": row.get("sales_order"),
                       "item_code": row.get("item_code"), "docstatus": 1}
            if row.get("so_detail"):
                filters["so_detail"] = row.get("so_detail")
            if frappe.db.exists("Delivery Note Item", filters):
                return True
    return False


@frappe.whitelist()
def delivery_backed(items):
    if not frappe.has_permission("Sales Invoice", "read"):
        frappe.throw(_("Not permitted"), frappe.PermissionError)
    return has_delivery_note(frappe.parse_json(items) or [])


def validate_stock_update(doc, method=None):
    if doc.update_stock and has_delivery_note(doc.get("items") or []):
        frappe.throw(_("此发票已有交货单记录库存，请取消“更新库存”后再保存或提交。"))
