# -*- coding: utf-8 -*-
"""商品打包（Product Bundle Definition）

功能：
- 同一商品不同包装单位（如 1件/3件/5件），各有独立条码
- POS 扫条码自动识别是单品还是打包，按打包数量加购
- 打包可以有独立价格（打包优惠价）或按单价×数量

打包条码规则建议：
- 单品条码：原条码（如 6901234567892）
- 3件装条码：原条码 + 后缀（如 6901234567892-3）
- 或使用完全独立的条码
"""
import frappe
from frappe import _


@frappe.whitelist()
def get_bundle_definitions(item_code=None):
    """获取商品打包定义列表

    Args:
        item_code: 指定物料（可选，不传则返回所有）
    """
    filters = {}
    if item_code:
        filters["parent_item"] = item_code

    bundles = frappe.get_all(
        "Product Bundle Definition",
        filters=filters,
        fields=["name", "parent_item", "bundle_name", "barcode",
                "quantity", "bundle_price", "is_active"],
        order_by="parent_item, quantity",
    )

    result = []
    for b in bundles:
        if not b.is_active:
            continue
        # 获取物料名称
        item_name = frappe.db.get_value("Item", b.parent_item, "item_name") or ""
        chinese_name = frappe.db.get_value("Item", b.parent_item, "custom_chinese_name") or ""
        result.append({
            "name": b.name,
            "parent_item": b.parent_item,
            "item_name": item_name,
            "chinese_name": chinese_name,
            "bundle_name": b.bundle_name,
            "barcode": b.barcode,
            "quantity": b.quantity,
            "bundle_price": b.bundle_price,
            "unit_price": round(b.bundle_price / b.quantity, 2) if b.bundle_price and b.quantity else 0,
        })

    return result


@frappe.whitelist()
def resolve_barcode_for_pos(barcode):
    """POS 扫码时解析条码（先查打包定义，再查普通条码）

    Returns:
        dict with type:
        - "bundle": 打包条码，返回 bundle 信息 + parent_item
        - "single": 单品条码，返回 item 信息
        - "not_found": 未找到
    """
    if not barcode:
        return {"type": "not_found"}

    # 1. 查打包条码
    bundle = frappe.db.get_value(
        "Product Bundle Definition",
        {"barcode": barcode, "is_active": 1},
        ["name", "parent_item", "bundle_name", "quantity", "bundle_price"],
        as_dict=True,
    )

    if bundle:
        item = frappe.get_doc("Item", bundle.parent_item)
        # 获取变体信息
        is_variant = bool(item.variant_of)
        is_template = bool(item.has_variants)

        return {
            "type": "bundle",
            "bundle_name": bundle.bundle_name,
            "parent_item": bundle.parent_item,
            "item_name": item.item_name,
            "chinese_name": item.custom_chinese_name or "",
            "quantity": bundle.quantity,
            "bundle_price": bundle.bundle_price,
            "unit_price": round(bundle.bundle_price / bundle.quantity, 2) if bundle.bundle_price else 0,
            "is_variant": is_variant,
            "is_template": is_template,
            "variant_of": item.variant_of or "",
        }

    # 2. 查普通条码（Item Barcode 子表）
    item_code = frappe.db.get_value("Item Barcode", {"barcode": barcode}, "parent")
    if item_code:
        item = frappe.get_doc("Item", item_code)
        return {
            "type": "single",
            "item_code": item_code,
            "item_name": item.item_name,
            "chinese_name": item.custom_chinese_name or "",
            "has_variants": bool(item.has_variants),
            "variant_of": item.variant_of or "",
        }

    # 3. 兜底：条码=物料编码
    item_code = frappe.db.get_value("Item", {"item_code": barcode, "disabled": 0}, "name")
    if item_code:
        item = frappe.get_doc("Item", item_code)
        return {
            "type": "single",
            "item_code": item_code,
            "item_name": item.item_name,
            "chinese_name": item.custom_chinese_name or "",
            "has_variants": bool(item.has_variants),
            "variant_of": item.variant_of or "",
        }

    return {"type": "not_found"}


@frappe.whitelist()
def create_bundle(parent_item, bundles):
    """创建商品打包定义

    Args:
        parent_item: 母物料编码
        bundles: list of dict, each with:
            - bundle_name: 打包名称（如 "3件装"）
            - barcode: 打包条码
            - quantity: 包含数量
            - bundle_price: 打包总价（可选，不填则按单价×数量）
    """
    if isinstance(bundles, str):
        import json
        bundles = json.loads(bundles)

    # 验证母物料存在
    if not frappe.db.exists("Item", parent_item):
        frappe.throw(_("物料 {0} 不存在").format(parent_item))

    # 获取单品价格
    unit_price = frappe.db.get_value(
        "Item Price",
        {"item_code": parent_item, "selling": 1},
        "price_list_rate",
    ) or 0

    created = []
    for b in bundles:
        qty = int(b.get("quantity", 1))
        bp = b.get("bundle_price")
        if not bp:
            bp = round(unit_price * qty, 2)

        doc = frappe.get_doc({
            "doctype": "Product Bundle Definition",
            "parent_item": parent_item,
            "bundle_name": b.get("bundle_name", f"{qty}件装"),
            "barcode": b.get("barcode", ""),
            "quantity": qty,
            "bundle_price": bp,
            "is_active": 1,
        })
        doc.insert(ignore_permissions=True)
        created.append(doc.name)

    frappe.db.commit()
    return {"status": "ok", "created": created, "count": len(created)}
