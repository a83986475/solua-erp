"""Show the submitted Sales Orders that currently reserve stock."""

import frappe
from frappe import _
from frappe.utils import flt


def _calculate_reserved_qty(row, exclude_returns):
    """Return the current stock reservation for one Sales Order Item."""
    order_qty = flt(row.get("qty"))
    delivered_qty = flt(row.get("delivered_qty"))
    if not order_qty or flt(row.get("delivered_by_supplier")) or order_qty < delivered_qty:
        return 0

    remaining_qty = order_qty - delivered_qty
    if exclude_returns:
        remaining_qty -= flt(row.get("returned_qty"))
    return max(flt(row.get("stock_qty")) * remaining_qty / order_qty, 0)


def _columns():
    return [
        {"fieldname": "item_code", "label": _("货号"), "fieldtype": "Link", "options": "Item", "width": 150},
        {"fieldname": "item_name", "label": _("物料名称"), "fieldtype": "Data", "width": 180},
        {"fieldname": "warehouse", "label": _("仓库"), "fieldtype": "Link", "options": "Warehouse", "width": 150},
        {"fieldname": "sales_order", "label": _("占用订单"), "fieldtype": "Link", "options": "Sales Order", "width": 165},
        {"fieldname": "customer", "label": _("客户"), "fieldtype": "Link", "options": "Customer", "width": 180},
        {"fieldname": "status", "label": _("订单状态"), "fieldtype": "Data", "width": 100},
        {"fieldname": "transaction_date", "label": _("订单日期"), "fieldtype": "Date", "width": 100},
        {"fieldname": "reservation_source", "label": _("预留来源"), "fieldtype": "Data", "width": 110},
        {"fieldname": "parent_item", "label": _("组合商品"), "fieldtype": "Link", "options": "Item", "width": 150},
        {"fieldname": "order_qty", "label": _("订单数量"), "fieldtype": "Float", "width": 100},
        {"fieldname": "uom", "label": _("单位"), "fieldtype": "Link", "options": "UOM", "width": 80},
        {"fieldname": "delivered_qty", "label": _("已交付"), "fieldtype": "Float", "width": 90},
        {"fieldname": "returned_qty", "label": _("已退货"), "fieldtype": "Float", "width": 90},
        {"fieldname": "reserved_qty", "label": _("当前预留（库存单位）"), "fieldtype": "Float", "width": 145},
    ]


def _row(order, item, reserved_qty, source, parent_item="", item_name=None, stock_uom=None):
    return {
        "item_code": item.get("item_code"),
        "item_name": item_name or item.get("item_name") or item.get("item_code"),
        "warehouse": item.get("warehouse"),
        "sales_order": order.name,
        "customer": order.customer,
        "status": order.status,
        "transaction_date": order.transaction_date,
        "reservation_source": source,
        "parent_item": parent_item,
        "order_qty": flt(item.get("qty")),
        "uom": item.get("uom") or stock_uom,
        "delivered_qty": flt(item.get("delivered_qty")),
        "returned_qty": flt(item.get("returned_qty")),
        "reserved_qty": flt(reserved_qty),
    }


def execute(filters=None):
    filters = frappe._dict(filters or {})
    if not filters.company:
        frappe.throw(_("Company is required"))
    if not frappe.has_permission("Sales Order", ptype="read"):
        frappe.throw(_("没有销售订单查看权限"))

    order_filters = {
        "company": filters.company,
        "docstatus": 1,
        "status": ["not in", ["On Hold", "Closed", "Cancelled"]],
    }
    if filters.sales_order:
        order_filters["name"] = filters.sales_order
    orders = frappe.get_list(
        "Sales Order",
        filters=order_filters,
        fields=["name", "customer", "status", "transaction_date"],
        limit_page_length=0,
        order_by="transaction_date desc, name desc",
    )
    if not orders:
        return _columns(), []

    order_names = [order.name for order in orders]
    item_filters = {"parent": ["in", order_names], "parenttype": "Sales Order"}
    item_fields = [
        "name", "parent", "item_code", "item_name", "warehouse", "uom", "stock_uom",
        "qty", "stock_qty", "delivered_qty", "returned_qty", "delivered_by_supplier",
    ]
    sales_items = frappe.get_all("Sales Order Item", filters=item_filters, fields=item_fields, limit_page_length=0)
    item_by_name = {item.name: item for item in sales_items}
    exclude_returns = bool(frappe.get_cached_value(
        "Selling Settings", "Selling Settings", "dont_reserve_sales_order_qty_on_sales_return"
    ))
    order_by_name = {order.name: order for order in orders}
    rows = []

    for item in sales_items:
        if filters.item_code and item.item_code != filters.item_code:
            continue
        if filters.warehouse and item.warehouse != filters.warehouse:
            continue
        reserved_qty = _calculate_reserved_qty(item, exclude_returns)
        if reserved_qty > 0:
            rows.append(_row(order_by_name[item.parent], item, reserved_qty, _("销售订单行")))

    packed_filters = {"parent": ["in", order_names], "parenttype": "Sales Order"}
    if filters.item_code:
        packed_filters["item_code"] = filters.item_code
    if filters.warehouse:
        packed_filters["warehouse"] = filters.warehouse
    packed_items = frappe.get_all(
        "Packed Item",
        filters=packed_filters,
        fields=["parent", "parent_detail_docname", "item_code", "item_name", "warehouse", "qty"],
        limit_page_length=0,
    )
    packed_codes = list({row.item_code for row in packed_items if row.item_code})
    packed_item_map = {
        row.name: row
        for row in frappe.get_all(
            "Item", filters={"name": ["in", packed_codes]}, fields=["name", "item_name", "stock_uom"], limit_page_length=0
        )
    } if packed_codes else {}
    for packed in packed_items:
        parent_item = item_by_name.get(packed.parent_detail_docname)
        if not parent_item:
            continue
        parent_qty = flt(parent_item.get("qty"))
        parent_reserved_qty = _calculate_reserved_qty(parent_item, exclude_returns)
        if not parent_qty or not parent_reserved_qty:
            continue
        reserved_qty = flt(packed.qty) * parent_reserved_qty / flt(parent_item.get("stock_qty") or parent_qty)
        if reserved_qty <= 0:
            continue
        packed_item = packed_item_map.get(packed.item_code)
        rows.append(_row(
            order_by_name[packed.parent],
            {
                "item_code": packed.item_code,
                "item_name": packed.item_name,
                "warehouse": packed.warehouse,
                "qty": parent_item.qty,
                "uom": parent_item.uom,
                "delivered_qty": parent_item.delivered_qty,
                "returned_qty": parent_item.returned_qty,
            },
            reserved_qty,
            _("组合商品"),
            parent_item=parent_item.item_code,
            item_name=(packed_item.item_name if packed_item else packed.item_name),
            stock_uom=(packed_item.stock_uom if packed_item else None),
        ))

    if filters.item_code:
        rows = [row for row in rows if row["item_code"] == filters.item_code]
    if filters.warehouse:
        rows = [row for row in rows if row["warehouse"] == filters.warehouse]
    rows.sort(key=lambda row: (row["item_code"] or "", row["warehouse"] or "", row["sales_order"] or ""))
    return _columns(), rows
