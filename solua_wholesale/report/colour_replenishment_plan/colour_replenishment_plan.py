"""Estimate replenishment by colour using days when stock was on hand."""

from collections import defaultdict
from datetime import timedelta
from math import ceil

import frappe
from frappe import _
from frappe.utils import flt, getdate

from solua_home.api.color_card import get_item_cor


MIN_STOCK_DAYS = 14
SALES_VOUCHERS = ("Delivery Note", "Sales Invoice")


def _days(filters, field, minimum, maximum):
    value = flt(filters.get(field))
    if not minimum <= value <= maximum or value != int(value):
        frappe.throw(_("{0}������ {1} �� {2} ֮�������").format(
            _({"history_days": "�ؿ�����", "lead_days": "��������", "cover_days": "�����󱸻�����"}[field]),
            minimum, maximum,
        ))
    return int(value)


def _stock_days(opening, entries, start, end):
    # No earlier ledger means the colour first enters observation on its first movement.
    if opening is None and not entries:
        return 0, 0
    observed_from = start if opening is not None else entries[0][0]
    days_with_stock = set()
    balance = opening or 0
    day = observed_from
    for movement_day, change in entries:
        if balance > 0.000001:
            while day <= movement_day:
                days_with_stock.add(day)
                day += timedelta(days=1)
        day = movement_day
        balance += change
    if balance > 0.000001:
        while day <= end:
            days_with_stock.add(day)
            day += timedelta(days=1)
    observed = (end - observed_from).days + 1
    return len(days_with_stock), observed - len(days_with_stock)


def _internal_sales_vouchers(entries):
    internal = set()
    for doctype in SALES_VOUCHERS:
        names = {row.voucher_no for row in entries if row.voucher_type == doctype}
        if names:
            # The report already has access to these ledger entries. Only read the internal flag.
            internal.update((doctype, name) for name in frappe.get_all(
                doctype, filters={"name": ["in", list(names)], "is_internal_customer": 1}, pluck="name",
            ))
    return internal


def _incoming(item_codes, warehouses, company, today, deadline):
    scope = {"item_code": ["in", item_codes], "warehouse": ["in", warehouses],
             "parenttype": "Purchase Order", "parentfield": "items", "docstatus": 1, "delivered_by_supplier": 0}
    parents = frappe.get_all("Purchase Order Item", filters=scope, pluck="parent", distinct=True)
    if not parents:
        return {}, {}
    open_orders = {row.name: row.status for row in frappe.get_list("Purchase Order", filters={
        "name": ["in", parents], "company": company, "docstatus": 1,
        "status": ["not in", ["Closed", "Completed", "Delivered"]],
    }, fields=["name", "status"], limit_page_length=0)}
    if not open_orders:
        return {}, {}
    outstanding, due = defaultdict(float), defaultdict(float)
    for row in frappe.get_all("Purchase Order Item", filters={**scope, "parent": ["in", list(open_orders)]},
                             fields=["parent", "item_code", "qty", "received_qty", "conversion_factor", "schedule_date"]):
        qty = max(0, flt(row.qty) - flt(row.received_qty)) * (flt(row.conversion_factor) or 1)
        outstanding[row.item_code] += qty
        if open_orders[row.parent] != "On Hold" and row.schedule_date and today <= getdate(row.schedule_date) <= deadline:
            due[row.item_code] += qty
    return outstanding, due


def _columns():
    return [
        {"fieldname": "item_code", "label": _("��ɫ����"), "fieldtype": "Link", "options": "Item", "width": 190},
        {"fieldname": "colour", "label": _("ɫ��"), "fieldtype": "Data", "width": 85},
        {"fieldname": "item_name", "label": _("��Ʒ����"), "fieldtype": "Data", "width": 180},
        {"fieldname": "stock_uom", "label": _("��浥λ"), "fieldtype": "Link", "options": "UOM", "width": 90},
        *[
            {"fieldname": field, "label": _(label), "fieldtype": "Float", "precision": precision, "width": width}
            for field, label, precision, width in (
                ("net_shipped", "��ʷ������", 2, 100),
                ("stock_days", "�л�����", 0, 90),
                ("out_days", "�޻�����", 0, 90),
                ("daily_rate", "�л��վ�����", 2, 115),
                ("on_hand", "��ǰ�ֻ�", 2, 95),
                ("reserved", "������ռ��", 2, 100),
                ("incoming", "�ɹ�δ����", 2, 105),
                ("due", "�ƻ����ڵ���", 2, 115),
                ("suggested_qty", "���鶩����", 0, 110),
            )
        ],
        {"fieldname": "note", "label": _("��ע"), "fieldtype": "Data", "width": 150},
    ]


def execute(filters=None):
    filters = frappe._dict(filters or {})
    if not filters.company or not filters.template:
        frappe.throw(_("��ѡ��˾�Ϳ�ʽģ��"))
    if not frappe.get_list("Company", filters={"name": filters.company}, pluck="name", limit_page_length=1):
        frappe.throw(_("�޷��鿴��ѡ��˾"), frappe.PermissionError)
    for doctype in ("Bin", "Stock Ledger Entry", "Purchase Order"):
        if not frappe.has_permission(doctype, "read"):
            frappe.throw(_("�˱�����Ҫ��ȡ {0} ��Ȩ��").format(_(doctype)), frappe.PermissionError)
    history_days = _days(filters, "history_days", 14, 365)
    lead_days = _days(filters, "lead_days", 1, 365)
    cover_days = _days(filters, "cover_days", 1, 365)
    today = getdate()
    start, end = today - timedelta(days=history_days), today - timedelta(days=1)
    horizon = lead_days + cover_days
    deadline = today + timedelta(days=horizon)

    warehouse_filter = {"company": filters.company, "is_group": 0, "disabled": 0}
    if filters.warehouse:
        warehouse_filter["name"] = filters.warehouse
    warehouses = frappe.get_list("Warehouse", filters=warehouse_filter, pluck="name", limit_page_length=0)
    if not warehouses:
        frappe.throw(_("û�пɶ�ȡ�Ĳֿ�"))
    items = frappe.get_list("Item", filters={"variant_of": filters.template, "disabled": 0, "is_stock_item": 1},
                           fields=["name", "item_name", "stock_uom", "custom_color_code"], limit_page_length=0)
    if not items:
        return _columns(), [], _("��ѡ��ʽû�пɶ�ȡ����Ч�����ɫ��")
    item_codes = [row.name for row in items]
    scope = {"item_code": ["in", item_codes], "warehouse": ["in", warehouses]}
    ledger_scope = {**scope, "company": filters.company, "is_cancelled": 0}
    ledger = frappe.get_list(
        "Stock Ledger Entry", filters={**ledger_scope, "posting_date": ["<=", end]},
        fields=["item_code", "warehouse", "posting_date", "actual_qty", "qty_after_transaction", "voucher_type", "voucher_no"],
        order_by="posting_datetime asc, creation asc, name asc", limit_page_length=0,
    )
    entries = [row for row in ledger if getdate(row.posting_date) >= start]
    internal = _internal_sales_vouchers(entries)
    balances, openings = defaultdict(float), defaultdict(float)
    by_item, net_shipped = defaultdict(list), defaultdict(float)
    for row in ledger:
        key = (row.item_code, row.warehouse)
        previous = balances[key]
        # Use the actual balance, including reconciliations and backdated stock entries.
        balances[key] = flt(row.qty_after_transaction) if row.qty_after_transaction is not None else previous + flt(row.actual_qty)
        change = balances[key] - previous
        day = getdate(row.posting_date)
        if day < start:
            openings[row.item_code] += change
            continue
        by_item[row.item_code].append((day, change))
        if row.voucher_type in SALES_VOUCHERS and (row.voucher_type, row.voucher_no) not in internal:
            net_shipped[row.item_code] -= flt(row.actual_qty)

    on_hand, reserved = defaultdict(float), defaultdict(float)
    for row in frappe.get_list("Bin", filters=scope, fields=["item_code", "actual_qty", "reserved_qty"], limit_page_length=0):
        on_hand[row.item_code] += flt(row.actual_qty)
        reserved[row.item_code] += flt(row.reserved_qty)
    incoming, due = _incoming(item_codes, warehouses, filters.company, today, deadline)

    rows = []
    for item in items:
        code = item.name
        stocked, out = _stock_days(openings.get(code), by_item[code], start, end)
        rate = max(0, net_shipped[code]) / stocked if stocked else None
        due_qty = due.get(code, 0)
        suggested = None
        if stocked >= MIN_STOCK_DAYS:
            suggested = max(0, ceil(rate * horizon - on_hand[code] + reserved[code] - due_qty - 0.000001))
        rows.append({
            "template": filters.template, "item_code": code, "colour": get_item_cor(code, item),
            "item_name": item.item_name, "stock_uom": item.stock_uom,
            "net_shipped": net_shipped[code], "stock_days": stocked, "out_days": out, "daily_rate": rate,
            "on_hand": on_hand[code], "reserved": reserved[code], "incoming": incoming.get(code, 0), "due": due_qty,
            "suggested_qty": suggested,
            "note": _("�л����� {0} �죬�˹�ȷ��").format(MIN_STOCK_DAYS) if suggested is None else "",
        })
    rows.sort(key=lambda row: (row["colour"] or row["item_code"], row["item_code"]))
    message = _("��ʷ���� {0} �� {1}�����ױʿ����ˮ����㣬��������ʵ���漴��Ϊ�л����������ѿ������˻���"
                "���ۼ��ӽ��쵽 {2} Ԥ�Ƶ����Ĳɹ��������ڼ���ͣ�Ĳɹ������Ⱥ˶ԡ�"
                "����������浥λ����ȡ����δָ���ֿ�ʱ���ܹ�˾�¿ɶ�ȡ�Ĳֿ⡣").format(start, end, deadline)
    return _columns(), rows, message

