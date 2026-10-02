"""Administrator-only mobile lookup API."""

import frappe
from frappe import _

from solua_home.api.home import _resolve_company, _resolve_warehouse
from solua_home.api.sales import (
    _display_price,
    get_sales_order_color_variants,
    search_sales_order_items,
)


def _require_admin():
    if frappe.session.user != "Administrator" and "System Manager" not in frappe.get_roles():
        frappe.throw(_("仅系统管理员可使用移动管理台"), frappe.PermissionError)


def _defaults():
    company = _resolve_company()
    warehouse = _resolve_warehouse(company) if company else None
    return {
        "company": company.name if company else "",
        "currency": company.default_currency if company else "MZN",
        "warehouse": warehouse or "",
    }


@frappe.whitelist()
def get_defaults():
    _require_admin()
    result = _defaults()
    if not result["company"]:
        return {"state": "no_permission", "message": _("没有可访问的公司")}
    return {"state": "ok", **result}


def _decorate_prices(result, context):
    for row in result.get("variants") or []:
        row["wholesale_rate_1"] = row.get("wholesale_rate") or 0
        row["wholesale_rate_3"] = _display_price(
            row.get("item_code"), context, "Wholesale Selling 3", context.get("set_warehouse")
        )
    return result


@frappe.whitelist()
def lookup(barcode, warehouse=None):
    _require_admin()
    defaults = _defaults()
    if not defaults["company"]:
        return {"state": "no_permission", "templates": [], "variants": []}

    context = {
        "company": defaults["company"],
        "set_warehouse": str(warehouse or "").strip() or defaults["warehouse"],
        "price_list": "Wholesale Selling",
        "selling_price_list": "Wholesale Selling",
    }
    query = str(barcode or "").strip()
    if not query:
        return {"state": "no_data", "templates": [], "variants": []}

    result = get_sales_order_color_variants(barcode=query, context=context)
    if result.get("variants"):
        return _decorate_prices(result, context)

    fuzzy = search_sales_order_items(
        context=context,
        filters={"search": query, "warehouse": context["set_warehouse"]},
    )
    return _decorate_prices(
        {
            "state": "ok" if fuzzy.get("items") else "no_data",
            "title": _("搜索结果：{0}").format(query),
            "templates": [],
            "variants": fuzzy.get("items") or [],
            "errors": fuzzy.get("errors") or [],
        },
        context,
    )
