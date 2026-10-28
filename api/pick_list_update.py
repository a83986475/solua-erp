"""Preview and confirm a draft Pick List refresh from its Sales Order."""

import hashlib
import json

import frappe
from frappe import _
from frappe.utils import flt


ROW_FIELDS = (
    "sales_order", "sales_order_item", "product_bundle_item", "item_code", "item_name",
    "warehouse", "uom", "stock_uom", "conversion_factor", "qty", "stock_qty",
    "batch_no", "serial_no", "serial_and_batch_bundle",
)
QUANTITY_FIELDS = {"qty", "stock_qty", "conversion_factor"}


def _rows(doc):
    return [
        {key: flt(row.get(key)) if key in QUANTITY_FIELDS else (row.get(key) or "") for key in ROW_FIELDS}
        for row in doc.get("locations") or []
    ]


def _changes(before, after):
    def grouped(rows):
        result = {}
        for row in rows:
            key = tuple(row.get(field) for field in (
                "sales_order_item", "product_bundle_item", "item_code", "warehouse", "uom", "conversion_factor"
            ))
            if key not in result:
                result[key] = dict(row, qty=0, stock_qty=0)
            result[key]["qty"] += row["qty"]
            result[key]["stock_qty"] += row["stock_qty"]
        return result

    old, new = grouped(before), grouped(after)
    changes = []
    for key in dict.fromkeys([*old, *new]):
        left, right = old.get(key), new.get(key)
        if left and right and left["qty"] == right["qty"] and left["stock_qty"] == right["stock_qty"]:
            continue
        row = right or left
        changes.append({
            **{field: row[field] for field in ("item_code", "item_name", "warehouse", "uom", "stock_uom")},
            "action": "新增" if not left else "移除" if not right else "调整",
            "before_qty": left["qty"] if left else 0,
            "after_qty": right["qty"] if right else 0,
            "before_stock_qty": left["stock_qty"] if left else 0,
            "after_stock_qty": right["stock_qty"] if right else 0,
        })
    return changes


def _prepare(pick_list, lock=False):
    doc = frappe.get_doc("Pick List", pick_list, for_update=lock)
    doc.check_permission("read")
    doc.check_permission("write")
    if doc.docstatus != 0 or doc.purpose != "Delivery":
        frappe.throw(_("仅出货用途的拣货单草稿可以按最新订单更新。"))
    if doc.get("custom_pick_result") not in (None, "", "待拣货"):
        frappe.throw(_("已登记拣货结果，请先核实仓库实际情况，不能自动覆盖。"))
    for row in doc.get("locations") or []:
        if any(flt(row.get(field)) != 0 for field in ("picked_qty", "delivered_qty", "stock_reserved_qty")):
            frappe.throw(_("存在已拣、已交付或预留数量，不能自动更新拣货明细。"))
        if any(row.get(field) for field in ("batch_no", "serial_no", "serial_and_batch_bundle")):
            frappe.throw(_("明细已指定批次或序列号，请人工核对，不能自动覆盖。"))
        if not row.get("sales_order") or not row.get("sales_order_item"):
            frappe.throw(_("存在非订单来源的手工明细，请人工核对，不能自动覆盖。"))
    orders = {row.sales_order for row in doc.get("locations") or [] if row.sales_order}
    if doc.get("custom_sales_order"):
        orders.add(doc.custom_sales_order)
    if len(orders) != 1:
        frappe.throw(_("此功能仅支持关联一张销售订单的拣货单。"))
    order = frappe.get_doc("Sales Order", orders.pop(), for_update=lock)
    order.check_permission("read")
    if order.docstatus != 1 or order.status in ("Closed", "Cancelled", "On Hold", "Completed"):
        frappe.throw(_("销售订单必须已提交且仍可交付，才能更新拣货单。"))
    if order.company != doc.company or order.customer != doc.customer:
        frappe.throw(_("销售订单的公司或客户与拣货单不一致。"))
    for doctype in ("Delivery Note Item", "Sales Invoice Item"):
        if frappe.db.exists(doctype, {"against_pick_list": doc.name, "docstatus": ["!=", 2]}):
            frappe.throw(_("已有下游交货单或销售发票，不能自动更新拣货明细。"))
    if frappe.db.exists("Stock Reservation Entry", {
        "from_voucher_type": "Pick List", "from_voucher_no": doc.name, "docstatus": ["!=", 2],
    }):
        frappe.throw(_("已有库存预留记录，不能自动更新拣货明细。"))

    from erpnext.selling.doctype.sales_order import sales_order

    mapper = getattr(sales_order, "create_pick_list", None)
    if mapper is None:
        from erpnext.selling.doctype.sales_order.mapper import create_pick_list as mapper

    candidate = frappe.get_doc(doc.as_dict())
    candidate.set("locations", [])
    candidate.pick_manually = 0
    candidate = mapper(order.name, target_doc=candidate)
    before, after = _rows(doc), _rows(candidate)
    if not after:
        frappe.throw(_("当前没有可生成的拣货明细，请核对订单剩余数量和库存；原单据未改动。"))
    from solua_home.api.stock import _pick_list_order_comparison

    comparison = _pick_list_order_comparison(candidate)
    unplanned = [
        {key: row.get(key) for key in ("item_code", "item_name", "stock_uom", "order_qty", "planned_qty")}
        for row in comparison["rows"]
        if not row.get("extra") and flt(row["order_qty"]) > flt(row["planned_qty"]) + 0.000001
    ]
    payload = [str(doc.modified), str(order.modified), before, after]
    token = hashlib.sha256(json.dumps(payload, ensure_ascii=False, sort_keys=True).encode()).hexdigest()
    return doc, after, {
        "pick_list": doc.name, "sales_order": order.name, "token": token,
        "changes": _changes(before, after), "changed": before != after,
        "before_rows": len(before), "after_rows": len(after), "unplanned": unplanned,
    }


@frappe.whitelist()
def preview(pick_list):
    return _prepare(pick_list)[2]


@frappe.whitelist(methods=["POST"])
def apply(pick_list, token):
    doc, rows, result = _prepare(pick_list, lock=True)
    if not token or token != result["token"]:
        frappe.throw(_("订单、拣货单或可拣库存已变化，请重新点击按最新订单更新并确认差异。"))
    if result["changed"]:
        doc.set("locations", rows)
        doc.save()
    return {"name": doc.name, "docstatus": doc.docstatus, "updated": result["changed"]}
