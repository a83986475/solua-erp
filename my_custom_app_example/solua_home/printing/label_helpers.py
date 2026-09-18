# -*- coding: utf-8 -*-
# solua_home/printing/label_helpers.py
# 价格标签打印格式的 Jinja helper：
#   get_barcode_img(doc)  -> 条码 base64 PNG data URI（无条码返回空字符串）
#   get_selling_price(doc)-> 现价格式化字符串（无价格返回 "—"）
# 依赖：python-barcode（服务器 bench env 已安装，Pillow 为 frappe 自带）

import base64
from io import BytesIO

import frappe

DEFAULT_PRICE_LIST = "Standard Selling"
DEFAULT_CURRENCY = "MZN"


def get_barcode_img(doc, font_size=8, module_height=8):
    """渲染物料标签条码为 PNG data URI（可直接放进 <img>）。

    2026-08-08 简化：统一 Code 128 渲染（放弃 EAN-13）——
    - 数字/字母/符号都可编码，任意值原样输出（图=库，永不错位）
    - 不再依赖 EAN-13 校验位，无需区分正确/错误校验位
    - 无条码返回空字符串（模板里自动隐藏）
    """
    barcode_value, _barcode_type = _get_barcode(doc)
    if not barcode_value:
        return ""

    try:
        import barcode as python_barcode
        from barcode.writer import ImageWriter
    except ImportError:
        return ""

    try:
        writer = ImageWriter()
        writer.set_options({
            "module_width": 0.2,
            "module_height": module_height,
            "font_size": font_size,
            "quiet_zone": 1.5,
            "dpi": 300,
        })
        code = python_barcode.get("code128", str(barcode_value), writer=writer)
        buf = BytesIO()
        code.write(buf)
        data = buf.getvalue()
        return f"data:image/png;base64,{base64.b64encode(data).decode()}"
    except Exception:
        frappe.log_error(f"条码渲染失败: {barcode_value}", "solua_home")
        return ""


def _get_barcode(doc):
    """取物料的标签条码。

    策略（2026-08-08 更新）：
    - 物料自己有子表条码 → 用它（按声明的 barcode_type 渲染）
    - 变体没有独立条码 → 用变体编码（如 CR-001-BR），code128 原样打印，
      扫码直接定位到具体颜色，无需再选色
    - 模板 / 其余 → 模板子表条码（同条码多色时扫码仍弹选色）
    """
    def _first_barcode(item):
        if getattr(item, "barcodes", None):
            for row in item.barcodes:
                if row.barcode:
                    return row.barcode, (row.barcode_type or "").lower()
        return None, ""

    value, btype = _first_barcode(doc)
    if value:
        return value, btype

    variant_of = getattr(doc, "variant_of", None)
    if variant_of:
        if doc.get("name"):
            # 变体无独立条码 → 打印变体编码（Code 128，字母数字皆可）
            return doc.name, "code128"
        # 兜底：doc 尚无 name 时取模板条码
        try:
            tpl = frappe.get_doc("Item", variant_of)
        except frappe.DoesNotExistError:
            return None, ""
        value, btype = _first_barcode(tpl)
        if value:
            return value, btype

    return None, ""


def get_selling_price(doc, price_list=None, currency=None):
    """取物料现价（Standard Selling），返回格式化字符串。

    无价格时返回 "—"（模板里显示占位符）。
    """
    price_list = price_list or DEFAULT_PRICE_LIST
    currency = currency or frappe.db.get_single_value("Global Defaults", "default_currency") or DEFAULT_CURRENCY

    rate = frappe.db.get_value(
        "Item Price",
        {"item_code": doc.name, "price_list": price_list},
        "price_list_rate",
    )
    if not rate:
        return "—"
    return frappe.utils.fmt_money(rate, currency=currency, precision=0)
