# -*- coding: utf-8 -*-
"""零售参数集中设置 API

参考智百威零售参数设置，包含：
- 小票标题/页脚
- 打印设置（份数/公司名/日期时间/找零）
- 小票显示元素控制
- 抹零方式
- 前台改价/折扣控制
- 前台盘点/自动加购
"""
import frappe
from frappe import _

DEFAULTS = {
    "receipt_title_1": "Solua Home",
    "receipt_title_2": "Lda",
    "receipt_footer_1": "Obrigado pela preferência!",
    "receipt_footer_2": "",
    "receipt_footer_3": "www.solua.one",
    "receipt_footer_4": "",
    "paper_width": "80mm",
    "print_company_name": 1,
    "print_date_time": 1,
    "print_change": 1,
    "print_copies": 1,
    "rounding_method": "None",
    "default_warehouse": "Finished Goods - SH",
    "show_barcode_on_receipt": 1,
    "show_item_name": 1,
    "show_original_price": 0,
    "show_discount": 1,
    "show_qty": 1,
    "show_unit": 1,
    "show_subtotal": 1,
    "show_register_no": 0,
    "allow_price_override": 0,
    "price_override_requires_approval": 1,
    "max_discount_pct": 0,
    "allow_front_inventory": 0,
    "auto_add_item": 0,
    "print_delay_hours": 0,
    "receipt_format": "条码+品名+数量+单价+小计",
}


@frappe.whitelist()
def get_retail_settings():
    """获取零售参数"""
    if not frappe.db.exists("DocType", "Retail Settings"):
        return DEFAULTS.copy()

    settings = frappe.get_single("Retail Settings")
    result = {}
    for key in DEFAULTS:
        result[key] = getattr(settings, key, DEFAULTS[key])
    return result


@frappe.whitelist()
def save_retail_settings(**kwargs):
    """保存零售参数（仅管理员可操作）"""
    if frappe.session.user != "Administrator":
        frappe.throw(_("仅管理员可修改零售参数"))

    if not frappe.db.exists("DocType", "Retail Settings"):
        frappe.throw(_("Retail Settings DocType 未创建"))

    settings = frappe.get_single("Retail Settings")
    for key, val in kwargs.items():
        if key in DEFAULTS:
            # Check 字段需要转 int
            if DEFAULTS[key] in (0, 1):
                val = int(bool(val))
            setattr(settings, key, val)
    settings.save(ignore_permissions=True)
    frappe.db.commit()
    return {"status": "ok", "message": "零售参数已保存"}


@frappe.whitelist()
def apply_rounding(amount, method=None):
    """按抹零方式处理金额"""
    import math
    if not method:
        settings = get_retail_settings()
        method = settings.get("rounding_method", "None")

    if method == "None":
        return {"rounded": amount, "method": method, "difference": 0}
    elif method == "Round to 0.1":
        rounded = round(amount, 1)
    elif method == "Round to 1":
        rounded = round(amount)
    elif method == "Truncate cent":
        rounded = math.floor(amount * 100) / 100
    elif method == "Truncate dec":
        rounded = math.floor(amount * 10) / 10
    else:
        rounded = amount

    return {
        "rounded": rounded,
        "method": method,
        "difference": round(amount - rounded, 2),
    }
