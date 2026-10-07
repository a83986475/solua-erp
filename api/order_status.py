"""Order lifecycle display and reason-backed native closure; no inferred history."""
import json

import frappe
from frappe.utils import flt, escape_html
from solua_home.api.home import _can_read, _list


def ensure_fields():
    from frappe.custom.doctype.custom_field.custom_field import create_custom_fields
    create_custom_fields({"Sales Order": [{
        "fieldname": "custom_order_end_reason", "label": "订单结束原因", "fieldtype": "Small Text",
        "insert_after": "status", "read_only": 1, "allow_on_submit": 1, "no_copy": 1,
        "depends_on": "eval:doc.status=='Closed'", "description": "仅记录实际结束原因，历史空值不自动补填。",
    }]}, update=False)


def lifecycle(doc):
    if doc.docstatus == 2:
        return "已取消"
    if doc.docstatus == 0:
        return "草稿"
    return {"Closed": "已结束", "Completed": "已完成", "On Hold": "暂停中"}.get(doc.status, "进行中")


def summarize(doc, delivery_rows, invoice_rows, delivery_visible=True, invoice_visible=True):
    by_item = {item.name: {"gross": 0., "returned": 0., "billed": 0.} for item in doc.items}
    invoices = {}
    for row in delivery_rows:
        if row.so_detail in by_item:
            stock = abs(flt(row.stock_qty))
            by_item[row.so_detail]["returned" if row.is_return else "gross"] += stock
    for row in invoice_rows:
        if row.so_detail not in by_item:
            continue
        invoices[row.parent] = flt(row.outstanding_amount)
        stock = abs(flt(row.stock_qty))
        if not row.is_return:
            by_item[row.so_detail]["billed"] += stock
        if row.update_stock:
            by_item[row.so_detail]["returned" if row.is_return else "gross"] += stock
    units = {}
    any_return = any(row["returned"] > 0.000001 for row in by_item.values())
    has_delivered = False
    remaining = False
    has_billed = False
    billing_remaining = False
    for item in doc.items:
        qty = max(0, flt(item.qty))
        factor = flt(item.conversion_factor) or 1
        row = by_item[item.name]
        gross, returned = row["gross"] / factor, row["returned"] / factor
        net = max(0, gross - returned)
        pending = max(0, qty - net)
        unit = units.setdefault(item.uom, {"uom": item.uom, "ordered": 0., "delivered": 0., "returned": 0., "net": 0., "remaining": 0.})
        for key, value in (("ordered", qty), ("delivered", gross), ("returned", returned), ("net", net), ("remaining", pending)):
            unit[key] += value
        has_delivered |= gross > 0.000001
        remaining |= pending > 0.000001
        has_billed |= row["billed"] > 0.000001
        billing_remaining |= max(0, qty - returned) * factor > row["billed"] + 0.000001
    delivery = "无需交货" if doc.get("skip_delivery_note") else ("未交货" if not has_delivered else ("部分交货" if remaining else "全部交货"))
    if any_return:
        delivery = "已交货 · 有退货"
    if doc.status == "Closed" and remaining:
        delivery += " · 剩余不再交付"
    billing = "未开票" if not has_billed else ("部分开票" if billing_remaining else "已开票")
    payment = "未开票" if not invoices else ("未收齐" if any(value > 0.005 for value in invoices.values()) else "关联发票已结清")
    return {"status_label": lifecycle(doc), "delivery_label": delivery if delivery_visible else "交货情况无权限",
            "billing_label": billing if invoice_visible else "开票情况无权限",
            "payment_label": payment if invoice_visible else "收款情况无权限",
            "quantities": list(units.values()) if delivery_visible else [],
            "end_reason": (doc.get("custom_order_end_reason") or "未记录") if doc.status == "Closed" else "",
            "ended": doc.status == "Closed"}


@frappe.whitelist()
@frappe.read_only()
def get_order_statuses(names):
    names = frappe.parse_json(names) if isinstance(names, str) else names
    if not isinstance(names, list) or not 1 <= len(names) <= 50 or any(not isinstance(name, str) or not name for name in names):
        frappe.throw("请选择 1–50 张订单")
    docs = [frappe.get_doc("Sales Order", name) for name in dict.fromkeys(names)]
    for doc in docs:
        doc.check_permission("read")
    deliveries, invoices = [], []
    params = {"orders": tuple(doc.name for doc in docs)}
    if _can_read("Delivery Note"):
        parents = _list("Delivery Note", {"docstatus": 1, "company": ["in", list({d.company for d in docs})]}, ["name"])
        if parents:
            deliveries = frappe.db.sql("""SELECT dni.so_detail, dni.stock_qty, dn.is_return
                FROM `tabDelivery Note Item` dni JOIN `tabDelivery Note` dn ON dn.name=dni.parent
                JOIN `tabSales Order Item` soi ON soi.name=dni.so_detail
                WHERE soi.parent IN %(orders)s AND dn.name IN %(parents)s""",
                {**params, "parents": tuple(row.name for row in parents)}, as_dict=True)
    if _can_read("Sales Invoice"):
        parents = _list("Sales Invoice", {"docstatus": 1, "company": ["in", list({d.company for d in docs})]}, ["name"])
        if parents:
            invoices = frappe.db.sql("""SELECT sii.so_detail, sii.parent, sii.stock_qty,
                       si.is_return, si.update_stock, si.outstanding_amount
                FROM `tabSales Invoice Item` sii JOIN `tabSales Invoice` si ON si.name=sii.parent
                JOIN `tabSales Order Item` soi ON soi.name=sii.so_detail
                WHERE soi.parent IN %(orders)s AND si.name IN %(parents)s""",
                {**params, "parents": tuple(row.name for row in parents)}, as_dict=True)
    return {doc.name: summarize(doc, deliveries, invoices, _can_read("Delivery Note"), _can_read("Sales Invoice")) for doc in docs}


def _end_order(doc, reason):
    doc.check_permission("submit")
    if doc.docstatus != 1 or doc.status in ("Closed", "Completed", "Cancelled"):
        frappe.throw("此订单当前不能结束")
    if not isinstance(reason, str):
        frappe.throw("请填写订单结束原因（1–500 字）")
    reason = reason.strip()
    if not reason or len(reason) > 500:
        frappe.throw("请填写订单结束原因（1–500 字）")
    doc.check_modified_date()
    doc.db_set("custom_order_end_reason", reason, update_modified=False)
    doc.update_status("Closed")
    doc.add_comment("Comment", "订单已结束，不再交付剩余。原因：" + escape_html(reason))


@frappe.whitelist()
def update_status(status, name, reason=None):
    if status != "Closed":
        from erpnext.selling.doctype.sales_order.sales_order import update_status as native
        return native(status, name)
    _end_order(frappe.get_doc("Sales Order", name), reason)


@frappe.whitelist()
def close_or_unclose_sales_orders(names, status, reason=None):
    if status != "Closed":
        from erpnext.selling.doctype.sales_order.sales_order import close_or_unclose_sales_orders as native
        return native(names, status)
    names = json.loads(names) if isinstance(names, str) else names
    if not isinstance(names, list) or not 1 <= len(names) <= 50 or any(not isinstance(name, str) for name in names):
        frappe.throw("请选择 1–50 张订单")
    frappe.has_permission("Sales Order", "write", throw=True)
    # All writes stay in the request transaction; a failure rolls back the batch.
    for name in dict.fromkeys(names):
        _end_order(frappe.get_doc("Sales Order", name), reason)
