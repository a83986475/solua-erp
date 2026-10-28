"""Read-only API for a dedicated cloud assistant service user.

This module deliberately exposes fixed fields and fixed DocTypes only. It does
not provide a generic database, report, or method execution endpoint.
"""

import frappe
from frappe import _
from frappe.utils import cint, flt


MAX_PAGE_LENGTH = 50


def _page_length(value=20):
    try:
        return max(1, min(cint(value or 20), MAX_PAGE_LENGTH))
    except (TypeError, ValueError):
        return 20


def _page(value=1):
    try:
        return max(1, cint(value or 1))
    except (TypeError, ValueError):
        return 1


def _query(value, required=True):
    value = str(value or "").strip()
    if required and not value:
        frappe.throw(_("查询条件不能为空"))
    return value[:140]


def _read_doc(doctype, name):
    name = _query(name)
    doc = frappe.get_doc(doctype, name)
    doc.check_permission("read")
    return doc


def _require_read(doctype):
    if not frappe.has_permission(doctype, "read"):
        frappe.throw(_("没有读取 {0} 的权限").format(doctype), frappe.PermissionError)


def _paged(rows, page, page_length):
    start = (page - 1) * page_length
    selected = rows[start : start + page_length + 1]
    return {
        "rows": selected[:page_length],
        "page": page,
        "page_length": page_length,
        "has_next": len(selected) > page_length,
    }


@frappe.whitelist()
@frappe.read_only()
def get_capabilities():
    """Return the fixed read-only surface for cloud assistant discovery."""
    return {
        "version": "v1",
        "read_only": True,
        "methods": [
            "get_capabilities",
            "search_items",
            "get_stock",
            "search_customers",
            "list_sales_orders",
            "get_sales_order",
            "get_sales_order_chain",
        ],
    }


@frappe.whitelist()
@frappe.read_only()
def search_items(query, limit=20):
    """Search Item code/name and exact barcode matches for the assistant."""
    query = _query(query)
    limit = _page_length(limit)
    _require_read("Item")
    fields = ["name", "item_code", "item_name", "item_group", "stock_uom", "disabled"]
    exact_codes = {query}
    # shortcut: Item Barcode is a child table; parent Item permission is checked above.
    barcode_rows = frappe.get_all(
        "Item Barcode",
        filters={"barcode": query},
        fields=["parent"],
        limit_page_length=limit,
    )
    exact_codes.update(row.parent for row in barcode_rows if row.parent)
    rows = []
    if exact_codes:
        rows.extend(
            frappe.get_list(
                "Item",
                filters={"name": ["in", list(exact_codes)]},
                fields=fields,
                order_by="item_code asc",
                limit_page_length=limit,
            )
        )
    remaining = limit - len(rows)
    if remaining > 0:
        rows.extend(
            frappe.get_list(
                "Item",
                or_filters=[
                    ["item_code", "like", f"%{query}%"],
                    ["item_name", "like", f"%{query}%"],
                ],
                fields=fields,
                order_by="item_code asc",
                limit_page_length=remaining,
            )
        )
    seen = set()
    result = []
    for row in rows:
        if row.name in seen:
            continue
        seen.add(row.name)
        result.append(row)
    return {"query": query, "rows": result[:limit]}


@frappe.whitelist()
@frappe.read_only()
def get_stock(item_code, warehouse=None):
    """Return available stock without valuation or cost fields."""
    item_code = _query(item_code)
    filters = {"item_code": item_code}
    if warehouse:
        filters["warehouse"] = _query(warehouse)
    rows = frappe.get_list(
        "Bin",
        filters=filters,
        fields=["item_code", "warehouse", "actual_qty", "reserved_qty", "projected_qty"],
        order_by="warehouse asc",
        limit_page_length=MAX_PAGE_LENGTH,
    )
    for row in rows:
        row["available_qty"] = flt(row.actual_qty) - flt(row.reserved_qty)
    return {"item_code": item_code, "warehouse": warehouse or None, "rows": rows}


@frappe.whitelist()
@frappe.read_only()
def search_customers(query, limit=20):
    query = _query(query)
    limit = _page_length(limit)
    rows = frappe.get_list(
        "Customer",
        or_filters=[
            ["name", "like", f"%{query}%"],
            ["customer_name", "like", f"%{query}%"],
        ],
        fields=["name", "customer_name", "customer_group", "territory", "disabled"],
        order_by="customer_name asc",
        limit_page_length=limit,
    )
    return {"query": query, "rows": rows}


@frappe.whitelist()
@frappe.read_only()
def list_sales_orders(query=None, from_date=None, to_date=None, page=1, limit=20):
    page = _page(page)
    limit = _page_length(limit)
    query = _query(query, required=False)
    filters = {}
    if from_date:
        filters["transaction_date"] = [">=", str(from_date)[:10]]
    if to_date:
        filters["transaction_date"] = ["between", [str(from_date or "1900-01-01")[:10], str(to_date)[:10]]]
    or_filters = None
    if query:
        or_filters = [
            ["name", "like", f"%{query}%"],
            ["customer", "like", f"%{query}%"],
            ["customer_name", "like", f"%{query}%"],
        ]
    rows = frappe.get_list(
        "Sales Order",
        filters=filters,
        or_filters=or_filters,
        fields=[
            "name", "customer", "customer_name", "transaction_date", "status",
            "docstatus", "grand_total", "currency", "per_delivered", "per_billed",
        ],
        order_by="transaction_date desc, creation desc, name desc",
        limit_start=(page - 1) * limit,
        limit_page_length=limit + 1,
    )
    return _paged(rows, 1, limit) | {"page": page}


@frappe.whitelist()
@frappe.read_only()
def get_sales_order(name):
    doc = _read_doc("Sales Order", name)
    return {
        "name": doc.name,
        "customer": doc.customer,
        "customer_name": doc.customer_name,
        "transaction_date": str(doc.transaction_date or ""),
        "status": doc.status,
        "docstatus": doc.docstatus,
        "grand_total": doc.grand_total,
        "currency": doc.currency,
        "items": [
            {
                "item_code": row.item_code,
                "item_name": row.item_name,
                "qty": row.qty,
                "uom": row.uom,
                "rate": row.rate,
                "amount": row.amount,
                "warehouse": row.warehouse,
            }
            for row in doc.items
        ],
    }


@frappe.whitelist()
@frappe.read_only()
def get_sales_order_chain(name):
    """Return linked delivery, pick, and invoice documents for one order."""
    name = _query(name)
    _read_doc("Sales Order", name)
    links = {}
    for child_doctype, field, parent_doctype, key in (
        ("Delivery Note Item", "against_sales_order", "Delivery Note", "delivery_notes"),
        ("Pick List Item", "sales_order", "Pick List", "pick_lists"),
        ("Sales Invoice Item", "sales_order", "Sales Invoice", "sales_invoices"),
    ):
        if not frappe.get_meta(child_doctype).has_field(field) or not frappe.has_permission(parent_doctype, "read"):
            links[key] = []
            continue
        # shortcut: child rows inherit access from their parent document.
        rows = frappe.get_all(
            child_doctype,
            filters={field: name},
            fields=["parent"],
            limit_page_length=MAX_PAGE_LENGTH,
        )
        parents = {row.parent for row in rows if row.parent}
        allowed = frappe.get_list(
            parent_doctype,
            filters={"name": ["in", list(parents)]},
            fields=["name"],
            limit_page_length=MAX_PAGE_LENGTH,
        ) if parents else []
        links[key] = sorted({row.name for row in allowed})
    return {"sales_order": name, **links}
