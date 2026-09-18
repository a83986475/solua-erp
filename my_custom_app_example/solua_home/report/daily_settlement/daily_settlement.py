"""日结报表 - Daily Settlement Report"""
import frappe
from frappe import _
from frappe.utils import getdate, nowdate


def execute(filters=None):
    """日结报表入口"""
    columns = get_columns()
    data = get_data(filters)
    chart = get_chart(data)
    return columns, data, None, chart


def get_columns():
    return [
        {"fieldname": "cashier", "fieldtype": "Data", "label": _("收银员"), "width": 160},
        {"fieldname": "invoice_count", "fieldtype": "Int", "label": _("发票数"), "width": 80},
        {"fieldname": "total_sales", "fieldtype": "Currency", "label": _("销售总额"), "width": 120},
        {"fieldname": "return_count", "fieldtype": "Int", "label": _("退货数"), "width": 80},
        {"fieldname": "return_amount", "fieldtype": "Currency", "label": _("退货金额"), "width": 120},
        {"fieldname": "net_sales", "fieldtype": "Currency", "label": _("净销售"), "width": 120},
        {"fieldname": "cash_amount", "fieldtype": "Currency", "label": _("Cash"), "width": 100},
        {"fieldname": "card_amount", "fieldtype": "Currency", "label": _("Credit Card"), "width": 100},
        {"fieldname": "stored_value_amount", "fieldtype": "Currency", "label": _("储值支付"), "width": 100},
        {"fieldname": "closing_status", "fieldtype": "Data", "label": _("交班状态"), "width": 100},
    ]


def get_data(filters):
    report_date = filters.get("report_date") or nowdate()

    # 按收银员汇总
    rows = frappe.db.sql("""
        SELECT
            si.owner as cashier,
            COUNT(*) as invoice_count,
            SUM(si.grand_total) as total_sales,
            SUM(CASE WHEN si.is_return = 1 THEN 1 ELSE 0 END) as return_count,
            SUM(CASE WHEN si.is_return = 1 THEN si.grand_total ELSE 0 END) as return_amount
        FROM `tabSales Invoice` si
        WHERE si.is_pos = 1
          AND si.posting_date = %(date)s
          AND si.docstatus = 1
        GROUP BY si.owner
        ORDER BY si.owner
    """, {"date": report_date}, as_dict=True)

    # 按支付方式汇总（每个收银员）
    payment_map = {}
    payments = frappe.db.sql("""
        SELECT
            si.owner as cashier,
            p.mode_of_payment,
            SUM(p.amount) as amount
        FROM `tabSales Invoice Payment` p
        INNER JOIN `tabSales Invoice` si ON si.name = p.parent
        WHERE si.is_pos = 1
          AND si.posting_date = %(date)s
          AND si.docstatus = 1
        GROUP BY si.owner, p.mode_of_payment
    """, {"date": report_date}, as_dict=True)

    for p in payments:
        key = p.cashier
        if key not in payment_map:
            payment_map[key] = {}
        payment_map[key][p.mode_of_payment] = float(p.amount or 0)

    # 交班状态
    closing_map = {}
    closings = frappe.get_all("POS Closing Entry",
        filters={"posting_date": report_date},
        fields=["user", "docstatus", "grand_total"])
    for c in closings:
        closing_map[c.user] = "已交班" if c.docstatus == 1 else "草稿"

    # 组装数据
    data = []
    total_invoices = 0
    total_sales = 0
    total_returns = 0
    total_return_amt = 0
    total_cash = 0
    total_card = 0
    total_stored = 0

    for row in rows:
        pm = payment_map.get(row.cashier, {})
        cash = pm.get("Cash", 0)
        card = pm.get("Credit Card", 0)
        stored = pm.get("会员储值支付", 0)  # 如果有的话

        total_invoices += row.invoice_count or 0
        total_sales += float(row.total_sales or 0)
        total_returns += row.return_count or 0
        total_return_amt += float(row.return_amount or 0)
        total_cash += cash
        total_card += card
        total_stored += stored

        data.append({
            "cashier": row.cashier,
            "invoice_count": row.invoice_count,
            "total_sales": float(row.total_sales or 0),
            "return_count": row.return_count or 0,
            "return_amount": float(row.return_amount or 0),
            "net_sales": float(row.total_sales or 0) - float(row.return_amount or 0),
            "cash_amount": cash,
            "card_amount": card,
            "stored_value_amount": stored,
            "closing_status": closing_map.get(row.cashier, "—"),
        })

    # 合计行
    if data:
        data.append({
            "cashier": "合计",
            "invoice_count": total_invoices,
            "total_sales": total_sales,
            "return_count": total_returns,
            "return_amount": total_return_amt,
            "net_sales": total_sales - total_return_amt,
            "cash_amount": total_cash,
            "card_amount": total_card,
            "stored_value_amount": total_stored,
            "closing_status": "",
        })

    return data


def get_chart(data):
    """生成支付方式饼图"""
    if not data or len(data) <= 1:
        return None

    # 取合计行数据
    total_row = data[-1] if data else {}

    labels = []
    values = []
    if total_row.get("cash_amount"):
        labels.append("Cash")
        values.append(total_row["cash_amount"])
    if total_row.get("card_amount"):
        labels.append("Credit Card")
        values.append(total_row["card_amount"])
    if total_row.get("stored_value_amount"):
        labels.append("储值支付")
        values.append(total_row["stored_value_amount"])

    if not labels:
        return None

    return {
        "data": {
            "labels": labels,
            "datasets": [{"values": values}],
        },
        "type": "pie",
        "colors": ["#28a745", "#007bff", "#e67e22"],
    }
