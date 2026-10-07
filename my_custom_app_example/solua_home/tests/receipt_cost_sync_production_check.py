"""One-off live DocType check; call only through bench execute, always rolling back."""

import frappe
from frappe.utils import add_days, flt, nowdate


def check_item_price_precision_rollback():
    item = frappe.get_all(
        "Item", filters={"is_stock_item": 1, "disabled": 0, "has_variants": 0}, fields=["name", "stock_uom"],
        order_by="name asc", limit_page_length=1,
    )
    if not item:
        frappe.throw("没有可用于临时价目表精度验证的库存商品。")
    currency = frappe.db.get_value("Price List", "Standard Buying", "currency")
    if currency != "MZN":
        frappe.throw("Standard Buying 价目表当前不是MZN，停止精度验证。")
    try:
        price = frappe.get_doc({
            "doctype": "Item Price",
            "item_code": item[0].name,
            "price_list": "Standard Buying",
            "buying": 1,
            "selling": 0,
            "uom": item[0].stock_uom,
            "currency": currency,
            "price_list_rate": 10 / 3,
            "valid_from": add_days(nowdate(), 2),
        }).insert(ignore_permissions=True)
        stored = frappe.db.get_value("Item Price", price.name, "price_list_rate")
        precision = frappe.get_precision("Item Price", "price_list_rate")
        expected = flt(10 / 3, precision)
        if flt(stored, precision) != expected:
            raise AssertionError(f"Item Price DB rate {stored!r} did not round to {expected!r}")
        return {"input": "10/3", "stored_rate": float(stored), "precision": precision,
                "rollback": "completed in finally"}
    finally:
        frappe.db.rollback()


def check_live_field_and_price_floor():
    field = frappe.db.get_value(
        "Custom Field", {"dt": "Item", "fieldname": "custom_receipt_cost_sync"},
        ["fieldtype", "hidden", "read_only", "no_copy"], as_dict=True,
    )
    if not field or field.fieldtype != "Long Text" or not field.hidden or not field.read_only or not field.no_copy:
        raise AssertionError("The hidden Item cost-sync ledger field is missing or has unexpected flags")

    from solua_home.receipt_cost_sync import current_reference_rate
    from solua_home.api.sales import check_price_above_cost

    candidates = frappe.get_all(
        "Item Price", filters={"price_list": "Standard Buying", "currency": "MZN"},
        fields=["item_code"], limit_page_length=500,
    )
    for item_code in dict.fromkeys(row.item_code for row in candidates):
        stock_uom = frappe.db.get_value("Item", item_code, "stock_uom")
        rate = current_reference_rate(item_code, stock_uom)
        if not rate or rate <= 0.01:
            continue
        below = check_price_above_cost(item_code, rate - 0.01)
        equal = check_price_above_cost(item_code, rate)
        if below.get("ok") or flt(below.get("cost")) != flt(rate) or not equal.get("ok"):
            raise AssertionError("Live POS price check did not use the active Standard Buying reference")
        return {"field": "hidden Long Text present", "floor": "active Standard Buying", "rate": float(rate),
                "below_rejected": True, "equal_allowed": True}
    frappe.throw("未找到可用于只读验证的有效Standard Buying库存单位参考价。")
