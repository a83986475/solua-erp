"""Administrator-only mobile lookup API."""

import frappe
from frappe import _
from frappe.utils import add_months, flt, getdate, nowdate

from solua_home.api.home import _resolve_company, _resolve_warehouse
from solua_home.api.sales import (
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


@frappe.whitelist()
@frappe.read_only()
def get_mobile_reports(period="month", from_date=None, to_date=None):
    """Return the existing permission-aware business totals for the mobile report hub."""
    _require_admin()
    from solua_home.api.business_totals import METRICS, get_total

    defaults = _defaults()
    metrics = ("orders", "delivered", "invoices", "unbilled", "receivable", "paid")
    reports = []
    for metric in metrics:
        result = get_total(
            metric=metric,
            period=str(period or "month"),
            from_date=from_date,
            to_date=to_date,
        )
        reports.append({
            "key": metric,
            "label": METRICS[metric],
            "state": result.get("state"),
            "amount": result.get("amount"),
            "unallocated_amount": result.get("unallocated_amount") if metric == "paid" else None,
            "currency": result.get("currency") or "MZN",
            "from_date": result.get("from_date") or "",
            "to_date": result.get("to_date") or "",
            "items": (result.get("items") or [])[:10],
        })
    return {
        "state": "ok",
        "period": period,
        "company": defaults["company"],
        "warehouse": defaults["warehouse"],
        "from_date": reports[0].get("from_date") or "",
        "to_date": reports[0].get("to_date") or "",
        "currency": reports[0].get("currency") or defaults["currency"],
        "reports": reports,
    }


MOBILE_REPORTS = {
    "Profitability Analysis": ("盈利能力分析", "profitability"),
    "Template Stock Tree": ("库存树报表", "stock"),
    "Solua Business Totals": ("经营金额报表", "business"),
    "Solua Delivery Summary": ("送货汇总", "delivery"),
    "Item-wise Sales History": ("物料销售明细金额", "item_sales"),
}
MOBILE_REPORT_PAGE_LENGTH = 50
MOBILE_REPORT_MAX_PAGE_LENGTH = 100


def _mobile_report_dates(from_date=None, to_date=None):
    end = getdate(to_date) if to_date else getdate(nowdate())
    start = getdate(from_date) if from_date else add_months(end, -1)
    if start > end:
        frappe.throw("开始日期不能晚于结束日期")
    return str(start), str(end)


def _mobile_report_base(report, company, from_date, to_date):
    label, kind = MOBILE_REPORTS[report]
    return {
        "state": "ok",
        "report": report,
        "label": label,
        "kind": kind,
        "company": company,
        "from_date": from_date,
        "to_date": to_date,
        "rows": [],
        "summary": [],
        "row_count": 0,
        "page": 1,
        "page_length": MOBILE_REPORT_PAGE_LENGTH,
        "page_count": 1,
        "has_prev": False,
        "has_next": False,
    }


def _mobile_paginate(payload, rows, page=1, page_length=MOBILE_REPORT_PAGE_LENGTH):
    try:
        page = max(1, int(page or 1))
    except (TypeError, ValueError):
        page = 1
    try:
        page_length = max(1, min(int(page_length or MOBILE_REPORT_PAGE_LENGTH), MOBILE_REPORT_MAX_PAGE_LENGTH))
    except (TypeError, ValueError):
        page_length = MOBILE_REPORT_PAGE_LENGTH
    row_count = len(rows)
    page_count = max(1, (row_count + page_length - 1) // page_length)
    page = min(page, page_count)
    start = (page - 1) * page_length
    payload.update({
        "row_count": row_count,
        "page": page,
        "page_length": page_length,
        "page_count": page_count,
        "has_prev": page > 1,
        "has_next": page < page_count,
        "rows": rows[start:start + page_length],
    })
    return payload


def _mobile_business_report(report, company, from_date, to_date, metric, page, page_length):
    from solua_home.api.business_totals import METRICS, get_total

    metric = metric if metric in METRICS else ("delivered" if report == "Solua Delivery Summary" else "orders")
    result = get_total(
        metric=metric,
        period="custom",
        from_date=from_date,
        to_date=to_date,
        company=company,
    )
    payload = _mobile_report_base(report, company, from_date, to_date)
    payload.update({
        "state": result.get("state"),
        "currency": result.get("currency") or "MZN",
        "metric": metric,
        "metric_label": METRICS[metric],
        "unallocated_amount": result.get("unallocated_amount") if metric == "paid" else None,
        "metric_options": [] if report == "Solua Delivery Summary" else [
            {"value": key, "label": label}
            for key, label in METRICS.items()
        ],
    })
    items = result.get("items") or []
    rows = [{
        "name": row.get("name") or "",
        "doctype": row.get("doctype") or "",
        "customer": row.get("customer") or "",
        "date": str(row.get("date") or ""),
        "amount": flt(row.get("amount")),
        "currency": row.get("currency") or payload["currency"],
        "status": row.get("billing_state") or "",
    } for row in items]
    _mobile_paginate(payload, rows, page, page_length)
    payload["summary"] = [
        {"label": METRICS[metric], "value": flt(result.get("amount") or 0), "type": "money", "currency": payload["currency"]},
        *([{"label": "未分配收款", "value": flt(result.get("unallocated_amount") or 0), "type": "money", "currency": payload["currency"]}] if metric == "paid" else []),
        {"label": "明细行数", "value": len(items), "type": "number"},
    ]
    return payload


def _mobile_profitability_report(company, from_date, to_date, page, page_length):
    from solua_home.solua_wholesale.report.profitability_analysis.profitability_analysis import execute

    fiscal_year = frappe.get_all(
        "Fiscal Year",
        filters={"year_start_date": ["<=", to_date], "year_end_date": [">=", from_date]},
        fields=["name"],
        order_by="year_start_date desc",
        limit_page_length=1,
    )
    if not fiscal_year:
        frappe.throw("找不到覆盖所选日期的财务年度")
    _, data = execute(frappe._dict({
        "company": company,
        "based_on": "Cost Center",
        "fiscal_year": fiscal_year[0].name,
        "from_date": from_date,
        "to_date": to_date,
        "show_zero_values": 0,
    }))
    raw_rows = [dict(row) for row in data if row]
    total = next(
        (row for row in reversed(raw_rows) if str(row.get("account_name") or "").strip("'").casefold() in {"total", "总计", "合计"}),
        {},
    )
    if not total:
        roots = [row for row in raw_rows if int(row.get("indent") or 0) == 0]
        total = {field: sum(flt(row.get(field)) for row in roots) for field in ("income", "expense", "gross_profit_loss")}
    rows = [{
        "account_name": row.get("account_name") or row.get("account") or "",
        "indent": int(row.get("indent") or 0),
        "income": flt(row.get("income")),
        "expense": flt(row.get("expense")),
        "gross_profit_loss": flt(row.get("gross_profit_loss")),
        "currency": row.get("currency") or "MZN",
    } for row in raw_rows if row is not total]
    payload = _mobile_report_base("Profitability Analysis", company, from_date, to_date)
    currency = frappe.get_cached_value("Company", company, "default_currency") or "MZN"
    payload.update({
        "currency": currency,
        "summary": [
            {"label": "收入", "value": flt(total.get("income")), "type": "money", "currency": currency},
            {"label": "支出", "value": flt(total.get("expense")), "type": "money", "currency": currency},
            {"label": "毛利/亏损", "value": flt(total.get("gross_profit_loss")), "type": "money", "currency": currency},
        ],
    })
    return _mobile_paginate(payload, rows, page, page_length)


def _mobile_stock_report(company, warehouse, from_date, to_date, page, page_length):
    from solua_home.solua_wholesale.report.template_stock_tree.template_stock_tree import execute

    _, data = execute(frappe._dict({
        "company": company,
        "warehouse": warehouse,
        "exclude_legacy": 1,
    }))
    rows = [{
        "item_code": row.get("item_code") or "",
        "item_name": row.get("item_name") or "",
        "indent": int(row.get("indent") or 0),
        "actual_qty": flt(row.get("actual_qty")),
        "reserved_qty": flt(row.get("reserved_qty")),
        "available_qty": flt(row.get("available_qty")),
        "stock_uom": row.get("stock_uom") or "",
    } for row in data]
    payload = _mobile_report_base("Template Stock Tree", company, from_date, to_date)
    payload.update({
        "warehouse": warehouse or "全部有权限仓库",
        "summary": [
            {"label": "显示行数", "value": len(rows), "type": "number"},
            {"label": "仓库", "value": warehouse or "全部有权限仓库", "type": "text"},
        ],
    })
    return _mobile_paginate(payload, rows, page, page_length)


def _mobile_item_sales_report(company, from_date, to_date, item_group=None, item_code=None, customer=None,
                              page=1, page_length=MOBILE_REPORT_PAGE_LENGTH):
    from erpnext.selling.report.item_wise_sales_history.item_wise_sales_history import execute

    report_result = execute(frappe._dict({
        "company": company,
        "from_date": from_date,
        "to_date": to_date,
        "item_group": str(item_group or "").strip(),
        "item_code": str(item_code or "").strip(),
        "customer": str(customer or "").strip(),
    }))
    data = report_result[1]
    grouped = {}
    for row in data:
        item_code_value = row.get("item_code") or ""
        key = item_code_value or row.get("item_name") or ""
        item = grouped.setdefault(key, {
            "item_code": item_code_value,
            "item_name": row.get("item_name") or "",
            "customers": [],
            "sales_orders": [],
            "quantity": 0,
            "uom": row.get("uom") or "",
            "amount": 0,
            "delivered_quantity": 0,
            "billed_amount": 0,
            "currency": row.get("currency") or "MZN",
        })
        customer_name = row.get("customer_name") or row.get("customer") or ""
        if customer_name and customer_name not in item["customers"]:
            item["customers"].append(customer_name)
        sales_order = row.get("sales_order") or ""
        if sales_order and sales_order not in item["sales_orders"]:
            item["sales_orders"].append(sales_order)
        item["quantity"] += flt(row.get("quantity"))
        item["amount"] += flt(row.get("amount"))
        item["delivered_quantity"] += flt(row.get("delivered_quantity"))
        item["billed_amount"] += flt(row.get("billed_amount"))
    rows = []
    for item in grouped.values():
        customers = item.pop("customers")
        item["customer"] = ", ".join(customers[:2]) + (" …" if len(customers) > 2 else "")
        item["sales_orders"] = item.pop("sales_orders")
        item["sales_order_count"] = len(item["sales_orders"])
        rows.append(item)
    rows.sort(key=lambda row: (-row["quantity"], -row["amount"], row["item_code"]))
    currency = frappe.get_cached_value("Company", company, "default_currency") or "MZN"
    payload = _mobile_report_base("Item-wise Sales History", company, from_date, to_date)
    payload.update({
        "currency": currency,
        "summary": [
            {"label": "销售数量", "value": sum(row["quantity"] for row in rows), "type": "number"},
            {"label": "销售金额", "value": sum(row["amount"] for row in rows), "type": "money", "currency": currency},
            {"label": "物料数", "value": len(rows), "type": "number"},
        ],
    })
    return _mobile_paginate(payload, rows, page, page_length)


@frappe.whitelist()
@frappe.read_only()
def get_mobile_report_detail(report, from_date=None, to_date=None, company=None, warehouse=None, metric=None,
                             item_group=None, item_code=None, customer=None, page=1,
                             page_length=MOBILE_REPORT_PAGE_LENGTH):
    """Return a compact, mobile-only rendering model for the five wholesale reports."""
    _require_admin()
    report = str(report or "").strip()
    if report not in MOBILE_REPORTS:
        frappe.throw("不支持的移动报表")
    company_doc = _resolve_company(str(company or "").strip() or None)
    if not company_doc:
        frappe.throw("没有可访问的公司")
    start, end = _mobile_report_dates(from_date, to_date)
    defaults = _defaults()
    warehouse = str(warehouse or "").strip() or defaults["warehouse"]
    if report == "Profitability Analysis":
        return _mobile_profitability_report(company_doc.name, start, end, page, page_length)
    if report == "Template Stock Tree":
        return _mobile_stock_report(company_doc.name, warehouse, start, end, page, page_length)
    if report == "Solua Delivery Summary":
        return _mobile_business_report(report, company_doc.name, start, end, "delivered", page, page_length)
    if report == "Solua Business Totals":
        return _mobile_business_report(report, company_doc.name, start, end, metric, page, page_length)
    return _mobile_item_sales_report(company_doc.name, start, end, item_group, item_code, customer, page, page_length)


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
@frappe.read_only()
def list_customers(query=None, limit=30):
    """List active customers and their primary contact/address for the mobile customer center."""
    _require_admin()
    try:
        limit = max(1, min(int(limit or 30), 50))
    except (TypeError, ValueError):
        limit = 30
    query = str(query or "").strip()
    meta = frappe.get_meta("Customer")
    searchable = [field for field in ("name", "customer_name", "mobile_no", "phone", "tax_id") if meta.has_field(field)]
    fields = [
        field for field in (
            "name", "customer_name", "customer_type", "customer_group", "territory", "tax_id",
            "mobile_no", "phone", "customer_primary_address", "customer_primary_contact", "modified",
        ) if meta.has_field(field) or field == "name"
    ]
    kwargs = {"filters": {"disabled": 0}, "fields": fields, "limit_page_length": limit, "order_by": "modified desc"}
    if query and searchable:
        like = f"%{query}%"
        kwargs["or_filters"] = [[field, "like", like] for field in searchable]
    rows = frappe.get_list("Customer", **kwargs)
    result = []
    for row in rows:
        address = {}
        if row.get("customer_primary_address"):
            address = frappe.db.get_value(
                "Address", row.customer_primary_address, ["address_line1", "city", "phone"], as_dict=True
            ) or {}
        contact = {}
        if row.get("customer_primary_contact"):
            contact = frappe.db.get_value(
                "Contact", row.customer_primary_contact, ["mobile_no", "phone"], as_dict=True
            ) or {}
        result.append({
            "name": row.name,
            "customer_name": row.get("customer_name") or row.name,
            "customer_type": row.get("customer_type") or "",
            "customer_group": row.get("customer_group") or "",
            "territory": row.get("territory") or "",
            "tax_id": row.get("tax_id") or "",
            "phone": row.get("phone") or row.get("mobile_no") or contact.get("phone") or contact.get("mobile_no") or address.get("phone") or "",
            "address": address.get("address_line1") or "",
            "city": address.get("city") or "",
        })
    return result


@frappe.whitelist()
def get_customer_form_options():
    _require_admin()
    meta = frappe.get_meta("Customer")
    type_field = meta.get_field("customer_type")
    types = [value for value in (type_field.options or "").splitlines() if value]
    observed = frappe.get_all("Customer", fields=["customer_type"], limit_page_length=200)
    observed_types = {row.customer_type for row in observed if row.customer_type}
    types = [value for value in types if value in observed_types] or ["Company"]
    groups = frappe.get_all(
        "Customer Group", filters={"is_group": 0}, pluck="name", order_by="name asc", limit_page_length=100
    )
    territories = frappe.get_all(
        "Territory", filters={"is_group": 0}, pluck="name", order_by="name asc", limit_page_length=100
    )
    existing = frappe.get_all(
        "Customer", fields=["customer_group", "territory"], limit_page_length=200, order_by="modified desc"
    )
    default_group = next((row.customer_group for row in existing if row.customer_group in groups), groups[0] if groups else "")
    default_territory = next(
        (row.territory for row in existing if row.territory in territories), territories[0] if territories else ""
    )
    return {
        "customer_types": types,
        "customer_groups": groups,
        "territories": territories,
        "defaults": {"customer_type": types[0], "customer_group": default_group, "territory": default_territory},
    }


@frappe.whitelist()
def create_customer(
    customer_name, customer_type="Company", customer_group=None, territory=None, tax_id=None,
    address=None, city=None, phone=None,
):
    _require_admin()
    customer_name = str(customer_name or "").strip()
    customer_type = str(customer_type or "Company").strip()
    customer_group = str(customer_group or "").strip()
    territory = str(territory or "").strip()
    tax_id = str(tax_id or "").strip()
    address = str(address or "").strip()
    city = str(city or "").strip()
    phone = str(phone or "").strip()
    if not customer_name:
        frappe.throw(_("请输入客户名称"))
    if any(len(value) > 140 for value in (customer_name, tax_id, address, city, phone)):
        frappe.throw(_("客户名称、税号、地址、城市或电话过长"))
    if not customer_group or not territory:
        frappe.throw(_("请选择客户分组和地区"))
    if address and not city:
        frappe.throw(_("填写地址时请同时填写城市"))
    if city and not address:
        frappe.throw(_("填写城市时请同时填写地址"))
    if frappe.db.exists("Customer", {"customer_name": customer_name, "disabled": 0}):
        frappe.throw(_("客户已存在：{0}").format(customer_name))
    types = [value for value in (frappe.get_meta("Customer").get_field("customer_type").options or "").splitlines() if value]
    if customer_type not in types:
        frappe.throw(_("客户类型无效"))
    for doctype, value, label in (("Customer Group", customer_group, "客户分组"), ("Territory", territory, "地区")):
        if value and not frappe.db.exists(doctype, {"name": value, "is_group": 0}):
            frappe.throw(_("{0}无效").format(label))
    doc = frappe.new_doc("Customer")
    doc.customer_name = customer_name
    doc.customer_type = customer_type
    if customer_group:
        doc.customer_group = customer_group
    if territory:
        doc.territory = territory
    if tax_id:
        doc.tax_id = tax_id
    if frappe.get_meta("Customer").has_field("custom_status"):
        doc.custom_status = "正常"
    doc.insert()
    if address:
        address_doc = frappe.new_doc("Address")
        address_doc.address_title = customer_name
        address_doc.address_type = "Shop"
        address_doc.address_line1 = address
        address_doc.city = city
        address_doc.is_primary_address = 1
        address_doc.append("links", {"link_doctype": "Customer", "link_name": doc.name})
        address_doc.insert()
        doc.customer_primary_address = address_doc.name
    if phone:
        contact = frappe.new_doc("Contact")
        contact.first_name = customer_name
        contact.is_primary_contact = 1
        contact.append("links", {"link_doctype": "Customer", "link_name": doc.name})
        contact.append("phone_nos", {"phone": phone, "is_primary_mobile_no": 1})
        contact.insert()
        doc.customer_primary_contact = contact.name
    if address or phone:
        doc.save()
    return {"state": "ok", "name": doc.name, "customer_name": doc.customer_name}


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


def _customer_price_list(customer=None):
    """Use the customer's approved wholesale list without exposing tier names."""
    if not customer:
        return "Wholesale Selling"
    customer = _customer(customer)
    level_three_customers = {"AN LAN SUPERMERCADO, LDA", "HOME STORE, LDA"}
    return "Wholesale Selling 3" if customer.name in level_three_customers else "Wholesale Selling"


def _order_context(customer, warehouse=None):
    defaults = _defaults()
    if not defaults["company"]:
        frappe.throw(_("没有可访问的公司"))
    customer_doc = _customer(customer)
    warehouse = str(warehouse or "").strip() or defaults["warehouse"]
    if warehouse and not frappe.db.exists(
        "Warehouse", {"name": warehouse, "company": defaults["company"], "is_group": 0}
    ):
        frappe.throw(_("仓库无效：{0}").format(warehouse))
    return {
        "company": defaults["company"],
        "customer": customer_doc.name,
        "set_warehouse": warehouse,
        "price_list": _customer_price_list(customer_doc.name),
        "selling_price_list": _customer_price_list(customer_doc.name),
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
        normalized.append({
            "item_code": item_code,
            "qty": qty,
            "warehouse": str(row.get("warehouse") or warehouse).strip(),
            "notes": str(row.get("notes") or "").strip(),
        })
    return normalized


def _apply_order_data(doc, context, address, resolved_rows, notes=""):
    doc.customer = context["customer"]
    doc.company = context["company"]
    doc.transaction_date = context["transaction_date"]
    doc.selling_price_list = context["selling_price_list"]
    doc.set_warehouse = context["set_warehouse"]
    for field, value in (("customer_address", address), ("shipping_address_name", address)):
        if frappe.get_meta("Sales Order").has_field(field):
            setattr(doc, field, value or "")
    if notes is not None and frappe.get_meta("Sales Order").has_field("custom_additional_notes"):
        doc.custom_additional_notes = str(notes or "").strip()
    doc.set("items", [])
    item_meta = frappe.get_meta("Sales Order Item")
    for row in resolved_rows:
        item = doc.append("items", {})
        for field in ("item_code", "item_name", "description", "uom", "stock_uom", "conversion_factor", "stock_qty", "rate", "price_list_rate", "warehouse", "qty"):
            if item_meta.has_field(field) and field in row:
                setattr(item, field, row[field])
        for note_field in ("additional_notes", "pos_additional_notes"):
            if item_meta.has_field(note_field):
                setattr(item, note_field, row.get("notes") or "")
                break
        if item_meta.has_field("delivery_date"):
            item.delivery_date = context["transaction_date"]


@frappe.whitelist()
def save_sales_order(customer, rows, warehouse=None, address=None, name=None, submit=0, notes=None):
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
    _apply_order_data(doc, context, address, resolved["rows"], notes)
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


def _can_create(doctype):
    return bool(frappe.has_permission(doctype, ptype="create"))


def _document_summaries(doctype, names, limit_page_length=100):
    names = list(dict.fromkeys(name for name in names if name))
    if not names:
        return []
    return frappe.get_all(
        doctype,
        filters={"name": ["in", names], "docstatus": ["<", 2]},
        fields=["name", "docstatus", "status", "posting_date", "grand_total", "currency", "modified"],
        order_by="modified desc",
        limit_page_length=max(limit_page_length, len(names)),
    )


def _sales_order_relations_batch(names, docstatus_by_name=None):
    names = list(dict.fromkeys(name for name in names if name))
    docstatus_by_name = docstatus_by_name or {}
    empty = {
        "delivery_notes": [],
        "sales_invoices": [],
        "pick_lists": [],
        "can_create_delivery": False,
        "can_create_pick_list": False,
    }
    result = {name: dict(empty) for name in names}
    if not names:
        return result

    delivery_names = frappe.get_all(
        "Delivery Note Item",
        filters={"against_sales_order": ["in", names]},
        fields=["parent", "against_sales_order"],
        limit_page_length=0,
    )
    delivery_names_by_order = {}
    all_delivery_names = []
    for row in delivery_names:
        if row.parent not in all_delivery_names:
            all_delivery_names.append(row.parent)
        delivery_names_by_order.setdefault(row.against_sales_order, [])
        if row.parent not in delivery_names_by_order[row.against_sales_order]:
            delivery_names_by_order[row.against_sales_order].append(row.parent)
    deliveries = _document_summaries("Delivery Note", all_delivery_names)
    deliveries_by_name = {row.name: row for row in deliveries}
    delivery_names = list(deliveries_by_name)
    invoice_rows = frappe.get_all(
        "Sales Invoice Item",
        filters={"delivery_note": ["in", delivery_names]},
        fields=["parent", "delivery_note"],
        limit_page_length=0,
    ) if delivery_names else []
    direct_invoice_rows = frappe.get_all(
        "Sales Invoice Item",
        filters={"sales_order": ["in", names]},
        fields=["parent", "sales_order"],
        limit_page_length=0,
    )
    invoice_names = list(dict.fromkeys(
        [row.parent for row in direct_invoice_rows]
        + [row.parent for row in invoice_rows]
    ))
    invoices = _document_summaries("Sales Invoice", invoice_names)
    pick_item_rows = frappe.get_all(
        "Pick List Item",
        filters={"sales_order": ["in", names], "parenttype": "Pick List"},
        fields=["parent", "sales_order"],
        limit_page_length=0,
    )
    pick_list_names = list(dict.fromkeys(row.parent for row in pick_item_rows if row.parent))
    pick_lists = frappe.get_all(
        "Pick List",
        filters={"name": ["in", pick_list_names], "docstatus": ["<", 2]},
        fields=["name", "docstatus", "status", "modified", "creation"],
        order_by="modified desc",
        limit_page_length=max(100, len(pick_list_names)),
    ) if pick_list_names else []
    for pick_list in pick_lists:
        pick_list["date"] = str(pick_list.modified or pick_list.creation or "")
    invoices_by_delivery = {}
    for row in invoice_rows:
        invoices_by_delivery.setdefault(row.delivery_note, set()).add(row.parent)
    invoices_by_order = {}
    for row in direct_invoice_rows:
        invoices_by_order.setdefault(row.sales_order, set()).add(row.parent)
    pick_lists_by_order = {}
    for row in pick_item_rows:
        pick_lists_by_order.setdefault(row.sales_order, set()).add(row.parent)
    can_create_delivery = _can_create("Delivery Note")
    can_create_invoice = _can_create("Sales Invoice")
    can_create_pick_list = _can_create("Pick List")
    for name in names:
        order_deliveries = [
            deliveries_by_name[delivery_name]
            for delivery_name in delivery_names_by_order.get(name, [])
            if delivery_name in deliveries_by_name
        ]
        for delivery in order_deliveries:
            delivery["invoices"] = [
                invoice for invoice in invoices
                if invoice.name in invoices_by_delivery.get(delivery.name, set())
            ]
            delivery["can_create_invoice"] = bool(
                delivery.docstatus == 1
                and delivery.status not in ("Completed", "Closed")
                and can_create_invoice
            )
        order_invoices = [
            invoice for invoice in invoices
            if invoice.name in invoices_by_order.get(name, set())
            or any(invoice.name in invoices_by_delivery.get(delivery.name, set()) for delivery in order_deliveries)
        ]
        order_pick_lists = [
            pick_list for pick_list in pick_lists
            if pick_list.name in pick_lists_by_order.get(name, set())
        ]
        result[name] = {
            "delivery_notes": order_deliveries,
            "sales_invoices": order_invoices,
            "pick_lists": order_pick_lists,
            "can_create_delivery": bool(docstatus_by_name.get(name) == 1 and can_create_delivery),
            "can_create_pick_list": bool(docstatus_by_name.get(name) == 1 and can_create_pick_list),
        }
    return result


def _sales_order_relations(name, docstatus):
    return _sales_order_relations_batch([name], {name: docstatus}).get(name, {})


def _document_summary(doc):
    date = doc.get("posting_date") or doc.get("transaction_date") or ""
    doctype = doc.doctype
    route = {"Sales Order": "sales-order", "Delivery Note": "delivery-note", "Sales Invoice": "sales-invoice"}.get(doctype, "")
    return {
        "doctype": doctype,
        "name": doc.name,
        "docstatus": doc.docstatus,
        "status": doc.get("status") or "",
        "date": str(date),
        "grand_total": doc.get("grand_total") or 0,
        "currency": doc.get("currency") or "MZN",
        "url": f"/app/{route}/{doc.name}" if route else "",
    }


@frappe.whitelist()
def create_delivery_note(sales_order):
    _require_admin()
    if not _can_create("Delivery Note"):
        frappe.throw(_("没有创建交货单的权限"), frappe.PermissionError)
    sales_order = frappe.get_doc("Sales Order", str(sales_order or "").strip())
    sales_order.check_permission("read")
    if sales_order.docstatus != 1:
        frappe.throw(_("只有已提交的销售订单可以开交货单"))
    from solua_home.api.stock import get_existing_draft_delivery_note

    existing = get_existing_draft_delivery_note(sales_order.name)
    if existing:
        return {"state": "existing", **_document_summary(existing)}
    from erpnext.selling.doctype.sales_order.sales_order import make_delivery_note

    delivery = make_delivery_note(sales_order.name)
    if not delivery or not delivery.items:
        frappe.throw(_("该销售订单没有可交付的剩余数量"))
    delivery.insert()
    return {"state": "draft", **_document_summary(delivery)}


@frappe.whitelist()
def create_sales_invoice(delivery_note):
    _require_admin()
    if not _can_create("Sales Invoice"):
        frappe.throw(_("没有创建销售发票的权限"), frappe.PermissionError)
    from solua_home.api.unbilled import prepare_invoice

    result = prepare_invoice(str(delivery_note or "").strip())
    if result.get("draft_invoices"):
        invoice = frappe.get_doc("Sales Invoice", result["draft_invoices"][0])
        return {"state": "existing", **_document_summary(invoice)}
    invoice_data = result.get("invoice")
    if not invoice_data:
        frappe.throw(_("没有可开票的数量"))
    invoice = frappe.get_doc(invoice_data)
    invoice.insert()
    return {"state": "draft", **_document_summary(invoice)}


@frappe.whitelist()
def create_pick_list(sales_order):
    """Create or reuse a draft Pick List for a submitted Sales Order."""
    _require_admin()
    if not _can_create("Pick List"):
        frappe.throw(_("没有创建拣货单的权限"), frappe.PermissionError)
    sales_order = frappe.get_doc("Sales Order", str(sales_order or "").strip())
    sales_order.check_permission("read")
    if sales_order.docstatus != 1:
        frappe.throw(_("只有已提交的销售订单可以生成拣货单"))

    from solua_home.api.stock import get_existing_draft_pick_list

    existing = get_existing_draft_pick_list(sales_order.name)
    if existing:
        return {"state": "existing", "doctype": "Pick List", "name": existing.name, "docstatus": 0}

    from solua_home.api.stock import create_pick_list as map_pick_list

    pick_list = map_pick_list(sales_order.name)
    if not pick_list or not pick_list.locations:
        frappe.throw(_("该销售订单没有可拣货的剩余数量"))
    pick_list.insert()
    return {"state": "draft", "doctype": "Pick List", "name": pick_list.name, "docstatus": pick_list.docstatus}


@frappe.whitelist()
def list_sales_orders(query=None, limit=20, page=1, sort="date_desc", item_query=None):
    """List recent non-cancelled orders for the protected mobile order tab."""
    _require_admin()
    try:
        limit = max(1, min(int(limit or 20), 50))
    except (TypeError, ValueError):
        limit = 20
    try:
        page = max(1, int(page or 1))
    except (TypeError, ValueError):
        page = 1
    query = str(query or "").strip()
    filters = {"docstatus": ["<", 2]}
    or_filters = None
    if query:
        like = f"%{query}%"
        or_filters = [[field, "like", like] for field in ("name", "customer", "customer_name")]
    item_query = str(item_query or "").strip()
    if item_query:
        matches = frappe.db.sql("""
            SELECT DISTINCT soi.parent
            FROM `tabSales Order Item` soi
            LEFT JOIN `tabItem` item ON item.name = soi.item_code
            WHERE soi.parenttype = 'Sales Order'
                AND (soi.item_code LIKE %(query)s OR soi.item_name LIKE %(query)s
                    OR item.variant_of LIKE %(query)s)
        """, {"query": f"%{item_query}%"}, pluck=True)
        filters["name"] = ["in", matches]
    sort = sort if sort in ("date_desc", "name_desc", "amount_desc") else "date_desc"
    order_by = {
        "date_desc": "transaction_date desc, creation desc, name desc",
        "name_desc": "name desc",
        "amount_desc": "grand_total desc, transaction_date desc, name desc",
    }[sort]
    count = frappe.get_all("Sales Order", filters=filters, or_filters=or_filters,
                           fields=[{"COUNT": "name", "as": "total"}])[0].total
    page_count = max(1, (count + limit - 1) // limit)
    page = min(page, page_count)
    rows = frappe.get_all(
        "Sales Order",
        filters=filters,
        or_filters=or_filters,
        fields=[
            "name", "customer", "customer_name", "transaction_date", "status", "docstatus",
            "grand_total", "currency", "modified",
        ],
        order_by=order_by,
        limit_start=(page - 1) * limit,
        limit_page_length=limit,
    )
    fulfillment = {}
    if rows:
        from solua_home.api.order_status import get_order_statuses
        fulfillment = get_order_statuses([row.name for row in rows])
    names = [row.name for row in rows]
    items_by_order = {}
    if names:
        for item in frappe.get_all(
            "Sales Order Item",
            filters={"parent": ["in", names], "parenttype": "Sales Order"},
            fields=["parent", "item_code", "item_name", "qty", "uom", "stock_uom", "conversion_factor", "stock_qty", "rate", "amount"],
            order_by="parent asc, idx asc",
            limit_page_length=0,
        ):
            items_by_order.setdefault(item.parent, []).append(item)
    relations = _sales_order_relations_batch(names, {row.name: row.docstatus for row in rows})
    for row in rows:
        row["fulfillment"] = fulfillment[row.name]
        row["items"] = items_by_order.get(row.name, [])
        row.update(relations.get(row.name, {}))
    return {"rows": rows, "row_count": count, "page": page, "page_count": page_count,
            "page_length": limit, "has_prev": page > 1, "has_next": page < page_count,
            "sort": sort}


def _decorate_prices(result):
    for row in result.get("variants") or []:
        row.pop("wholesale_rate", None)
        row.pop("standard_selling_rate", None)
    return result


@frappe.whitelist()
@frappe.read_only()
def search_item_suggestions(query, limit=8):
    """Return lightweight item candidates; full stock/price lookup stays on submit."""
    _require_admin()
    query = str(query or "").strip()
    if len(query) < 2:
        return {"items": []}
    try:
        limit = max(1, min(int(limit or 8), 20))
    except (TypeError, ValueError):
        limit = 8

    fields = ["name", "item_code", "item_name", "variant_of", "has_variants"]
    meta = frappe.get_meta("Item")
    for field in ("custom_order_code", "custom_label_barcode"):
        if meta.has_field(field):
            fields.append(field)
    exact_item_or_filters = [
        [field, "=", query]
        for field in ("name", "item_code", "custom_order_code", "custom_label_barcode")
        if field in fields
    ]
    rows = frappe.get_all(
        "Item",
        filters={"disabled": 0},
        or_filters=exact_item_or_filters,
        fields=fields,
        order_by="has_variants desc, name asc",
        limit_page_length=limit,
    ) if exact_item_or_filters else []
    exact_barcode_parents = frappe.get_all(
        "Item Barcode",
        filters={"barcode": query},
        fields=["parent"],
        limit_page_length=limit,
    )
    parent_names = [row.parent for row in exact_barcode_parents if row.parent]
    if parent_names:
        rows.extend(frappe.get_all(
            "Item",
            filters={"name": ["in", parent_names], "disabled": 0},
            fields=fields,
            limit_page_length=limit,
        ))
    if not rows:
        like = f"%{query}%"
        rows = frappe.get_all(
            "Item",
            filters={"disabled": 0},
            or_filters=[
                [field, "like", like]
                for field in ("name", "item_code", "item_name", "custom_order_code", "custom_label_barcode")
                if field in fields
            ],
            fields=fields,
            order_by="has_variants desc, name asc",
            limit_page_length=limit,
        )
    unique = {}
    for row in rows:
        unique[row.name] = {
            "name": row.name,
            "item_code": row.item_code or row.name,
            "item_name": row.item_name or row.name,
            "variant_of": row.variant_of or "",
            "has_variants": bool(row.has_variants),
        }
    return {"items": list(unique.values())[:limit]}


@frappe.whitelist()
def lookup(barcode, warehouse=None, customer=None):
    _require_admin()
    defaults = _defaults()
    if not defaults["company"]:
        return {"state": "no_permission", "templates": [], "variants": []}

    price_list = _customer_price_list(customer) if str(customer or "").strip() else "Wholesale Selling"
    context = {
        "company": defaults["company"],
        "set_warehouse": str(warehouse or "").strip() or defaults["warehouse"],
        "price_list": price_list,
        "selling_price_list": price_list,
    }
    query = str(barcode or "").strip()
    if not query:
        return {"state": "no_data", "templates": [], "variants": []}

    result = get_sales_order_color_variants(barcode=query, context=context)
    if result.get("variants"):
        return _decorate_prices(result)

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
        }
    )
