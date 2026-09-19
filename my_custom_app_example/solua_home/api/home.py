"""Permission-aware data and navigation for the Solua Home Desk page."""

import re

import frappe
from frappe import _
from frappe.utils import flt, nowdate

DEFAULT_COMPANY = "Solua Home, Lda"
DEFAULT_WAREHOUSE = "Finished Goods - SH"
SERVICE_ACCOUNT_MARKERS = ("sync", "api", "integration", "service", "bot")


def _has_field(doctype, fieldname):
    return frappe.get_meta(doctype).has_field(fieldname)


def _can_read(doctype):
    if frappe.session.user == "Guest":
        return False
    return bool(frappe.db.exists("DocType", doctype) and frappe.has_permission(doctype, ptype="read"))


def _can_create(doctype):
    return bool(frappe.db.exists("DocType", doctype) and frappe.has_permission(doctype, ptype="create"))


def _list(doctype, filters=None, fields=None, *, limit=0, order_by=None, or_filters=None):
    if doctype in {"Item Barcode", "Item Variant Attribute", "Item Reorder"}:
        # These child tables have no independent role permissions. Restrict every
        # query to Item parents visible to this user, then read only those rows.
        parents = [row.name for row in _list("Item", fields=["name"], limit=0)]
        if not parents:
            return []
        child_filters = dict(filters or {})
        requested = child_filters.pop("parent", None)
        if isinstance(requested, str):
            parents = [name for name in parents if name == requested]
        elif isinstance(requested, (list, tuple)) and requested[0] == "in":
            parents = [name for name in parents if name in requested[1]]
        if not parents:
            return []
        return frappe.get_all(doctype, filters={**child_filters, "parenttype": "Item", "parent": ["in", parents]},
                              fields=fields or ["name"], limit_page_length=limit, order_by=order_by)
    if not _can_read(doctype):
        return []
    kwargs = {"filters": filters or {}, "fields": fields or ["name"], "limit_page_length": limit}
    if order_by:
        kwargs["order_by"] = order_by
    if or_filters:
        kwargs["or_filters"] = or_filters
    return frappe.get_list(doctype, **kwargs)


def _resolve_company(requested=None):
    if requested:
        candidates = [requested.strip()]
    else:
        candidates = [DEFAULT_COMPANY, frappe.defaults.get_user_default("Company")]
    for name in dict.fromkeys(filter(None, candidates)):
        rows = _list("Company", {"name": name}, ["name", "default_currency"], limit=1)
        if rows:
            return rows[0]
    if requested:
        return None
    return next(iter(_list("Company", fields=["name", "default_currency"], order_by="name asc", limit=1)), None)


def _resolve_warehouse(company, requested=None):
    if not company:
        return None
    candidates = [requested.strip()] if requested else [DEFAULT_WAREHOUSE, frappe.defaults.get_user_default("Warehouse")]
    filters = {"company": company.name, "is_group": 0}
    for name in dict.fromkeys(filter(None, candidates)):
        rows = _list("Warehouse", {**filters, "name": name}, ["name"], limit=1)
        if rows:
            return rows[0].name
    if requested:
        return None
    rows = _list("Warehouse", filters, ["name"], order_by="name asc", limit=1)
    return rows[0].name if rows else None


def _invoice_specs(company, date=None):
    base = {"company": company, "docstatus": 1}
    if date:
        base["posting_date"] = date
    sales_filters = dict(base)
    if _has_field("Sales Invoice", "custom_is_topup"):
        sales_filters["custom_is_topup"] = 0
    specs = [("Sales Invoice", sales_filters)]
    # A POS Invoice linked to a consolidated Sales Invoice is already represented there.
    if _can_read("POS Invoice"):
        specs.append(("POS Invoice", {**base, "consolidated_invoice": ["is", "not set"]}))
    return specs


def _aggregate(specs, value_field, extra_filters=None):
    total = 0.0
    count = 0
    for doctype, base_filters in specs:
        if not _has_field(doctype, value_field):
            continue
        row = next(
            iter(_list(
                doctype,
                {**base_filters, **(extra_filters or {})},
                [{"COUNT": "name", "as": "count"}, {"SUM": value_field, "as": "total"}],
                limit=1,
            )),
            None,
        )
        if row:
            count += int(row.get("count") or 0)
            total += flt(row.get("total"))
    return {"count": count, "total": total}


def _count(doctype, filters):
    if not _can_read(doctype):
        return 0
    row = next(iter(_list(doctype, filters, [{"COUNT": "name", "as": "count"}], limit=1)), None)
    return int(row.get("count") or 0) if row else 0


def _detail_rows(specs, extra_filters, fields, order_by, limit=5):
    rows = []
    for doctype, base_filters in specs:
        for row in _list(
            doctype,
            {**base_filters, **extra_filters},
            ["name", *fields],
            limit=limit,
            order_by=order_by,
        ):
            row["doctype"] = doctype
            rows.append(row)
    key_field = order_by.split(",")[0].strip().split()[0]
    return sorted(rows, key=lambda row: (row.get(key_field) or "", row.name))[:limit]


def _low_stock(warehouse):
    if not warehouse or not _can_read("Item") or not _can_read("Bin"):
        return {"state": "no_permission", "count": None, "items": []}
    reorder_rows = _list(
        "Item Reorder",
        {"warehouse": warehouse, "warehouse_reorder_level": [">", 0]},
        ["parent", "warehouse_reorder_level"],
        limit=0,
    )
    if not reorder_rows:
        return {"state": "no_data", "count": 0, "items": []}
    item_codes = list(dict.fromkeys(row.parent for row in reorder_rows))
    items = _list(
        "Item",
        {"name": ["in", item_codes], "disabled": 0, "is_stock_item": 1, "has_variants": 0},
        ["name", "item_name", "stock_uom"],
        limit=0,
    )
    allowed_codes = {row.name for row in items}
    if not allowed_codes:
        return {"state": "no_data", "count": 0, "items": []}
    bins = _list(
        "Bin",
        {"item_code": ["in", list(allowed_codes)], "warehouse": warehouse},
        ["item_code", "actual_qty"],
        limit=0,
    )
    actual = {row.item_code: flt(row.actual_qty) for row in bins}
    item_map = {row.name: row for row in items}
    alerts = []
    for row in reorder_rows:
        if row.parent not in allowed_codes:
            continue
        # A missing permitted Bin can mean row-level denial, not zero stock.
        if row.parent not in actual:
            continue
        qty = actual[row.parent]
        if qty < flt(row.warehouse_reorder_level):
            item = item_map[row.parent]
            alerts.append({
                "name": item.name,
                "item_name": item.item_name,
                "actual_qty": qty,
                "reorder_level": flt(row.warehouse_reorder_level),
                "stock_uom": item.stock_uom,
            })
    alerts.sort(key=lambda row: (row["actual_qty"] - row["reorder_level"], row["name"]))
    incomplete = bool(allowed_codes - actual.keys())
    return {"state": "incomplete" if incomplete else ("ok" if alerts else "no_data"),
            "count": None if incomplete else len(alerts), "items": alerts[:5]}


def _item_data_status():
    if not _can_read("Item"):
        return {"state": "no_permission", "missing_image": None, "missing_color_code": None}
    fields = ["name", "image", "variant_of", "disabled"]
    if _has_field("Item", "custom_color_code"):
        fields.append("custom_color_code")
    items = _list("Item", {"disabled": 0}, fields, limit=0)
    color_items = {row.parent for row in _list("Item Variant Attribute", {"attribute": "Cor"}, ["parent"], limit=0)}
    return {
        "state": "ok" if items else "no_data",
        "missing_image": sum(1 for row in items if not row.get("image")),
        "missing_color_code": sum(1 for row in items if row.name in color_items and not row.get("custom_color_code")),
        "item_count": len(items),
    }


def _permissions():
    return {
        "new_sales_invoice": _can_create("Sales Invoice"),
        "new_sales_order": _can_create("Sales Order"),
        "new_delivery_note": _can_create("Delivery Note"),
        "new_purchase_receipt": _can_create("Purchase Receipt"),
        "new_item": _can_create("Item"),
        "new_stock_entry": _can_create("Stock Entry"),
        "read_item": _can_read("Item"),
        "read_stock_reconciliation": _can_read("Stock Reconciliation"),
        "new_stock_reconciliation": _can_create("Stock Reconciliation"),
        "read_customer": _can_read("Customer"),
        "read_supplier": _can_read("Supplier"),
        "read_item_price": _can_read("Item Price"),
        "read_print_settings": _can_read("Print Settings"),
        "read_print_format": _can_read("Print Format"),
        "read_pricing_rule": _can_read("Pricing Rule"),
        "new_pricing_rule": _can_create("Pricing Rule"),
        "read_pos_closing": _can_read("POS Closing Entry"),
    }


def _stock_entry_types():
    """Return the actual Material Issue type names used by the homepage."""
    if not _can_read("Stock Entry Type"):
        return {}
    rows = _list("Stock Entry Type", {"purpose": "Material Issue"}, ["name"], limit=0)
    names = {row.name for row in rows}

    def pick(preferred, aliases):
        return next((name for name in aliases if name in names), preferred)

    return {
        "issue": pick("Material Issue", ("Material Issue",)),
        "consumption": pick("领用", ("领用", "Consumption", "Issue for Use")),
        "wastage": pick("损耗", ("损耗", "Wastage", "Waste", "Material Loss")),
    }


@frappe.whitelist()
@frappe.read_only()
def get_dashboard_data(company=None, warehouse=None):
    """Return homepage data using permission-aware list queries."""
    if frappe.session.user == "Guest":
        return {"state": "no_permission"}
    company_doc = _resolve_company(company)
    if not company_doc:
        return {"state": "no_permission", "message": _("没有可访问的公司数据")}
    resolved_warehouse = _resolve_warehouse(company_doc, warehouse)
    today = nowdate()
    specs = _invoice_specs(company_doc.name, today)
    all_invoice_specs = _invoice_specs(company_doc.name)
    sales = _aggregate(specs, "base_grand_total")
    sale_count = _aggregate(specs, "base_grand_total", {"is_return": 0})["count"]
    returns = _aggregate(specs, "base_grand_total", {"is_return": 1})["count"]
    # outstanding_amount is in invoice currency; ERPNext has no
    # base_outstanding_amount column. Convert each accessible invoice once.
    outstanding_rows = []
    for doctype, filters in all_invoice_specs:
        for row in _list(doctype, {**filters, "outstanding_amount": [">", 0]},
                         ["name", "customer", "due_date", "outstanding_amount", "conversion_rate"], limit=0):
            row["doctype"] = doctype
            row["base_outstanding_amount"] = flt(row.outstanding_amount) * flt(row.conversion_rate or 1)
            outstanding_rows.append(row)
    outstanding = {"count": len(outstanding_rows), "total": sum(row.base_outstanding_amount for row in outstanding_rows)}
    invoice_read = any(_can_read(dt) for dt, _ in all_invoice_specs)
    overdue_rows = sorted([row for row in outstanding_rows if row.due_date and str(row.due_date) < today],
                          key=lambda row: (str(row.due_date), row.name))[:5]
    order_filters = {
        "company": company_doc.name,
        "docstatus": 1,
        "per_delivered": ["<", 100],
        "status": ["not in", ["Closed", "Completed", "Cancelled"]],
    }
    delivered = _aggregate([("Delivery Note", {
        "company": company_doc.name,
        "docstatus": 1,
        "posting_date": today,
        "is_return": 0,
    })], "base_grand_total")
    purchase_read = _can_read("Purchase Order")
    return {
        "state": "ok",
        "company": company_doc.name,
        "currency": company_doc.default_currency or "MZN",
        "warehouse": resolved_warehouse,
        "query_time": frappe.utils.now_datetime().strftime("%Y-%m-%d %H:%M:%S"),
        "sales": {
            "state": ("ok" if sales["count"] else "no_data") if invoice_read else "no_permission",
            "amount": sales["total"],
            "invoice_count": sale_count,
            "return_count": returns,
        },
        "outstanding": {
            "state": ("ok" if outstanding["count"] else "no_data") if invoice_read else "no_permission",
            "amount": outstanding["total"],
        },
        "orders_pending": {
            "state": "ok" if _can_read("Sales Order") else "no_permission",
            "count": _count("Sales Order", order_filters),
            "items": _list(
                "Sales Order", order_filters,
                ["name", "customer", "transaction_date", "delivery_date", "per_delivered", "status"],
                limit=5, order_by="delivery_date asc, modified asc",
            ),
        },
        "delivered_today": {"state": ("ok" if delivered["count"] else "no_data") if _can_read("Delivery Note") else "no_permission", "amount": delivered["total"]},
        "invoiced_today": {"state": ("ok" if sales["count"] else "no_data") if invoice_read else "no_permission", "amount": sales["total"]},
        "draft_sales": {"state": "ok", "items": _detail_rows(
            [("Sales Invoice", {"company": company_doc.name, "docstatus": 0})],
            {}, ["customer", "posting_date", "grand_total"], "modified desc",
        )},
        "pending_purchase": {
            "state": "ok" if purchase_read else "no_permission",
            "items": _list(
                "Purchase Order",
                {"company": company_doc.name, "docstatus": 1, "per_received": ["<", 100],
                 "status": ["not in", ["Closed", "Completed", "Cancelled"]]},
                ["name", "supplier", "transaction_date", "per_received", "status"],
                limit=5, order_by="transaction_date asc, modified asc",
            ),
        },
        "overdue": {"state": ("ok" if overdue_rows else "no_data") if invoice_read else "no_permission", "items": overdue_rows},
        "low_stock": _low_stock(resolved_warehouse),
        "item_data": _item_data_status(),
        "permissions": _permissions(),
        "stock_entry_types": _stock_entry_types(),
    }


def _search_fields():
    return [field for field in ["name", "item_code", "custom_order_code", "custom_spu_code", "custom_label_barcode"] if _has_field("Item", field)]


@frappe.whitelist()
@frappe.read_only()
def search_items(query=None):
    """Find permitted items by code, public order code, SPU or barcode."""
    query = (query or "").strip()
    if not query or len(query) > 120:
        return {"state": "no_data", "items": []}
    if not _can_read("Item"):
        return {"state": "no_permission", "items": []}
    fields = ["name", "item_code", "item_name", "variant_of", "has_variants", "stock_uom"]
    fields.extend(field for field in ["custom_order_code", "custom_spu_code", "custom_color_code", "custom_pos_short_name"] if _has_field("Item", field))
    items = _list("Item", {"disabled": 0}, fields, limit=20, or_filters=[[field, "=", query] for field in _search_fields()])
    if _can_read("Item"):
        parents = [row.parent for row in _list("Item Barcode", {"barcode": query}, ["parent"], limit=20)]
        if parents:
            items.extend(_list("Item", {"name": ["in", parents], "disabled": 0}, fields, limit=20))
    items_by_name = {row.name: row for row in items}
    if not items_by_name:
        return {"state": "no_data", "items": []}
    colors = {}
    if _can_read("Item"):
        colors = {row.parent: row.attribute_value for row in _list(
            "Item Variant Attribute", {"parent": ["in", list(items_by_name)], "attribute": "Cor"},
            ["parent", "attribute_value"], limit=0,
        )}
    return {"state": "ok", "items": [{
        "name": row.name, "item_code": row.item_code, "item_name": row.item_name,
        "variant_of": row.variant_of, "color": colors.get(row.name),
        "order_code": row.get("custom_order_code") or "", "spu_code": row.get("custom_spu_code") or "",
        "color_code": row.get("custom_color_code") or "", "pos_short_name": row.get("custom_pos_short_name") or "",
        "stock_uom": row.stock_uom,
    } for row in items_by_name.values()]}


@frappe.whitelist()
@frappe.read_only()
def get_color_variants(barcode=None, template=None, barcode_only=False):
    """Resolve a shared style barcode to permitted concrete color variants.

    The barcode identifies the style only; the employee must choose the fixed
    color explicitly. When barcode_only is true, only barcode fields are
    considered, so an Item Code or SPU cannot accidentally open the picker.
    This endpoint never changes inventory or documents.
    """
    if not _can_read("Item"):
        return {"state": "no_permission", "templates": []}
    candidates = []
    if template:
        candidates = _list(
            "Item", {"name": template, "disabled": 0},
            ["name", "item_code", "item_name", "has_variants", "variant_of"], limit=1,
        )
    elif barcode:
        barcode = str(barcode).strip()
        if _can_read("Item"):
            parents = _list("Item Barcode", {"barcode": barcode}, ["parent"], limit=20)
            parent_names = list({row.parent for row in parents})
            if parent_names:
                candidates.extend(_list(
                    "Item", {"name": ["in", parent_names], "disabled": 0},
                    ["name", "item_code", "item_name", "has_variants", "variant_of"], limit=20,
                ))
        strict_barcode = str(barcode_only).lower() in {"1", "true", "yes"}
        if not strict_barcode:
            fields = _search_fields()
            if fields:
                candidates.extend(_list(
                    "Item", {"disabled": 0},
                    ["name", "item_code", "item_name", "has_variants", "variant_of"], limit=20,
                    or_filters=[[field, "=", barcode] for field in fields],
                ))
    if not candidates:
        return {"state": "no_data", "templates": []}

    template_names = list(dict.fromkeys(row.variant_of or row.name for row in candidates))
    templates = _list(
        "Item", {"name": ["in", template_names], "disabled": 0},
        ["name", "item_code", "item_name", "has_variants"], limit=0,
    )
    item_fields = ["name", "item_code", "item_name", "stock_uom", "image", "variant_of"]
    item_fields.extend(field for field in ["custom_order_code", "custom_color_code", "custom_swatch_image"] if _has_field("Item", field))
    attributes = {}
    if _can_read("Item"):
        variant_names = [row.name for row in _list(
            "Item", {"variant_of": ["in", template_names], "disabled": 0}, ["name"], limit=0,
        )]
        if variant_names:
            attributes = {row.parent: row.attribute_value for row in _list(
                "Item Variant Attribute",
                {"parent": ["in", variant_names], "attribute": "Cor"},
                ["parent", "attribute_value"], limit=0,
            )}
    result = []
    for template_doc in templates:
        variant_rows = _list(
            "Item", {"variant_of": template_doc.name, "disabled": 0},
            item_fields, limit=0, order_by="name asc",
        )
        if not variant_rows and not template_doc.has_variants:
            variant_rows = _list("Item", {"name": template_doc.name, "disabled": 0}, item_fields, limit=1)
        result.append({
            "template": {"name": template_doc.name, "item_code": template_doc.item_code, "item_name": template_doc.item_name},
            "variants": [{
                "name": row.name,
                "item_code": row.item_code,
                "item_name": row.item_name,
                "stock_uom": row.stock_uom,
                "image": row.get("custom_swatch_image") or row.get("image") or "",
                "color": attributes.get(row.name, ""),
                "color_code": row.get("custom_color_code") or "",
                "order_code": row.get("custom_order_code") or "",
            } for row in variant_rows],
        })
    return {"state": "ok" if result else "no_data", "templates": result}


def get_home_page(user):
    """Default only ordinary employees; preserve explicit app/workspace choices."""
    if user in {"Guest", "Administrator"}:
        return None
    user_doc = frappe.get_cached_doc("User", user)
    if user_doc.user_type != "System User" or user_doc.default_app or user_doc.default_workspace:
        return None
    if frappe.db.get_value("DefaultValue", {"parent": user, "defkey": "desktop:home_page"}, "defvalue"):
        return None
    identity = f"{user_doc.name} {user_doc.email}".lower()
    if any(re.search(rf"(?:^|[._-]){marker}(?:$|[.@_-])", identity) for marker in SERVICE_ACCOUNT_MARKERS):
        return None
    # boot.home_page expects the Page document name; the browser route is
    # generated by Frappe as /desk/solua-home.
    return "solua-home"
