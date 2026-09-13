# -*- coding: utf-8 -*-
"""批发销售单使用的颜色和公开色卡 Jinja helper。"""

import base64
from io import BytesIO

import frappe

from solua_home.api.color_card import get_public_color_card_url


def _absolute_image(image):
    if not image:
        return ""
    if image.startswith(("http://", "https://", "data:")):
        return image
    return frappe.utils.get_url(image)


def get_item_color_info(item_code):
    """返回销售单一行的固定色号、对外货号、图片和色卡地址。"""
    if not item_code:
        return {}

    item = frappe.get_doc("Item", item_code)
    attrs = {
        row.attribute: row.attribute_value
        for row in frappe.get_all(
            "Item Variant Attribute",
            filters={"parent": item.name},
            fields=["attribute", "attribute_value"],
        )
    }
    template_code = item.variant_of or (item.item_code if item.has_variants else "")
    template = frappe.get_doc("Item", template_code) if template_code else item
    return {
        "item_code": item.item_code,
        "order_code": item.get("custom_order_code") or item.item_code,
        "color_code": item.get("custom_color_code") or "",
        "color_name": attrs.get("Cor") or item.get("custom_pos_short_name") or "",
        "display_name": item.get("custom_chinese_name") or item.item_name,
        "image": _absolute_image(item.get("custom_swatch_image") or item.get("image")),
        "template_code": template.item_code,
        "template_name": template.get("custom_chinese_name") or template.item_name,
        "card_url": get_public_color_card_url(template.item_code),
    }


def get_color_card_qr_img(item_code):
    """生成公开色卡地址的二维码 PNG data URI；未发布或依赖缺失时返回空字符串。"""
    url = get_public_color_card_url(item_code)
    if not url:
        return ""
    try:
        import qrcode
    except ImportError:
        frappe.log_error("缺少 qrcode 依赖，无法生成色卡二维码", "solua_home.color_card")
        return ""

    try:
        image = qrcode.make(url)
        output = BytesIO()
        image.save(output, format="PNG")
        encoded = base64.b64encode(output.getvalue()).decode()
        return f"data:image/png;base64,{encoded}"
    except Exception as e:
        frappe.log_error(f"色卡二维码生成失败: {e}", "solua_home.color_card")
        return ""
