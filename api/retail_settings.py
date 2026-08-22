# -*- coding: utf-8 -*-
"""零售参数集中设置

管理 POS 相关的零售参数：
- 小票标题/页脚
- 打印份数
- 抹零方式
- 前台允许改价
- 打印延迟
- POS 默认设置
"""
import frappe
from frappe import _

# 默认配置
DEFAULTS = {
    "receipt_title_1": "Solua Home",
    "receipt_title_2": "Lda",
    "receipt_footer_1": "Obrigado pela preferência!",
    "receipt_footer_2": "",
    "receipt_footer_3": "www.solua.one",
    "receipt_footer_4": "",
    "print_copies": 1,
    "rounding_method": "不处理",
    "allow_price_override": 0,
    "price_override_requires_approval": 1,
    "max_discount_pct": 0,
    "print_delay_hours": 0,
    "default_warehouse": "Finished Goods - SH",
    "receipt_format": "条码+品名+数量+单价+小计",
}


@frappe.whitelist()
def get_retail_settings():
    """获取零售参数"""
    settings = frappe.get_single("Retail Settings") if frappe.db.exists("DocType", "Retail Settings") else None
    if settings:
        return {
            "receipt_title_1": getattr(settings, "receipt_title_1", DEFAULTS["receipt_title_1"]),
            "receipt_title_2": getattr(settings, "receipt_title_2", DEFAULTS["receipt_title_2"]),
            "receipt_footer_1": getattr(settings, "receipt_footer_1", DEFAULTS["receipt_footer_1"]),
            "receipt_footer_2": getattr(settings, "receipt_footer_2", DEFAULTS["receipt_footer_2"]),
            "receipt_footer_3": getattr(settings, "receipt_footer_3", DEFAULTS["receipt_footer_3"]),
            "receipt_footer_4": getattr(settings, "receipt_footer_4", DEFAULTS["receipt_footer_4"]),
            "print_copies": getattr(settings, "print_copies", DEFAULTS["print_copies"]),
            "rounding_method": getattr(settings, "rounding_method", DEFAULTS["rounding_method"]),
            "allow_price_override": getattr(settings, "allow_price_override", DEFAULTS["allow_price_override"]),
            "price_override_requires_approval": getattr(settings, "price_override_requires_approval", DEFAULTS["price_override_requires_approval"]),
            "max_discount_pct": getattr(settings, "max_discount_pct", DEFAULTS["max_discount_pct"]),
            "print_delay_hours": getattr(settings, "print_delay_hours", DEFAULTS["print_delay_hours"]),
            "default_warehouse": getattr(settings, "default_warehouse", DEFAULTS["default_warehouse"]),
            "receipt_format": getattr(settings, "receipt_format", DEFAULTS["receipt_format"]),
        }
    return DEFAULTS.copy()


@frappe.whitelist()
def save_retail_settings(**kwargs):
    """保存零售参数（仅管理员可操作）"""
    if frappe.session.user != "Administrator":
        frappe.throw(_("仅管理员可修改零售参数"))

    if not frappe.db.exists("DocType", "Retail Settings"):
        frappe.throw(_("Retail Settings DocType 未创建，请先运行安装脚本"))

    settings = frappe.get_single("Retail Settings")
    for key, val in kwargs.items():
        if key in DEFAULTS:
            setattr(settings, key, val)
    settings.save(ignore_permissions=True)
    frappe.db.commit()
    return {"status": "ok", "message": "零售参数已保存"}


@frappe.whitelist()
def apply_rounding(amount, method=None):
    """按抹零方式处理金额

    Args:
        amount: 原始金额
        method: 抹零方式（不处理/四舍五入到角/四舍五入到元/舍去分/舍去角/手动抹零）
    """
    if not method:
        settings = get_retail_settings()
        method = settings.get("rounding_method", "不处理")

    if method == "不处理":
        return {"rounded": amount, "method": method, "difference": 0}
    elif method == "四舍五入到角":
        rounded = round(amount, 1)
    elif method == "四舍五入到元":
        rounded = round(amount, 0)
    elif method == "舍去分":
        import math
        rounded = math.floor(amount * 100) / 100
    elif method == "舍去角":
        import math
        rounded = math.floor(amount * 10) / 10
    else:
        rounded = amount

    return {
        "rounded": rounded,
        "method": method,
        "difference": round(amount - rounded, 2),
    }
