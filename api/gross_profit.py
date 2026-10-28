"""Gross Profit report corrections for amount-only credit notes."""

from frappe.utils import flt

import frappe
from frappe.desk.query_report import run as _native_run


def _recalculate_invoice_rows(
    rows, original_qty, price_only_credits, original_stock_qty=None, adjustment_parents=None
):
    """Use stock-UOM quantity for cost and keep stock cost on credit-only returns."""
    original_stock_qty = original_stock_qty or {}
    changed_parents = set()
    changed_parents.update(adjustment_parents or {})

    for row in rows:
        if row.get("indent") != 1:
            continue

        key = (row.get("parent_invoice"), row.get("sales_invoice"))
        is_price_only_credit = key in price_only_credits
        if not is_price_only_credit and key not in original_stock_qty:
            continue

        source_qty = flt(original_qty.get(key))
        source_stock_qty = flt(original_stock_qty.get(key))
        display_qty = source_qty if is_price_only_credit else flt(row.get("qty"))
        if is_price_only_credit:
            qty = source_qty
            cost_qty = source_stock_qty or display_qty
        elif source_stock_qty and abs(display_qty - source_qty) < 0.001 and abs(source_stock_qty - source_qty) >= 0.001:
            # Native Gross Profit can leave a box quantity on the row; use its stock quantity once.
            cost_qty = source_stock_qty
        else:
            # Native Gross Profit already reports the stock-UOM quantity for this row.
            cost_qty = display_qty
        valuation_rate = flt(row.get("valuation_rate"))
        if (is_price_only_credit and not qty) or not cost_qty or valuation_rate <= 0:
            continue

        selling_amount = flt(row.get("selling_amount"))
        buying_amount = flt(cost_qty * valuation_rate)
        gross_profit = selling_amount - buying_amount
        cost_changed = abs(flt(row.get("buying_amount")) - buying_amount) >= 0.001
        if is_price_only_credit:
            row["qty"] = qty
            row["avg._selling_rate"] = flt(selling_amount / qty, 3)
        if display_qty:
            row["valuation_rate"] = flt(buying_amount / display_qty, 3)
        row["buying_amount"] = flt(buying_amount, 3)
        row["gross_profit"] = flt(gross_profit, 3)
        row["gross_profit_%"] = flt(gross_profit / selling_amount * 100, 3) if selling_amount else 0
        if cost_changed or is_price_only_credit:
            changed_parents.add(row.get("parent_invoice"))

    for row in rows:
        parent = row.get("sales_invoice")
        if row.get("indent") != 0 or not parent or parent == "Total" or parent not in changed_parents:
            continue

        children = [child for child in rows if child.get("indent") == 1 and child.get("parent_invoice") == parent]
        selling_amount = sum(flt(child.get("selling_amount")) for child in children)
        buying_amount = sum(flt(child.get("buying_amount")) for child in children)
        gross_profit = selling_amount - buying_amount
        row["selling_amount"] = flt(selling_amount, 3)
        row["buying_amount"] = flt(buying_amount, 3)
        row["gross_profit"] = flt(gross_profit, 3)
        row["gross_profit_%"] = flt(gross_profit / selling_amount * 100, 3) if selling_amount else 0

    total = next((row for row in rows if row.get("sales_invoice") == "Total"), None)
    if total and changed_parents:
        parents = [row for row in rows if row.get("indent") == 0 and row.get("sales_invoice") not in (None, "Total")]
        selling_amount = sum(flt(row.get("selling_amount")) for row in parents)
        buying_amount = sum(flt(row.get("buying_amount")) for row in parents)
        gross_profit = selling_amount - buying_amount
        total["selling_amount"] = flt(selling_amount, 3)
        total["buying_amount"] = flt(buying_amount, 3)
        total["gross_profit"] = flt(gross_profit, 3)
        total["gross_profit_%"] = flt(gross_profit / selling_amount * 100, 3) if selling_amount else 0

    return rows


def _price_only_return_names(return_items, returns, original_qty, original_net_amount):
    states = {}
    for item in return_items:
        return_name = item.get("parent")
        key = (returns.get(return_name), item.get("item_code"))
        state = states.setdefault(
            return_name,
            {"full_qty": True, "amount_changed": False, "all_blank": True, "blank_amount": 0},
        )
        if not item.get("item_code"):
            state["blank_amount"] += abs(flt(item.get("base_net_amount")))
            continue

        state["all_blank"] = False
        source_qty = flt(original_qty.get(key))
        source_amount = flt(original_net_amount.get(key))
        if not source_qty or abs(abs(flt(item.get("qty"))) - abs(source_qty)) >= 0.001:
            state["full_qty"] = False
        if source_amount and abs(abs(flt(item.get("base_net_amount"))) - abs(source_amount)) >= 0.001:
            state["amount_changed"] = True
    return {
        name for name, state in states.items()
        if (state["all_blank"] and state["blank_amount"] > 0)
        or (state["full_qty"] and state["amount_changed"])
    }


def _append_price_adjustment_rows(rows, adjustments):
    """Show blank-item price credits in the invoice tree without adding stock cost."""
    if not adjustments:
        return

    parent_rows = {
        row.get("sales_invoice"): row
        for row in rows
        if row.get("indent") == 0 and row.get("sales_invoice") not in (None, "Total")
    }
    for parent, entries in sorted(
        adjustments.items(),
        key=lambda item: next(
            (index for index, row in enumerate(rows) if row is parent_rows.get(item[0])),
            -1,
        ),
        reverse=True,
    ):
        if parent not in parent_rows:
            continue
        parent_row = parent_rows[parent]
        parent_index = rows.index(parent_row)
        insert_at = parent_index + 1
        while (
            insert_at < len(rows)
            and rows[insert_at].get("indent") == 1
            and rows[insert_at].get("parent_invoice") == parent
        ):
            insert_at += 1

        adjustment_rows = []
        for entry in entries:
            amount = flt(entry.get("amount"))
            adjustment_rows.append(
                {
                    "indent": 1,
                    "parent_invoice": parent,
                    "sales_invoice": "",
                    "customer": parent_row.get("customer"),
                    "customer_group": parent_row.get("customer_group"),
                    "customer_name": parent_row.get("customer_name"),
                    "posting_date": parent_row.get("posting_date"),
                    "description": f"Price adjustment {entry.get('name')}",
                    "qty": None,
                    "avg._selling_rate": None,
                    "valuation_rate": None,
                    "selling_amount": amount,
                    "buying_amount": 0,
                    "gross_profit": amount,
                    "gross_profit_%": None,
                    "project": parent_row.get("project"),
                    "currency": parent_row.get("currency"),
                }
            )
        rows[insert_at:insert_at] = adjustment_rows


def _apply_grouped_total(result, reference_total):
    """Keep non-Invoice group totals aligned with corrected Invoice totals."""
    if not reference_total:
        return result

    rows = result.get("result") or []
    columns = result.get("columns") or []
    group_field = columns[0].get("fieldname") if columns else None
    total = next((row for row in rows if group_field and row.get(group_field) == "Total"), None)
    if not total or not flt(total.get("selling_amount")):
        return result

    total["selling_amount"] = flt(reference_total.get("selling_amount"))
    total["buying_amount"] = flt(reference_total.get("buying_amount"))
    total["gross_profit"] = flt(reference_total.get("gross_profit"))
    selling_amount = flt(total.get("selling_amount"))
    total["gross_profit_%"] = (
        flt(total["gross_profit"] / selling_amount * 100, 3) if selling_amount else 0
    )
    return result


def _fix_amount_only_returns(result, filters):
    rows = result.get("result") or []
    if not rows:
        return result

    group_by = filters.get("group_by", "Invoice")
    if group_by != "Invoice":
        invoice_filters = dict(filters, group_by="Invoice")
        invoice_result = _native_run(
            report_name="Gross Profit", filters=invoice_filters, are_default_filters=False
        )
        invoice_result = _fix_amount_only_returns(invoice_result, invoice_filters)
        invoice_rows = invoice_result.get("result") or []
        parents = list({row.get("parent_invoice") for row in invoice_rows if row.get("indent") == 1 and row.get("parent_invoice")})
    else:
        parents = list({row.get("parent_invoice") for row in rows if row.get("indent") == 1 and row.get("parent_invoice")})
    if not parents:
        return result

    original_items = frappe.get_all(
        "Sales Invoice Item",
        filters={"parent": ["in", parents]},
        fields=["parent", "item_code", "qty", "stock_qty", "base_net_amount"],
        limit_page_length=0,
    )
    original_qty = {}
    original_net_amount = {}
    original_stock_qty = {}
    for item in original_items:
        key = (item.parent, item.item_code)
        original_qty[key] = flt(original_qty.get(key)) + flt(item.qty)
        original_net_amount[key] = flt(original_net_amount.get(key)) + flt(item.base_net_amount)
        original_stock_qty[key] = flt(original_stock_qty.get(key)) + flt(item.stock_qty)

    price_only_returns = frappe.get_all(
        "Sales Invoice",
        filters={
            "return_against": ["in", parents],
            "docstatus": 1,
            "is_return": 1,
            "update_stock": 0,
        },
        fields=["name", "return_against"],
        limit_page_length=5000,
    )
    price_only_credits = {}
    price_only_adjustments = {}
    if price_only_returns:
        returns = {row.name: row.return_against for row in price_only_returns}
        return_items = frappe.get_all(
            "Sales Invoice Item",
            filters={"parent": ["in", list(returns)]},
            fields=["parent", "item_code", "qty", "base_net_amount"],
            limit_page_length=0,
        )
        price_only_names = _price_only_return_names(
            return_items, returns, original_qty, original_net_amount
        )
        for item in return_items:
            if item.parent not in price_only_names:
                continue
            if not item.item_code:
                adjustment = price_only_adjustments.setdefault(
                    returns[item.parent], {"name": item.parent, "amount": 0}
                )
                adjustment["amount"] += flt(item.base_net_amount)
                continue
            key = (returns[item.parent], item.item_code)
            price_only_credits[key] = flt(price_only_credits.get(key)) + flt(item.base_net_amount)

    adjustments_by_parent = {}
    for parent, adjustment in price_only_adjustments.items():
        adjustments_by_parent.setdefault(parent, []).append(adjustment)
    if group_by != "Invoice":
        reference_total = next(
            (row for row in invoice_rows if row.get("sales_invoice") == "Total"), None
        )
        return _apply_grouped_total(result, reference_total)

    _append_price_adjustment_rows(rows, adjustments_by_parent)
    _recalculate_invoice_rows(
        rows,
        original_qty,
        price_only_credits,
        original_stock_qty,
        adjustments_by_parent,
    )
    return result


@frappe.whitelist()
@frappe.read_only()
def run(
    report_name,
    filters=None,
    user=None,
    ignore_prepared_report=False,
    custom_columns=None,
    is_tree=False,
    parent_field=None,
    are_default_filters=True,
    js_filters=None,
):
    result = _native_run(
        report_name=report_name,
        filters=filters,
        user=user,
        ignore_prepared_report=ignore_prepared_report,
        custom_columns=custom_columns,
        is_tree=is_tree,
        parent_field=parent_field,
        are_default_filters=are_default_filters,
        js_filters=js_filters,
    )
    if report_name != "Gross Profit":
        return result

    parsed_filters = frappe.parse_json(filters) if isinstance(filters, str) else (filters or {})
    return _fix_amount_only_returns(result, parsed_filters)
