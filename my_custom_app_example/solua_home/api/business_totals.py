"""Permission-aware totals and the exact documents behind each homepage card."""
from datetime import date, timedelta

import frappe
from frappe.utils import flt, getdate, nowdate
from solua_home.api.home import _can_read, _invoice_specs, _list, _resolve_company

METRICS = {"orders": "总订单金额", "invoices": "总开票金额", "receivable": "总应收款", "paid": "总已付金额"}


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
def get_total(metric="orders", period="month", from_date=None, to_date=None, company=None):
    if metric not in METRICS:
        frappe.throw("无效的统计指标")
    company_doc = _resolve_company(company)
    if not company_doc:
        return {"state": "no_permission", "amount": None, "items": []}
    start, end = date_range(period, from_date, to_date)
    base = {"company": company_doc.name, "docstatus": 1}
    invoice_specs = _invoice_specs(company_doc.name, ["between", [start, end]])
    specs = [("Sales Order", {**base, "transaction_date": ["between", [start, end]]})] if metric == "orders" else invoice_specs
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
