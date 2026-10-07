"""Permission-aware totals and the exact documents behind each homepage card."""
from datetime import date, timedelta

import frappe
from frappe.utils import flt, getdate, nowdate
from solua_home.api.home import _can_read, _invoice_specs, _list, _resolve_company

METRICS = {"orders": "总订单金额", "pending_delivery": "待交付订单金额", "invoices": "总开票金额", "receivable": "总应收款", "paid": "总已付金额", "delivered": "送货金额", "unbilled": "已交货未开票金额"}


def pending_delivery_rows(company, start, end, customer=None, closed=False):
    filters = {"company": company, "docstatus": 1, "transaction_date": ["between", [start, end]]}
    if customer:
        filters["customer"] = customer
    filters["status"] = "Closed" if closed else ["not in", ["Closed", "Completed", "Cancelled"]]
    returned = {}
    if closed:
        return_filters = {"company": company, "docstatus": 1, "is_return": 1}
        if customer:
            return_filters["customer"] = customer
        for note in _list("Delivery Note", return_filters, ["name"]):
            for item in frappe.get_doc("Delivery Note", note.name).items:
                if item.so_detail:
                    returned[item.so_detail] = returned.get(item.so_detail, 0) - flt(item.qty)
    rows = []
    for order in _list("Sales Order", filters, ["name", "transaction_date", "customer"], order_by="transaction_date asc, name asc"):
        doc = frappe.get_doc("Sales Order", order.name)
        amount = 0
        for item in doc.items:
            qty = flt(item.qty)
            if qty > 0:
                amount += flt(item.base_amount) * min(1, max(0, qty - flt(item.delivered_qty) - returned.get(item.name, 0)) / qty)
        if amount > 0.005:
            # Prorate header taxes/discounts using the outstanding item value.
            amount *= flt(doc.base_grand_total) / flt(doc.base_total) if flt(doc.base_total) else 1
            rows.append({"doctype": "Sales Order", "name": doc.name, "date": str(doc.transaction_date),
                         "customer": doc.customer, "amount": flt(amount, 2), "status": doc.status})
    return rows


def date_range(period="month", from_date=None, to_date=None):
    period = {"本周": "week", "本月": "month", "本季度": "quarter", "本年": "year", "今天": "today", "自定义": "custom"}.get(period, period)
    today = getdate(nowdate())
    if period == "custom":
        if not from_date or not to_date:
            frappe.throw("请选择开始和结束日期")
        start, end = getdate(from_date), getdate(to_date)
    else:
        starts = {"today": today, "week": today - timedelta(days=today.weekday()),
                  "month": today.replace(day=1), "quarter": date(today.year, (today.month - 1) // 3 * 3 + 1, 1),
                  "year": date(today.year, 1, 1)}
        if period not in starts:
            frappe.throw("无效的时间范围")
        start, end = starts[period], today
    if start > end:
        frappe.throw("开始日期不能晚于结束日期")
    return str(start), str(end)


@frappe.whitelist()
@frappe.read_only()
def get_total(metric="orders", period="month", from_date=None, to_date=None, company=None, customer=None):
    if metric not in METRICS:
        frappe.throw("无效的统计指标")
    company_doc = _resolve_company(company)
    if not company_doc:
        return {"state": "no_permission", "amount": None, "items": []}
    start, end = date_range(period, from_date, to_date)
    if metric == "pending_delivery":
        if not _can_read("Sales Order"):
            return {"state": "no_permission", "amount": None, "items": []}
        items = pending_delivery_rows(company_doc.name, start, end, customer)
        for row in items:
            row["currency"] = company_doc.default_currency
        return {"state": "ok" if items else "no_data", "amount": sum(row["amount"] for row in items), "items": items,
                "from_date": start, "to_date": end, "company": company_doc.name,
                "currency": company_doc.default_currency, "metric": metric, "period": period}
    if metric == "unbilled":
        from solua_home.api.unbilled import get_rows
        if not _can_read("Delivery Note"):
            return {"state": "no_permission", "amount": None, "items": []}
        items = get_rows(company_doc.name, start, end, customer)
        return {"state": "ok" if items else "no_data", "amount": sum(row["amount"] for row in items), "items": items,
                "from_date": start, "to_date": end, "company": company_doc.name,
                "currency": company_doc.default_currency, "metric": metric, "period": period}
    base = {"company": company_doc.name, "docstatus": 1}
    invoice_specs = _invoice_specs(company_doc.name, ["between", [start, end]])
    specs = [("Sales Order", {**base, "transaction_date": ["between", [start, end]]})] if metric == "orders" else invoice_specs
    if metric == "delivered":
        specs = [("Delivery Note", {**base, "posting_date": ["between", [start, end]], "is_return": 0})]
    if not any(_can_read(dt) for dt, _ in specs):
        return {"state": "no_permission", "amount": None, "items": []}
    items = []
    for dt, filters in specs:
        date_field = "transaction_date" if dt == "Sales Order" else "posting_date"
        fields = ["name", date_field]
        fields += ["customer", "base_grand_total"]
        if metric in ("receivable", "paid"):
            fields += ["outstanding_amount", "conversion_rate"]
        if metric == "receivable":
            filters = {**filters, "outstanding_amount": [">", 0]}
        if customer:
            filters = {**filters, "customer": customer}
        for row in _list(dt, filters, fields, order_by=f"{date_field} asc, name asc"):
            amount = flt(row.base_grand_total)
            if metric == "receivable":
                amount = flt(row.outstanding_amount) * flt(row.conversion_rate or 1)
            elif metric == "paid":
                amount = flt(row.base_grand_total) - flt(row.outstanding_amount) * flt(row.conversion_rate or 1)
            if metric == "paid" and not amount:
                continue
            items.append({"doctype": dt, "name": row.name, "date": str(row.get(date_field)),
                          "customer": row.get("customer"), "amount": amount,
                          "currency": company_doc.default_currency})
    return {"state": "ok" if items else "no_data", "amount": sum(row["amount"] for row in items),
            "items": items, "from_date": start, "to_date": end, "company": company_doc.name,
            "currency": company_doc.default_currency, "metric": metric, "period": period}


@frappe.whitelist()
@frappe.read_only()
def get_reconciliation(period="year", from_date=None, to_date=None, company=None, customer=None):
    """Explain order less invoice totals; all categories use one explicit period."""
    if not all(_can_read(dt) for dt in ("Sales Order", "Delivery Note", "Sales Invoice")):
        return {"state": "no_permission", "amount": None, "groups": []}
    args = dict(period=period, from_date=from_date, to_date=to_date, company=company, customer=customer)
    totals = {metric: get_total(metric=metric, **args) for metric in ("orders", "invoices", "pending_delivery", "unbilled")}
    orders = totals["orders"]
    if orders["state"] == "no_permission":
        return {"state": "no_permission", "amount": None, "groups": []}
    company, start, end = orders["company"], orders["from_date"], orders["to_date"]
    groups = []
    def add(label, items):
        groups.append({"label": label, "amount": sum(row["amount"] for row in items), "items": items})
    add("待交付订单", totals["pending_delivery"]["items"])
    add("已结束订单未交付金额", pending_delivery_rows(company, start, end, customer, closed=True))
    billing = totals["unbilled"]["items"]
    add("已交货待开票商品", [dict(row, amount=row["amount"] - row["price_adjustment"]) for row in billing
                             if abs(row["amount"] - row["price_adjustment"]) > 0.005])
    add("价格调整", [dict(row, amount=row["price_adjustment"]) for row in billing if abs(row["price_adjustment"]) > 0.005])
    filters = {"company": company, "docstatus": 1, "is_return": 1, "posting_date": ["between", [start, end]]}
    if customer:
        filters["customer"] = customer
    returns = _list("Delivery Note", filters, ["name", "posting_date", "customer", "base_grand_total"])
    add("退货", [{"doctype": "Delivery Note", "name": row.name, "date": str(row.posting_date),
                  "customer": row.customer, "amount": -flt(row.base_grand_total)} for row in returns])
    add("贷项冲减", [dict(row, amount=-row["amount"]) for row in totals["invoices"]["items"] if row["amount"] < 0])
    amount = orders["amount"] - totals["invoices"]["amount"]
    residual = flt(amount - sum(group["amount"] for group in groups), 2)
    if abs(residual) > 0.005:
        add("其他差额（跨期、关联、税费或折扣）", [{"amount": residual}])
    return {"state": "ok", "amount": amount, "groups": groups, "from_date": start, "to_date": end,
            "currency": orders["currency"], "company": company}
