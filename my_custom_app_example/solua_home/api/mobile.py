"""Administrator-only mobile lookup API."""

import frappe
from frappe import _

from solua_home.api.home import _resolve_company, _resolve_warehouse
from solua_home.api.sales import (
    _display_price,
    _json_value,
    _resolve_sales_rows,
    _positive_integer,
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


def _customer(customer):
    customer = str(customer or "").strip()
    if not customer:
        frappe.throw(_("请先选择客户"))
    result = frappe.db.get_value(
        "Customer", {"name": customer, "disabled": 0}, ["name", "customer_name"], as_dict=True
    )
    if not result:
        frappe.throw(_("客户不存在或已停用"))
    return result


@frappe.whitelist()
def search_customers(query):
    _require_admin()
    query = str(query or "").strip()
    if len(query) < 2:
        return []
    like = f"%{query}%"
    rows = frappe.get_list(
        "Customer",
        filters={"disabled": 0},
        or_filters=[[field, "like", like] for field in ("name", "customer_name", "mobile_no")],
        fields=["name", "customer_name", "mobile_no"],
        limit_page_length=12,
        order_by="customer_name asc",
    )
    return [
        {"customer": row.name, "customer_name": row.customer_name or row.name, "mobile_no": row.mobile_no or ""}
        for row in rows
    ]


@frappe.whitelist()
def get_customer_addresses(customer):
    _require_admin()
    customer = _customer(customer)
    names = frappe.get_all(
        "Dynamic Link",
        filters={
            "parenttype": "Address",
            "parentfield": "links",
            "link_doctype": "Customer",
            "link_name": customer.name,
        },
        pluck="parent",
        limit_page_length=50,
    )
    if not names:
        return []
    rows = frappe.get_all(
        "Address",
        filters={"name": ["in", names]},
        fields=["name", "address_title", "address_line1", "city", "phone", "is_primary_address"],
        order_by="is_primary_address desc, name asc",
        limit_page_length=50,
    )
    return [
        {
            "address": row.name,
            "title": row.address_title or row.name,
            "line1": row.address_line1 or "",
            "city": row.city or "",
            "phone": row.phone or "",
        }
        for row in rows
    ]


def _order_context(customer, warehouse=None):
    defaults = _defaults()
    if not defaults["company"]:
        frappe.throw(_("没有可访问的公司"))
    warehouse = str(warehouse or "").strip() or defaults["warehouse"]
    if warehouse and not frappe.db.exists(
        "Warehouse", {"name": warehouse, "company": defaults["company"], "is_group": 0}
    ):
        frappe.throw(_("仓库无效：{0}").format(warehouse))
    return {
        "company": defaults["company"],
        "customer": _customer(customer).name,
        "set_warehouse": warehouse,
        "price_list": "Wholesale Selling",
        "selling_price_list": "Wholesale Selling",
        "transaction_date": frappe.utils.nowdate(),
    }


def _validate_order_address(customer, address):
    address = str(address or "").strip()
    if address and not frappe.db.exists(
        "Dynamic Link",
        {"parenttype": "Address", "parent": address, "link_doctype": "Customer", "link_name": customer},
    ):
        frappe.throw(_("所选地址不属于当前客户"))
    return address


def _order_rows(rows, warehouse):
    rows = _json_value(rows)
    if not isinstance(rows, list) or not rows:
        frappe.throw(_("购物车不能为空"))
    if len(rows) > 100:
        frappe.throw(_("购物车商品不能超过 100 行"))
    normalized = []
    for row in rows:
        row = row or {}
        qty = _positive_integer(row.get("qty"))
        item_code = str(row.get("item_code") or "").strip()
        if not item_code or qty is None:
            frappe.throw(_("购物车中存在无效货号或数量"))
        normalized.append({"item_code": item_code, "qty": qty, "warehouse": str(row.get("warehouse") or warehouse).strip()})
    return normalized


def _apply_order_data(doc, context, address, resolved_rows):
    doc.customer = context["customer"]
    doc.company = context["company"]
    doc.transaction_date = context["transaction_date"]
    doc.selling_price_list = context["selling_price_list"]
    doc.set_warehouse = context["set_warehouse"]
    for field, value in (("customer_address", address), ("shipping_address_name", address)):
        if frappe.get_meta("Sales Order").has_field(field):
            setattr(doc, field, value or "")
    doc.set("items", [])
    item_meta = frappe.get_meta("Sales Order Item")
    for row in resolved_rows:
        item = doc.append("items", {})
        for field in ("item_code", "item_name", "description", "uom", "stock_uom", "conversion_factor", "stock_qty", "rate", "price_list_rate", "warehouse", "qty"):
            if item_meta.has_field(field) and field in row:
                setattr(item, field, row[field])
        if item_meta.has_field("delivery_date"):
            item.delivery_date = context["transaction_date"]


@frappe.whitelist()
def save_sales_order(customer, rows, warehouse=None, address=None, name=None, submit=0):
    _require_admin()
    context = _order_context(customer, warehouse)
    address = _validate_order_address(context["customer"], address)
    normalized = _order_rows(rows, context["set_warehouse"])
    resolved = _resolve_sales_rows(normalized, context, strict=True)
    if resolved["errors"]:
        frappe.throw("；".join(error.get("error") or "商品无法加入订单" for error in resolved["errors"]))

    if name:
        doc = frappe.get_doc("Sales Order", str(name).strip())
        if doc.docstatus != 0:
            frappe.throw(_("销售订单已经提交，不能重复修改"))
    else:
        doc = frappe.new_doc("Sales Order")
    _apply_order_data(doc, context, address, resolved["rows"])
    if doc.is_new():
        doc.insert()
    else:
        doc.save()
    if int(submit or 0):
        doc.submit()
    return {
        "state": "submitted" if doc.docstatus == 1 else "draft",
        "name": doc.name,
        "docstatus": doc.docstatus,
        "status": doc.status,
        "customer": doc.customer,
        "grand_total": doc.grand_total,
        "currency": doc.currency,
        "items": len(doc.items),
    }


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
