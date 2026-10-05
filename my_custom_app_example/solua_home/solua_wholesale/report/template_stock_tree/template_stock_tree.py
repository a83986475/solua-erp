"""Ordinary items and expandable template inventory, across selected warehouses."""
import json

import frappe
from frappe import _
from frappe.utils import flt

def _report_values(item, actual, reserved, opening=0, sold=0):
    """Return report quantities in the item's configured sales UOM when safe."""
    factor = flt(item.get("report_factor") or 1)
    uom = item.get("report_uom") or item.get("stock_uom")
    if factor <= 0:
        factor = 1
    return {
        "item_code": item["name"], "item_name": item["item_name"],
        "stock_uom": uom,
        "actual_qty": flt(actual) / factor,
        "reserved_qty": flt(reserved) / factor,
        "available_qty": (flt(actual) - flt(reserved)) / factor,
        "opening_qty": flt(opening) / factor,
        "sold_qty": flt(sold) / factor,
    }


def group_rows(items, bins, warehouse="", opening_quantities=None, sold_quantities=None):
    groups = {}
    quantities = {}
    opening_quantities = opening_quantities or {}
    sold_quantities = sold_quantities or {}
    for stock in bins:
        qty = quantities.setdefault(stock["item_code"], [0, 0])
        qty[0] += flt(stock["actual_qty"])
        qty[1] += flt(stock["reserved_qty"])
    for item in items.values():
        if item.get("has_variants"):
            continue
        template = items.get(item.get("variant_of"))
        if item.get("variant_of") and not template:
            continue
        key = (item.get("variant_of") or item["name"], item.get("report_uom") or item["stock_uom"])
        if key not in groups:
            groups[key] = []
        actual, reserved = quantities.get(item["name"], [0, 0])
        groups[key].append({**_report_values(item, actual, reserved, opening_quantities.get(item["name"], 0), sold_quantities.get(item["name"], 0)), "warehouse": warehouse})
    for item in items.values():
        if item.get("has_variants") and not any(key[0] == item["name"] for key in groups):
            groups[(item["name"], item.get("report_uom") or item["stock_uom"])] = []
    rows = []
    for key, children in sorted(groups.items()):
        code, uom = key
        node_id = json.dumps(key, ensure_ascii=False)
        if items[code].get("has_variants"):
            rows.append({
                "node_id": node_id, "parent_id": "", "indent": 0,
                "item_code": code, "item_name": items[code]["item_name"],
                "warehouse": warehouse, "stock_uom": items[code].get("report_uom") or uom,
                **{field: sum(row[field] for row in children)
                   for field in ("actual_qty", "reserved_qty", "available_qty", "opening_qty", "sold_qty")},
            })
            for child in sorted(children, key=lambda row: row["item_code"]):
                rows.append({**child, "node_id": json.dumps((*key, child["item_code"])),
                             "parent_id": node_id, "indent": 1})
        else:
            rows.extend({**child, "node_id": node_id, "parent_id": "", "indent": 0} for child in children)
    return rows


def execute(filters=None):
    filters = frappe._dict(filters or {})
    if not filters.company:
        frappe.throw(_("Company is required"))
    warehouse_filters = {"company": filters.company, "is_group": 0}
    if filters.warehouse:
        warehouse_filters["name"] = filters.warehouse
    warehouses = frappe.get_list("Warehouse", filters=warehouse_filters, pluck="name", limit_page_length=0)
    items = {row.name: row for row in frappe.get_list(
        "Item", filters={"is_stock_item": 1},
        fields=["name", "item_name", "variant_of", "has_variants", "stock_uom", "sales_uom"], limit_page_length=0
    )}
    sales_uom_factors = {
        (row.parent, row.uom): flt(row.conversion_factor)
        for row in frappe.get_all(
            "UOM Conversion Detail",
            filters={"parenttype": "Item", "parent": ["in", list(items)]},
            fields=["parent", "uom", "conversion_factor"],
            limit_page_length=0,
        )
        if flt(row.conversion_factor) > 0
    } if items else {}
    for item in items.values():
        sales_uom = item.get("sales_uom") or ""
        factor = sales_uom_factors.get((item.name, sales_uom)) if sales_uom else None
        if not factor and item.get("variant_of") and sales_uom:
            factor = sales_uom_factors.get((item.get("variant_of"), sales_uom))
        if sales_uom and sales_uom != item.get("stock_uom") and factor:
            item["report_uom"] = sales_uom
            item["report_factor"] = factor
    bins = frappe.get_list(
        "Bin", filters={"warehouse": ["in", warehouses], "item_code": ["in", list(items)]},
        fields=["item_code", "warehouse", "actual_qty", "reserved_qty"], limit_page_length=0,
    ) if warehouses and items else []
    opening_quantities = {}
    if warehouses:
        opening_reconciliations = frappe.get_all(
            "Stock Reconciliation",
            filters={"purpose": "Opening Stock", "docstatus": 1},
            pluck="name", limit_page_length=0,
        )
        if opening_reconciliations:
            for row in frappe.get_all(
                "Stock Reconciliation Item",
                filters={
                    "parent": ["in", opening_reconciliations],
                    "parenttype": "Stock Reconciliation",
                    "warehouse": ["in", warehouses],
                    "item_code": ["in", list(items)],
                },
                fields=["item_code", "qty"], limit_page_length=0,
            ):
                opening_quantities[row.item_code] = opening_quantities.get(row.item_code, 0) + flt(row.qty)
    sold_quantities = {}
    if warehouses and items:
        for row in frappe.get_all(
            "Stock Ledger Entry",
            filters={
                "warehouse": ["in", warehouses],
                "item_code": ["in", list(items)],
                "voucher_type": ["in", ["Delivery Note", "Sales Invoice"]],
                "is_cancelled": 0,
            },
            fields=["item_code", "actual_qty"], limit_page_length=0,
        ):
            sold_quantities[row.item_code] = sold_quantities.get(row.item_code, 0) - flt(row.actual_qty)
    if filters.template:
        items = {name: item for name, item in items.items()
                 if name == filters.template or item.get("variant_of") == filters.template}
    columns = [
        {"fieldname": "item_code", "label": _("货号"), "fieldtype": "Link", "options": "Item", "width": 290},
        {"fieldname": "item_name", "label": _("Item Name"), "fieldtype": "Data", "width": 200},
        {"fieldname": "warehouse", "label": _("Warehouse"), "fieldtype": "Data", "width": 180},
        {"fieldname": "stock_uom", "label": _("单位"), "fieldtype": "Link", "options": "UOM", "width": 80},
    ]
    columns.extend({"fieldname": field, "label": _(label), "fieldtype": "Float", "precision": "0", "width": 130}
                   for field, label in [("actual_qty", "实际数量"), ("reserved_qty", "销售预留数量"), ("available_qty", "可用数量")])
    warehouse_label = filters.warehouse or _("全部有权限仓库")
    columns.insert(4, {"fieldname": "opening_qty", "label": _("初始库存"), "fieldtype": "Float", "precision": "0", "width": 130})
    columns.insert(5, {"fieldname": "sold_qty", "label": _("已销售数量"), "fieldtype": "Float", "precision": "0", "width": 130})
    return columns, group_rows(items, bins, warehouse_label, opening_quantities, sold_quantities) if warehouses else []
