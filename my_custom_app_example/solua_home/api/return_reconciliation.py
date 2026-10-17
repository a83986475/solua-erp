"""Classify submitted customer returns without changing accounting or stock."""
from collections import defaultdict

import frappe
from frappe.utils import date_diff, flt, nowdate

from solua_home.api.home import _can_create, _can_read, _list
from solua_home.api.unbilled import billing_module


def classify_return_lines(return_rows, invoice_rows, credit_rows=None):
    """Classify return rows using exact SO/DN detail matches where possible."""
    credit_rows = credit_rows or []
    credited = defaultdict(float)
    for row in credit_rows:
        key = (row.get("invoice"), row.get("so_detail"), row.get("item_code"))
        credited[key] += abs(flt(row.get("qty")))

    invoice_by_name = defaultdict(list)
    for row in invoice_rows:
        if not row.get("is_return") and flt(row.get("qty")) > 0:
            invoice_by_name[row.get("invoice")].append(row)

    line_states = []
    invoice_names = []
    for return_row in return_rows:
        quantity = abs(flt(return_row.get("qty")))
        exact_totals = defaultdict(float)
        available_totals = defaultdict(float)
        same_order_item = []
        for invoice_name, rows in invoice_by_name.items():
            for row in rows:
                if row.get("item_code") != return_row.get("item_code"):
                    continue
                if row.get("sales_order") == return_row.get("sales_order"):
                    same_order_item.append(row)
                exact_detail = (
                    return_row.get("so_detail")
                    and row.get("so_detail") == return_row.get("so_detail")
                ) or (
                    return_row.get("original_dn_detail")
                    and row.get("dn_detail") == return_row.get("original_dn_detail")
                )
                if not exact_detail:
                    continue
                available = flt(row.get("qty")) - credited[(invoice_name, row.get("so_detail"), row.get("item_code"))]
                exact_totals[invoice_name] += flt(row.get("qty"))
                available_totals[invoice_name] += available
        total_billed = sum(exact_totals.values())
        original_qty = flt(return_row.get("original_qty"))
        if original_qty and exact_totals and total_billed < original_qty - 0.000001:
            remainder = original_qty - total_billed
            if abs(remainder - quantity) <= 0.000001:
                line_states.append("covered")
                continue
            if total_billed + quantity < original_qty - 0.000001:
                line_states.append("unbilled")
                continue
        exact = sorted(invoice_name for invoice_name, available in available_totals.items()
                       if available + 0.000001 >= quantity)
        if len(exact) == 1:
            line_states.append("exact")
            invoice_names.append(exact[0])
        elif exact:
            line_states.append("multiple_invoices")
        elif same_order_item:
            line_states.append("mismatched_detail")
        else:
            line_states.append("unbilled")

    if line_states and all(state == "exact" for state in line_states) and len(set(invoice_names)) == 1:
        return {"state": "已开票待贷项", "invoice_names": sorted(set(invoice_names)), "line_states": line_states}
    if line_states and all(state == "covered" for state in line_states):
        return {"state": "原发票数量已覆盖", "invoice_names": [], "line_states": line_states}
    if line_states and all(state in {"unbilled", "covered"} for state in line_states):
        return {"state": "未开票无需贷项", "invoice_names": [], "line_states": line_states}
    return {"state": "明细不一致", "invoice_names": [], "line_states": line_states}


def _invoice_rows(company, customer):
    return frappe.db.sql(
        """SELECT si.name invoice, si.customer, si.is_return,
                          sii.item_code, sii.qty, sii.sales_order, sii.so_detail,
                          sii.delivery_note, sii.dn_detail
                     FROM `tabSales Invoice` si
                LEFT JOIN `tabSales Invoice Item` sii ON sii.parent = si.name
                    WHERE si.company = %(company)s
                      AND si.customer = %(customer)s
                      AND si.docstatus = 1""",
        {"company": company, "customer": customer},
        as_dict=True,
    )


def _credit_rows(company, customer):
    return frappe.db.sql(
        """SELECT si.return_against invoice, si.is_return,
                          sii.item_code, sii.qty, sii.so_detail
                     FROM `tabSales Invoice` si
                LEFT JOIN `tabSales Invoice Item` sii ON sii.parent = si.name
                    WHERE si.company = %(company)s
                      AND si.customer = %(customer)s
                      AND si.docstatus = 1
                      AND si.is_return = 1""",
        {"company": company, "customer": customer},
        as_dict=True,
    )


def _drafts_for_return(source_name):
    parents = frappe.get_all(
        "Sales Invoice Item",
        filters={"delivery_note": source_name, "parenttype": "Sales Invoice"},
        pluck="parent",
        limit_page_length=100,
    )
    if not parents:
        return []
    return [
        row.name
        for row in frappe.get_all(
            "Sales Invoice",
            filters={"name": ["in", list(dict.fromkeys(parents))], "docstatus": 0, "is_return": 1},
            fields=["name"],
            order_by="modified desc",
            limit_page_length=100,
        )
    ]


def _return_row(source):
    original = frappe.get_doc("Delivery Note", source.return_against) if source.return_against else None
    original_by_so_detail = {
        row.so_detail: row for row in (original.items if original else []) if row.so_detail
    }
    return_rows = [
        {
            "item_code": row.item_code,
            "qty": row.qty,
            "sales_order": row.against_sales_order,
            "so_detail": row.so_detail,
            "original_dn_detail": getattr(original_by_so_detail.get(row.so_detail), "name", None),
            "original_qty": getattr(original_by_so_detail.get(row.so_detail), "qty", None),
        }
        for row in source.items
        if flt(row.qty) < 0
    ]
    classification = classify_return_lines(
        return_rows,
        _invoice_rows(source.company, source.customer),
        _credit_rows(source.company, source.customer),
    )
    drafts = _drafts_for_return(source.name)
    submitted_credits = frappe.get_all(
        "Sales Invoice Item",
        filters={"delivery_note": source.name, "parenttype": "Sales Invoice"},
        pluck="parent",
        limit_page_length=100,
    )
    submitted_credits = [
        row.name
        for row in frappe.get_all(
            "Sales Invoice",
            filters={"name": ["in", list(dict.fromkeys(submitted_credits))], "docstatus": 1, "is_return": 1},
            fields=["name"],
            limit_page_length=100,
        )
    ] if submitted_credits else []
    if submitted_credits:
        classification = {**classification, "state": "已有贷项", "invoice_names": []}
    elif drafts:
        classification = {**classification, "state": "已有草稿", "invoice_names": []}

    amount = abs(flt(getattr(source, "base_grand_total", 0) or source.grand_total))
    can_prepare = classification["state"] == "已开票待贷项" and _can_create("Sales Invoice")
    if classification["state"] == "已有草稿":
        action = "查看草稿"
    elif can_prepare:
        action = "生成贷项草稿"
    elif classification["state"] in ("未开票无需贷项", "原发票数量已覆盖"):
        action = "无需贷项"
    elif classification["state"] == "已有贷项":
        action = "已完成"
    else:
        action = "人工核对"
    return {
        "doctype": "Delivery Note",
        "name": source.name,
        "is_return": 1,
        "date": str(source.posting_date),
        "customer": source.customer,
        "amount": flt(amount, 2),
        "currency": frappe.get_cached_value("Company", source.company, "default_currency"),
        "waiting_days": max(0, date_diff(nowdate(), source.posting_date)),
        "billing_state": classification["state"],
        "original_invoice": classification["invoice_names"][0] if len(classification["invoice_names"]) == 1 else "",
        "draft_invoices": drafts,
        "action": action,
        "can_prepare_return": bool(can_prepare),
    }


@frappe.whitelist()
@frappe.read_only()
def get_rows(company, start, end, customer=None):
    if not _can_read("Delivery Note"):
        return []
    filters = {"company": company, "docstatus": 1, "is_return": 1, "posting_date": ["between", [start, end]]}
    if customer:
        filters["customer"] = customer
    return [_return_row(frappe.get_doc("Delivery Note", row.name))
            for row in _list("Delivery Note", filters, ["name"], order_by="posting_date asc, name asc")]


@frappe.whitelist()
def prepare_return_invoice(delivery_note):
    if not _can_read("Delivery Note"):
        frappe.throw("没有查看退货交货单的权限", frappe.PermissionError)
    if not _can_create("Sales Invoice"):
        frappe.throw("没有创建销售发票的权限", frappe.PermissionError)
    source = frappe.get_doc("Delivery Note", delivery_note)
    source.check_permission("read")
    if source.docstatus != 1 or not source.is_return:
        frappe.throw("只能为已提交的退货交货单生成贷项草稿")
    existing = _drafts_for_return(source.name)
    if existing:
        return {"draft_invoices": existing}
    row = _return_row(source)
    if row["billing_state"] != "已开票待贷项" or not row["original_invoice"]:
        frappe.throw(f"{row['billing_state']}：当前不能自动生成贷项草稿")
    invoice = billing_module().make_sales_invoice(source.name)
    invoice.return_against = row["original_invoice"]
    invoice.update_stock = 0
    invoice.remarks = f"退货贷项草稿：依据 {source.name}；原发票 {row['original_invoice']}。仅草稿，未提交。"
    if not invoice.is_return or any(flt(item.qty) >= 0 for item in invoice.items):
        frappe.throw("退货贷项草稿校验失败：商品数量或退货标记不正确")
    invoice.insert()
    return {"draft_invoices": [invoice.name], "status": "draft_created"}
