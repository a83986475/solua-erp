# -*- coding: utf-8 -*-
# Copyright (c) 2026, yangyang7920 and contributors
# For license information, please see license.txt

import frappe
from frappe import _


@frappe.whitelist()
def get_template_variants(template_item):
    """获取指定模板物料的所有变体

    Args:
        template_item: 模板物料编码

    Returns:
        list: 变体列表，每个变体包含 item_code, item_name, attributes 等信息
    """
    if not template_item:
        return []

    fields = [
        "item_code", "item_name", "custom_chinese_name",
        "custom_spec_summary", "custom_pos_short_name",
        "image", "custom_swatch_image", "stock_uom", "disabled",
        "item_group", "brand",
    ]
    for fieldname in ["custom_order_code"]:
        if frappe.db.has_column("Item", fieldname):
            fields.append(fieldname)

    variants = frappe.get_list(
        "Item",
        filters={
            "variant_of": template_item,
            "disabled": 0,
        },
        fields=fields,
        order_by="item_code asc",
    )

    # 为每个变体获取属性值
    result = []
    for v in variants:
        attrs = frappe.get_all(
            "Item Variant Attribute",
            filters={"parent": v.item_code},
            fields=["attribute", "attribute_value"],
        )
        v["attributes"] = {a.attribute: a.attribute_value for a in attrs}
        result.append(v)

    return result


@frappe.whitelist()
def get_template_stock_summary(template_item, warehouse=None):
    """获取模板物料下所有变体的库存汇总

    Args:
        template_item: 模板物料编码
        warehouse: 可选，指定仓库

    Returns:
        dict: {
            "template_code": "...",
            "template_name": "...",
            "total_stock": 123,
            "variants": [
                {
                    "item_code": "...",
                    "item_name": "...",
                    "attributes": {...},
                    "actual_qty": 10,
                    "warehouse": "..." (if specified)
                },
                ...
            ]
        }
    """
    if not template_item:
        frappe.throw(_("Please specify a template item"))

    template = frappe.get_doc("Item", template_item)
    if not template.has_variants:
        frappe.throw(_("{0} is not a template item").format(template_item))

    variants = get_template_variants(template_item)
    total_stock = 0

    filters = {"item_code": ["in", [v.item_code for v in variants]]}
    if warehouse:
        filters["warehouse"] = warehouse

    stock_data = {}
    try:
        bins = frappe.get_list(
            "Bin",
            filters=filters,
            fields=["item_code", "warehouse", "actual_qty"],
        )
    except frappe.PermissionError:
        bins = []

    for d in bins:
        key = d.item_code
        if key not in stock_data:
            stock_data[key] = 0
        stock_data[key] += d.actual_qty
        total_stock += d.actual_qty

    for v in variants:
        v["actual_qty"] = stock_data.get(v.item_code, 0)

    return {
        "template_code": template.item_code,
        "template_name": template.item_name,
        "template_spu": template.custom_spu_code,
        "total_stock": total_stock,
        "variants": variants,
    }


@frappe.whitelist()
def get_attribute_values(attribute_name):
    """获取指定属性的所有可选值

    Args:
        attribute_name: 属性名称（如 Color, Size）

    Returns:
        list: 属性值列表 [{attribute_value, abbr}, ...]
    """
    if not attribute_name:
        return []

    if not frappe.db.exists("Item Attribute", attribute_name):
        return []

    attr = frappe.get_doc("Item Attribute", attribute_name)

    return [
        {"attribute_value": v.attribute_value, "abbr": v.abbr}
        for v in attr.item_attribute_values
    ]


@frappe.whitelist()
def bulk_create_variants(template_item, attribute_values=None, price_list=None):
    """批量生成变体向导：模板 + 勾选的颜色值 -> 自动建变体

    Args:
        template_item: 模板物料编码（has_variants=1）
        attribute_values: 要生成的颜色值列表，如 ["Branco", "Azul"]
                          （None 或空 = 属性全部值）
        price_list: 价格表名（默认 Standard Selling）

    Returns:
        dict: {created: [codes], skipped: [codes], errors: [{color, error}]}
    """
    if not template_item:
        frappe.throw(_("请选择模板物料"))

    template = frappe.get_doc("Item", template_item)
    if not template.has_variants:
        frappe.throw(_("{0} 不是多规格模板物料").format(template_item))

    # 模板使用的属性（窗帘场景 = Cor）
    template_attrs = [a.attribute for a in template.attributes]
    if not template_attrs:
        frappe.throw(_("模板 {0} 的 Attributes 为空，请先添加属性（如 Cor）").format(template_item))

    # 收集所有属性值（默认用第一个属性的全部值；支持多属性组合）
    if attribute_values:
        if isinstance(attribute_values, str):
            attribute_values = frappe.parse_json(attribute_values)
        selected = [str(v).strip() for v in attribute_values if str(v).strip()]
    else:
        selected = []

    # 从 Item Attribute 拉取所有可选值（多属性：笛卡尔组合）
    attr_values_by_attr = {}
    for attr_name in template_attrs:
        attr = frappe.get_doc("Item Attribute", attr_name)
        vals = [v.attribute_value for v in attr.item_attribute_values]
        attr_values_by_attr[attr_name] = vals

    # 组合生成
    import itertools

    combos = [dict(zip(template_attrs, combo)) for combo in itertools.product(*attr_values_by_attr.values())]
    if selected:
        # 只保留用户勾选的颜色（作用于第一个属性，即颜色）
        main_attr = template_attrs[0]
        combos = [c for c in combos if c[main_attr] in selected]

    created, skipped, errors = [], [], []
    price_list = price_list or "Standard Selling"

    for combo in combos:
        args = {k: v for k, v in combo.items()}

        # 已有同属性组合的变体则跳过
        existing = _find_existing_variant(template_item, combo)
        if existing:
            skipped.append(existing)
            continue

        try:
            from erpnext.controllers.item_variant import create_variant

            v = create_variant(template_item, args)
            v.flags.ignore_permissions = True
            v.insert()

            # 继承模板价格
            _ensure_item_price(v.name, template, price_list)
            # 中文名 / POS 简称 自动拼接颜色
            _set_variant_names(v, combo)
            v.save(ignore_permissions=True)
            frappe.db.commit()
            created.append(v.name)
        except Exception as e:
            frappe.db.rollback()
            frappe.log_error(f"变体创建失败 [{template_item} {combo}]: {e}", "solua_home.bulk_variants")
            errors.append({"combo": combo, "error": str(e)[:200]})

    return {
        "created": created,
        "skipped": skipped,
        "errors": errors,
        "total": len(created) + len(skipped) + len(errors),
    }


def _find_existing_variant(template_item, combo):
    """按模板 + 属性组合查已有变体"""
    items = frappe.get_all("Item", filters={"variant_of": template_item}, fields=["name"])
    for it in items:
        attrs = frappe.get_all(
            "Item Variant Attribute",
            filters={"parent": it.name},
            fields=["attribute", "attribute_value"],
        )
        a = {x.attribute: x.attribute_value for x in attrs}
        if all(a.get(k) == v for k, v in combo.items()):
            return it.name
    return None


def _ensure_item_price(variant_name, template, price_list="Standard Selling"):
    """变体创建后确保有价格（继承模板 standard_rate）"""
    existing = frappe.db.get_value(
        "Item Price",
        {"item_code": variant_name, "price_list": price_list},
        "name",
    )
    if existing:
        return

    rate = template.get("standard_rate")
    if not rate:
        return

    currency = frappe.defaults.get_user_default("currency") or frappe.db.get_single_value(
        "Global Defaults", "default_currency"
    ) or "MZN"

    try:
        doc = frappe.get_doc({
            "doctype": "Item Price",
            "item_code": variant_name,
            "price_list": price_list,
            "price_list_rate": rate,
            "selling": 1,
            "currency": currency,
        })
        doc.insert(ignore_permissions=True)
    except Exception as e:
        frappe.log_error(f"变体价格创建失败 [{variant_name}]: {e}", "solua_home.bulk_variants")


def _set_variant_names(variant, combo):
    """变体中文名/POS 简称自动拼接（中文名 + 颜色中文）"""
    color = combo.get("Cor") or next(iter(combo.values()), None)
    if not color:
        return
    color_zh = frappe.db.get_value(
        "Translation",
        {"source_text": color, "language": "zh"},
        "translated_text",
    ) or color

    tpl = frappe.db.get_value("Item", variant.variant_of, ["item_name", "custom_chinese_name"], as_dict=True)
    if tpl:
        # 中文名 = 模板中文名 + 颜色（无论变体是否已继承，统一补齐颜色后缀）
        base_cn = tpl.custom_chinese_name or tpl.item_name
        if base_cn and color_zh and color_zh not in str(variant.custom_chinese_name or ""):
            variant.custom_chinese_name = f"{base_cn}·{color_zh}"
        if not variant.custom_pos_short_name:
            variant.custom_pos_short_name = f"{color_zh}"


@frappe.whitelist()
def get_template_attribute_values(template_item):
    """获取模板可用的属性值（第一个属性的全部可选值，窗帘=颜色池）"""
    if not template_item or not frappe.db.exists("Item", template_item):
        return []

    tpl = frappe.get_doc("Item", template_item)
    attrs = [a.attribute for a in tpl.attributes]
    if not attrs:
        return []

    attr_name = attrs[0]
    attr = frappe.get_doc("Item Attribute", attr_name)
    return [
        {"attribute_value": v.attribute_value, "abbr": v.abbr}
        for v in attr.item_attribute_values
    ]


@frappe.whitelist()
def search_items_by_spu(spu_code):
    """通过 SPU 编码搜索模板物料及其变体

    Args:
        spu_code: SPU 编码

    Returns:
        dict: 模板和变体信息
    """
    if not spu_code:
        return None

    templates = frappe.get_all(
        "Item",
        filters={"custom_spu_code": spu_code, "has_variants": 1},
        fields=["item_code", "item_name", "custom_chinese_name", "custom_spu_code"],
        limit=1,
    )

    if not templates:
        return {
            "template": None,
            "variant_count": 0,
            "variants": [],
        }

    template = templates[0]
    variants = get_template_variants(template.item_code)

    return {
        "template": template,
        "variant_count": len(variants),
        "variants": variants,
    }
