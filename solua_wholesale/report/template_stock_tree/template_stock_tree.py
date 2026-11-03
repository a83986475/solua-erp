"""Ordinary items and expandable template inventory, across selected warehouses."""
import json

import frappe
from frappe import _
from frappe.utils import cint, flt, getdate, today


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

def _report_values(item, actual, reserved, opening=0, inbound=0, outbound=0, closing=None, sold=0, delivered=0):
    """Return report quantities in the item's configured sales UOM when safe."""
    factor = flt(item.get("report_factor") or 1)
    uom = item.get("report_uom") or item.get("stock_uom")
    if closing is None:
        closing = actual
    if factor <= 0:
        factor = 1
    return {
        "item_code": item["name"], "item_name": item["item_name"],
        "stock_uom": uom,
        "actual_qty": flt(actual) / factor,
        "closing_qty": flt(closing) / factor,
        "reserved_qty": flt(reserved) / factor,
        "available_qty": (flt(actual) - flt(reserved)) / factor,
        "opening_qty": flt(opening) / factor,
        "in_qty": flt(inbound) / factor,
        "out_qty": flt(outbound) / factor,
        "sold_qty": flt(sold) / factor,
        "delivered_qty": flt(delivered) / factor,
    }


def group_rows(items, bins, warehouse="", opening_quantities=None, sold_quantities=None, delivered_quantities=None,
               inbound_quantities=None, outbound_quantities=None, closing_quantities=None, legacy_opening_by_group=None):
    groups = {}
    quantities = {}
    opening_quantities = opening_quantities or {}
    sold_quantities = sold_quantities or {}
    delivered_quantities = delivered_quantities or {}
    inbound_quantities = inbound_quantities or {}
    outbound_quantities = outbound_quantities or {}
    closing_quantities = closing_quantities or {}
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
        groups[key].append({**_report_values(
            item,
            actual,
            reserved,
            opening_quantities.get(item["name"], 0),
            inbound_quantities.get(item["name"], 0),
            outbound_quantities.get(item["name"], 0),
            closing_quantities.get(item["name"]),
            sold_quantities.get(item["name"], 0),
            delivered_quantities.get(item["name"], 0),
        ), "warehouse": warehouse})
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
                   for field in ("actual_qty", "closing_qty", "reserved_qty", "available_qty", "in_qty", "out_qty", "sold_qty", "delivered_qty")},
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
        total = totals.setdefault(row["stock_uom"], {field: 0 for field in ("opening_qty", "in_qty", "out_qty", "sold_qty", "delivered_qty", "actual_qty", "closing_qty", "reserved_qty", "available_qty")})
        for field in total:
            total[field] += flt(row.get(field))
    for (item_code, uom), opening in legacy_opening_by_group.items():
        parent_id = json.dumps((item_code, uom), ensure_ascii=False)
        if parent_id in parent_ids:
            totals.setdefault(uom, {field: 0 for field in ("opening_qty", "in_qty", "out_qty", "sold_qty", "delivered_qty", "actual_qty", "closing_qty", "reserved_qty", "available_qty")})["opening_qty"] += flt(opening)
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


def _summarize_stock_ledger(rows, from_date, to_date):
    opening = {}
    inbound = {}
    outbound = {}
    closing = {}
    delivered = {}
    for row in rows:
        item_code = row.get("item_code")
        qty = flt(row.get("actual_qty"))
        posting_date = getdate(row.get("posting_date"))
        if posting_date < from_date:
            opening[item_code] = opening.get(item_code, 0) + qty
        if posting_date <= to_date:
            closing[item_code] = closing.get(item_code, 0) + qty
        if from_date <= posting_date <= to_date:
            if qty > 0:
                inbound[item_code] = inbound.get(item_code, 0) + qty
            elif qty < 0:
                outbound[item_code] = outbound.get(item_code, 0) - qty
            if row.get("voucher_type") in {"Delivery Note", "Sales Invoice"}:
                delivered[item_code] = delivered.get(item_code, 0) - qty
    return opening, inbound, outbound, closing, delivered


def _report_date_range(filters):
    to_date = getdate(filters.get("to_date") or today())
    from_date = getdate(filters.get("from_date") or to_date.replace(day=1))
    if from_date > to_date:
        frappe.throw(_("开始日期不能晚于截止日期"))
    return from_date, to_date


def execute(filters=None):
    filters = frappe._dict(filters or {})
    if not filters.company:
        frappe.throw(_("Company is required"))
    from_date, to_date = _report_date_range(filters)
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
    inbound_quantities = {}
    outbound_quantities = {}
    closing_quantities = {}
    legacy_opening_by_group = {}
    if warehouses:
        ledger_rows = frappe.get_list(
            "Stock Ledger Entry",
            filters={
                "warehouse": ["in", warehouses],
                "item_code": ["in", list(items)],
                "posting_date": ["<=", to_date],
                "is_cancelled": 0,
            },
            fields=["item_code", "posting_date", "actual_qty", "voucher_type"], limit_page_length=0,
        )
        opening_quantities, inbound_quantities, outbound_quantities, closing_quantities, delivered_quantities = _summarize_stock_ledger(
            ledger_rows, from_date, to_date
        )
    else:
        delivered_quantities = {}
    sold_quantities = {}
    if warehouses and items:
        orders = frappe.get_all(
            "Sales Order",
            filters={
                "company": filters.company,
                "docstatus": 1,
                "transaction_date": ["between", [from_date, to_date]],
            },
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
                   for field, label in [("opening_qty", "期初库存"), ("in_qty", "期间入库"), ("out_qty", "期间出库"),
                                        ("closing_qty", "截止库存"), ("actual_qty", "实际数量"),
                                        ("reserved_qty", "销售预留数量"), ("available_qty", "可用数量")])
    warehouse_label = filters.warehouse or _("全部有权限仓库")
    columns.insert(4, {"fieldname": "sold_qty", "label": _("期间销售订单数量"), "fieldtype": "Float", "precision": "0", "width": 130})
    columns.insert(5, {"fieldname": "delivered_qty", "label": _("期间已出货数量"), "fieldtype": "Float", "precision": "0", "width": 130})
    rows = group_rows(
        items, bins, warehouse_label, opening_quantities, sold_quantities, delivered_quantities,
        inbound_quantities, outbound_quantities, closing_quantities, legacy_opening_by_group,
    ) if warehouses else []
    return columns, add_totals(rows, legacy_opening_by_group)
