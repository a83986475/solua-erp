"""Ordinary items and expandable template inventory, across selected warehouses."""
import json

import frappe
from frappe import _
from frappe.utils import cint, flt, today


def _filter_items(items, exclude_legacy):
    if not exclude_legacy:
        return items
    return {name: item for name, item in items.items() if "LEGACY" not in name.upper()}

def _legacy_group_key(item_code, items):
    marker = "-LEGACY"
    if not item_code.upper().endswith(marker):
        return None
    template_code = item_code[:-len(marker)]
    template = items.get(template_code)
    if not template or not template.get("has_variants"):
        return None
    return template_code, template.get("report_uom") or template.get("stock_uom")

def _report_values(item, actual, reserved, opening=0, sold=0, delivered=0):
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
        "delivered_qty": flt(delivered) / factor,
    }


def group_rows(items, bins, warehouse="", opening_quantities=None, sold_quantities=None, delivered_quantities=None, legacy_opening_by_group=None):
    groups = {}
    quantities = {}
    opening_quantities = opening_quantities or {}
    sold_quantities = sold_quantities or {}
    delivered_quantities = delivered_quantities or {}
    legacy_opening_by_group = legacy_opening_by_group or {}
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
        groups[key].append({**_report_values(item, actual, reserved, opening_quantities.get(item["name"], 0), sold_quantities.get(item["name"], 0), delivered_quantities.get(item["name"], 0)), "warehouse": warehouse})
    for item in items.values():
        if item.get("has_variants") and not any(key[0] == item["name"] for key in groups):
            groups[(item["name"], item.get("report_uom") or item["stock_uom"])] = []
    rows = []
    for key, children in sorted(groups.items()):
        code, uom = key
        node_id = json.dumps(key, ensure_ascii=False)
        if items[code].get("has_variants"):
            hidden_opening = flt(legacy_opening_by_group.get(key) or 0)
            rows.append({
                "node_id": node_id, "parent_id": "", "indent": 0,
                "item_code": code, "item_name": items[code]["item_name"],
                "warehouse": warehouse, "stock_uom": items[code].get("report_uom") or uom,
                **{field: sum(row[field] for row in children)
                   for field in ("actual_qty", "reserved_qty", "available_qty", "sold_qty", "delivered_qty")},
                "opening_qty": sum(row["opening_qty"] for row in children) + hidden_opening,
            })
            for child in sorted(children, key=lambda row: row["item_code"]):
                rows.append({**child, "node_id": json.dumps((*key, child["item_code"])),
                             "parent_id": node_id, "indent": 1})
        else:
            rows.extend({**child, "node_id": node_id, "parent_id": "", "indent": 0} for child in children)
    return rows


def add_totals(rows, legacy_opening_by_group=None):
    parent_ids = {row["parent_id"] for row in rows if row.get("parent_id")}
    leaves = [row for row in rows if row["node_id"] not in parent_ids]
    legacy_opening_by_group = legacy_opening_by_group or {}
    totals = {}
    for row in leaves:
        total = totals.setdefault(row["stock_uom"], {field: 0 for field in ("opening_qty", "sold_qty", "delivered_qty", "actual_qty", "reserved_qty", "available_qty")})
        for field in total:
            total[field] += flt(row.get(field))
    for (item_code, uom), opening in legacy_opening_by_group.items():
        parent_id = json.dumps((item_code, uom), ensure_ascii=False)
        if parent_id in parent_ids:
            totals.setdefault(uom, {field: 0 for field in ("opening_qty", "sold_qty", "delivered_qty", "actual_qty", "reserved_qty", "available_qty")})["opening_qty"] += flt(opening)
    for uom, total in sorted(totals.items()):
        rows.append({
            "node_id": json.dumps(("__total__", uom), ensure_ascii=False), "parent_id": "", "indent": 0,
            "item_code": "", "item_name": _("合计（去重）"), "warehouse": "", "stock_uom": uom,
            **total,
        })
    return rows


def _sum_sales_order_items(rows):
    quantities = {}
    for row in rows:
        qty = flt(row.get("stock_qty"))
        if not qty:
            qty = flt(row.get("qty")) * (flt(row.get("conversion_factor")) or 1)
        item_code = row.get("item_code")
        quantities[item_code] = quantities.get(item_code, 0) + qty
    return quantities


def execute(filters=None):
    filters = frappe._dict(filters or {})
    if not filters.company:
        frappe.throw(_("Company is required"))
    warehouse_filters = {"company": filters.company, "is_group": 0}
    if filters.warehouse:
        warehouse_filters["name"] = filters.warehouse
    warehouses = frappe.get_list("Warehouse", filters=warehouse_filters, pluck="name", limit_page_length=0)
    all_items = {row.name: row for row in frappe.get_list(
        "Item", filters={"is_stock_item": 1},
        fields=["name", "item_name", "variant_of", "has_variants", "stock_uom", "sales_uom"], limit_page_length=0
    )}
    sales_uom_factors = {
        (row.parent, row.uom): flt(row.conversion_factor)
        for row in frappe.get_all(
            "UOM Conversion Detail",
            filters={"parenttype": "Item", "parent": ["in", list(all_items)]},
            fields=["parent", "uom", "conversion_factor"],
            limit_page_length=0,
        )
        if flt(row.conversion_factor) > 0 and row.parent in all_items
    } if all_items else {}
    for item in all_items.values():
        sales_uom = item.get("sales_uom") or ""
        factor = sales_uom_factors.get((item.name, sales_uom)) if sales_uom else None
        if not factor and item.get("variant_of") and sales_uom:
            factor = sales_uom_factors.get((item.get("variant_of"), sales_uom))
        if sales_uom and sales_uom != item.get("stock_uom") and factor:
            item["report_uom"] = sales_uom
            item["report_factor"] = factor
    items = _filter_items(all_items, cint(filters.get("exclude_legacy")))
    bins = frappe.get_list(
        "Bin", filters={"warehouse": ["in", warehouses], "item_code": ["in", list(items)]},
        fields=["item_code", "warehouse", "actual_qty", "reserved_qty"], limit_page_length=0,
    ) if warehouses and items else []
    opening_quantities = {}
    legacy_opening_by_group = {}
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
                    "item_code": ["in", list(all_items)],
                },
                fields=["item_code", "qty"], limit_page_length=0,
            ):
                if row.item_code in items:
                    opening_quantities[row.item_code] = opening_quantities.get(row.item_code, 0) + flt(row.qty)
                else:
                    key = _legacy_group_key(row.item_code, all_items)
                    if key:
                        item = all_items[row.item_code]
                        factor = flt(item.get("report_factor") or 1) or 1
                        legacy_opening_by_group[key] = legacy_opening_by_group.get(key, 0) + flt(row.qty) / factor
    sold_quantities = {}
    delivered_quantities = {}
    if warehouses and items:
        orders = frappe.get_all(
            "Sales Order",
            filters={"company": filters.company, "docstatus": 1, "transaction_date": ["<=", today()]},
            pluck="name", limit_page_length=0,
        )
        if orders:
            sold_quantities = _sum_sales_order_items(frappe.get_all(
                "Sales Order Item",
                filters={
                    "parent": ["in", orders],
                    "parenttype": "Sales Order",
                    "warehouse": ["in", warehouses],
                    "item_code": ["in", list(items)],
                },
                fields=["item_code", "qty", "stock_qty", "conversion_factor"], limit_page_length=0,
            ))
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
            delivered_quantities[row.item_code] = delivered_quantities.get(row.item_code, 0) - flt(row.actual_qty)
    if filters.template:
        items = {name: item for name, item in items.items()
                 if name == filters.template or item.get("variant_of") == filters.template}
        legacy_opening_by_group = {key: qty for key, qty in legacy_opening_by_group.items() if key[0] == filters.template}
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
    columns.insert(5, {"fieldname": "sold_qty", "label": _("销售订单数量"), "fieldtype": "Float", "precision": "0", "width": 130})
    columns.insert(6, {"fieldname": "delivered_qty", "label": _("已出货数量"), "fieldtype": "Float", "precision": "0", "width": 130})
    rows = group_rows(items, bins, warehouse_label, opening_quantities, sold_quantities, delivered_quantities, legacy_opening_by_group) if warehouses else []
    return columns, add_totals(rows, legacy_opening_by_group)
