"""Resolve a Sales Invoice's customer store from its linked Sales Orders."""

from collections import defaultdict

import frappe


STORE_FIELD = "custom_store_name"


def _records(doctype, names, fields, **filters):
    if not names:
        return {}
    return {
        row["name"]: row
        for row in frappe.get_all(
            doctype, filters={**filters, "name": ["in", sorted(names)]}, fields=["name", *fields]
        )
    }


def _invoice_items(names):
    items = defaultdict(list)
    if names:
        for row in frappe.get_all(
            "Sales Invoice Item",
            filters={"parenttype": "Sales Invoice", "parent": ["in", sorted(names)]},
            fields=["parent", "sales_order", "so_detail", "dn_detail"],
        ):
            items[row["parent"]].append(row)
    return items


def _invoice_details(names):
    return _records(
        "Sales Invoice", names, ["customer", "company", "is_return", "return_against", STORE_FIELD]
    )


def _has_order_source(row):
    return row.get("sales_order") or row.get("so_detail") or row.get("dn_detail")


def _same_party(source, invoice):
    return source.get("customer") == invoice.get("customer") and source.get("company") == invoice.get("company")


def _stores_from_orders(invoices, items_by_invoice):
    order_names_by_invoice = {}
    original_names = {
        invoice["return_against"]
        for name, invoice in invoices.items()
        if invoice.get("is_return") and invoice.get("return_against")
        and not any(map(_has_order_source, items_by_invoice.get(name, ())))
    }
    originals = _invoice_details(original_names)
    original_items = _invoice_items({name for name, invoice in originals.items() if not invoice.get(STORE_FIELD)})
    original_stores = {}
    source_items = {}
    for name, invoice in invoices.items():
        items = items_by_invoice.get(name, ())
        if not any(map(_has_order_source, items)):
            original_name = invoice.get("return_against")
            original = originals.get(original_name) if invoice.get("is_return") else None
            if original and _same_party(original, invoice):
                if original.get(STORE_FIELD):
                    original_stores[name] = original[STORE_FIELD]
                items = original_items.get(original_name, ())
        source_items[name] = items

    items = [row for rows in source_items.values() for row in rows]
    order_lines = _records(
        "Sales Order Item",
        {row["so_detail"] for row in items if row.get("so_detail") and not row.get("sales_order")},
        ["parent"],
        parenttype="Sales Order",
    )
    delivery_lines = _records(
        "Delivery Note Item",
        {
            row["dn_detail"] for row in items
            if row.get("dn_detail") and not row.get("sales_order") and row.get("so_detail") not in order_lines
        },
        ["against_sales_order"],
        parenttype="Delivery Note",
    )
    for name, rows in source_items.items():
        order_names_by_invoice[name] = {
            row.get("sales_order")
            or order_lines.get(row.get("so_detail"), {}).get("parent")
            or delivery_lines.get(row.get("dn_detail"), {}).get("against_sales_order")
            for row in rows if _has_order_source(row)
        }

    orders = _records(
        "Sales Order",
        {order for names in order_names_by_invoice.values() for order in names if order},
        ["company", "customer", STORE_FIELD],
    )
    for name, invoice in invoices.items():
        stores = set()
        for order_name in order_names_by_invoice[name]:
            order = orders.get(order_name)
            store = (order.get(STORE_FIELD) or "").strip() if order and _same_party(order, invoice) else ""
            stores.add(store)
        if len(stores) == 1 and "" not in stores:
            original_stores[name] = stores.pop()
    return original_stores


def apply_invoice_store(doc):
    """Populate mapped drafts immediately and validate the value on save."""
    if doc.docstatus < 2 and doc.meta.has_field(STORE_FIELD):
        stores = _stores_from_orders({doc.name: doc}, {doc.name: doc.get("items", [])})
        doc.set(STORE_FIELD, stores.get(doc.name))
    return doc


def get_invoice_stores(names):
    """Use saved names first, with a read-only lookup for historical invoices."""
    invoices = _invoice_details(names)
    historical = {name: row for name, row in invoices.items() if not row.get(STORE_FIELD)}
    stores = {name: row[STORE_FIELD] for name, row in invoices.items() if row.get(STORE_FIELD)}
    stores.update(_stores_from_orders(historical, _invoice_items(historical)))
    return stores
