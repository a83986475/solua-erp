# -*- coding: utf-8 -*-
import frappe


def extended_bootinfo(bootinfo):
    """注入自定义 boot 信息"""
    from solua_home.api.home import get_home_page

    # Respect explicit xPos/default workspace choices. Ordinary System Users
    # share the permission-aware wholesale page; this is only boot metadata.
    home_page = get_home_page(frappe.session.user)
    if home_page:
        bootinfo["home_page"] = home_page
    bootinfo["solua_home"] = {
        "version": "0.0.1",
        "app_name": "solua_home",
        "default_page": home_page,
        "curtain_colors": get_curtain_colors(),
    }


def get_curtain_colors():
    """获取窗帘颜色列表 (Cor Item Attribute 的值)"""
    try:
        attr = frappe.get_cached_doc("Item Attribute", "Cor")
        return [
            {"value": v.attribute_value, "abbr": v.abbr}
            for v in attr.item_attribute_values
        ]
    except Exception:
        return []
