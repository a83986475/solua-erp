import frappe
from solua_home.api.business_totals import get_total, METRICS


def execute(filters=None):
    filters = filters or {}
    result = get_total(**{key: filters.get(key) for key in ("metric", "period", "from_date", "to_date", "company") if filters.get(key)})
    if result["state"] == "no_permission":
        frappe.throw("没有查看此指标的权限", frappe.PermissionError)
    columns = [
        {"fieldname": "date", "label": "日期", "fieldtype": "Date", "width": 110},
        {"fieldname": "doctype", "label": "单据类型", "fieldtype": "Data", "width": 130},
        {"fieldname": "name", "label": "单据", "fieldtype": "Dynamic Link", "options": "doctype", "width": 210},
        {"fieldname": "customer", "label": "客户", "fieldtype": "Link", "options": "Customer", "width": 240},
        {"fieldname": "currency", "label": "币种", "fieldtype": "Data", "hidden": 1},
        {"fieldname": "amount", "label": METRICS[result["metric"]], "fieldtype": "Currency", "options": "currency", "width": 170},
    ]
    message = f"{result['from_date']} ~ {result['to_date']}；仅统计已提交单据。"
    if result["metric"] == "receivable":
        message += "按发票日期筛选，显示这些发票当前仍未收回的余额。"
    elif result["metric"] == "paid":
        message += "按收款日期统计客户实收（含预收款及 POS 现金收款），客户退款扣减；不包含日记账核销。"
    return columns, result["items"], message, None, [{"label": METRICS[result["metric"]], "value": result["amount"], "datatype": "Currency", "currency": result["currency"]}]
