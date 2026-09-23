# -*- coding: utf-8 -*-
"""公开色卡查询与内部商品展示数据。

公开接口只返回明确允许发布的 Item 字段，库存、价格、仓库和内部备注不会进入响应。
"""

from urllib.parse import quote

import frappe
from frappe import _
from frappe.utils import get_url


def _has_column(fieldname):
    return frappe.db.has_column("Item", fieldname)


def _item_fields():
    fields = [
        "name", "item_code", "item_name", "image", "stock_uom",
        "variant_of", "has_variants", "disabled",
        "custom_chinese_name", "custom_spu_code", "custom_spec_summary",
        "custom_pos_short_name", "custom_swatch_image",
    ]
    for fieldname in [
        "custom_color_code", "custom_order_code", "custom_color_card_published",
    ]:
        if _has_column(fieldname):
            fields.append(fieldname)
    return fields


def _find_item_codes(query):
    """按款号、对外货号、SPU、完整变体货号或共用条码精确定位物料。"""
    query = (query or "").strip()
    if not query or len(query) > 120:
        return []

    codes = []
    for fieldname in ["name", "item_code"]:
        codes.extend(
            row.name
            for row in frappe.get_all(
                "Item",
                filters={fieldname: query, "disabled": 0},
                fields=["name"],
                limit=10,
            )
        )

    for fieldname in ["custom_order_code", "custom_spu_code"]:
        if not _has_column(fieldname):
            continue
        codes.extend(
            row.name
            for row in frappe.get_all(
                "Item",
                filters={fieldname: query, "disabled": 0},
                fields=["name"],
                limit=10,
            )
        )

    barcode_parent = frappe.db.get_value("Item Barcode", {"barcode": query}, "parent")
    if barcode_parent:
        codes.append(barcode_parent)

    return list(dict.fromkeys(codes))


def _is_published(item_code):
    return bool(
        _has_column("custom_color_card_published")
        and frappe.db.get_value("Item", item_code, "custom_color_card_published")
    )


def _variant_attributes(item_code):
    rows = frappe.get_all(
        "Item Variant Attribute",
        filters={"parent": item_code},
        fields=["attribute", "attribute_value"],
    )
    return {row.attribute: row.attribute_value for row in rows}


def get_item_cor(item_code, item=None):
    """Return native Cor; only fall back for legacy records with no Cor row."""
    if not item_code:
        return ""
    color = (_variant_attributes(item_code).get("Cor") or "").strip()
    if color:
        return color
    # Compatibility only: old history may still have the retired duplicate field.
    if item is None:
        item = frappe.get_doc("Item", item_code)
    return str(item.get("custom_color_code") or "").strip()


def _public_variant(item):
    image = item.get("custom_swatch_image") or item.get("image") or ""
    return {
        "item_code": item.item_code,
        "order_code": item.get("custom_order_code") or item.item_code,
        "color_code": get_item_cor(item.name, item),
        "color_name": _variant_attributes(item.name).get("Cor") or item.get("custom_pos_short_name") or "",
        "name": item.get("custom_chinese_name") or item.item_name,
        "item_name": item.item_name,
        "image": image,
        "spec_summary": item.get("custom_spec_summary") or "",
        "stock_uom": item.get("stock_uom") or "",
    }


def _build_public_card(template_code):
    if not _is_published(template_code):
        return None

    template = frappe.get_doc("Item", template_code)
    fields = _item_fields()
    variants = frappe.get_all(
        "Item",
        filters={
            "variant_of": template_code,
            "disabled": 0,
            "custom_color_card_published": 1,
        },
        fields=fields,
        order_by="item_code asc",
    )

    return {
        "template_code": template.item_code,
        "order_code": template.get("custom_order_code") or template.item_code,
        "spu_code": template.get("custom_spu_code") or "",
        "name": template.get("custom_chinese_name") or template.item_name,
        "item_name": template.item_name,
        "image": template.get("image") or "",
        "spec_summary": template.get("custom_spec_summary") or "",
        "stock_uom": template.get("stock_uom") or "",
        "variants": [_public_variant(item) for item in variants],
    }


@frappe.whitelist(allow_guest=True)
def get_public_color_card(query=None):
    """公开查询色卡；未发布商品统一返回 not_found。"""
    for item_code in _find_item_codes(query):
        item = frappe.db.get_value(
            "Item",
            item_code,
            ["item_code", "variant_of", "has_variants", "disabled"],
            as_dict=True,
        )
        if not item or item.disabled:
            continue
        template_code = item.variant_of or (item.item_code if item.has_variants else None)
        if template_code:
            card = _build_public_card(template_code)
            if card:
                return card

    return None


def get_public_color_card_url(item_or_code):
    """供 Jinja 打印使用的公开色卡地址；未发布时返回空字符串。"""
    item_code = getattr(item_or_code, "name", None) or getattr(item_or_code, "item_code", None)
    item_code = item_code or (item_or_code if isinstance(item_or_code, str) else "")
    if not item_code:
        return ""

    item = frappe.db.get_value(
        "Item", item_code, ["item_code", "variant_of", "has_variants", "custom_order_code"], as_dict=True
    )
    if not item:
        return ""
    template_code = item.variant_of or (item.item_code if item.has_variants else None)
    if not template_code or not _is_published(template_code):
        return ""

    key = frappe.db.get_value("Item", template_code, "custom_order_code") or template_code
    return f"{get_url('/colors')}?q={quote(str(key))}"
