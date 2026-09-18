"""POS 交班 & 日结 API for solua_home

提供：
- get_today_closing: 查询当日交班状态
- create_closing_entry: 创建/提交当日交班单
- get_daily_settlement: 日结报表数据（按天汇总）
"""
import frappe
from frappe import _
import json
from datetime import datetime, date


@frappe.whitelist()
def get_today_closing(pos_profile=None):
    """查询当日交班状态

    Returns:
        dict: {
            has_opening: bool,       # 是否有开店记录
            has_closing: bool,       # 是否已交班
            closing_name: str,       # 交班单名称（如有）
            closing_status: str,     # Draft/Submitted
            invoice_count: int,      # 当日 POS 发票数
            total_amount: float,     # 当日总销售额
            payments: [...],         # 各支付方式汇总
            period_start: str,       # 班次开始时间
        }
    """
    today = date.today()
    user = frappe.session.user

    # 查找当日交班单
    closing = frappe.db.get_value(
        "POS Closing Entry",
        {"posting_date": today, "user": user, "docstatus": ["in", [0, 1]]},
        ["name", "status", "docstatus", "grand_total", "period_start_date",
         "period_end_date", "pos_profile"],
        as_dict=True,
    )

    # 当日 POS 发票汇总
    invoices = frappe.db.sql("""
        SELECT
            COUNT(*) as cnt,
                COALESCE(SUM(grand_total), 0) as total
        FROM `tabSales Invoice`
        WHERE is_pos = 1
          AND posting_date = %(today)s
          AND docstatus = 1
          AND owner = %(user)s
    """, {"today": today, "user": user}, as_dict=True)

    inv = invoices[0] if invoices else {"cnt": 0, "total": 0}

    # 各支付方式汇总
    payments = frappe.db.sql("""
        SELECT
            p.mode_of_payment,
            SUM(p.amount) as amount,
            COUNT(*) as cnt
        FROM `tabSales Invoice Payment` p
        INNER JOIN `tabSales Invoice` si ON si.name = p.parent
        WHERE si.is_pos = 1
          AND si.posting_date = %(today)s
          AND si.docstatus = 1
          AND si.owner = %(user)s
        GROUP BY p.mode_of_payment
    """, {"today": today, "user": user}, as_dict=True)

    # 查找当日开店记录
    opening = frappe.db.get_value(
        "POS Opening Entry",
        {"posting_date": today, "user": user},
        ["name", "status"],
        as_dict=True,
    )

    return {
        "has_opening": bool(opening),
        "opening_name": opening.name if opening else None,
        "opening_amount": 0,
        "has_closing": bool(closing),
        "closing_name": closing.name if closing else None,
        "closing_status": "Submitted" if closing and closing.docstatus == 1 else "Draft" if closing else None,
        "invoice_count": inv.cnt,
        "total_amount": float(inv.total),
        "payments": [{"mode": p.mode_of_payment, "amount": float(p.amount), "count": p.cnt} for p in payments],
        "period_start": str(closing.period_start_date) if closing and closing.period_start_date else None,
        "user": user,
        "today": str(today),
    }


@frappe.whitelist()
def create_closing_entry(pos_profile=None, opening_amount=0):
    """创建当日交班单（POS Closing Entry）

    自动聚合当日该用户的所有 POS 发票，生成交班单草稿。
    如果已有草稿，返回现有草稿。
    """
    today = date.today()
    user = frappe.session.user

    # 检查是否已提交
    existing_submitted = frappe.db.get_value(
        "POS Closing Entry",
        {"posting_date": today, "user": user, "docstatus": 1},
        "name",
    )
    if existing_submitted:
        return {"name": existing_submitted, "status": "already_submitted",
                "message": "当日已交班"}

    # 检查是否有草稿
    existing_draft = frappe.db.get_value(
        "POS Closing Entry",
        {"posting_date": today, "user": user, "docstatus": 0},
        "name",
    )
    if existing_draft:
        return {"name": existing_draft, "status": "draft_exists",
                "message": "已有草稿交班单"}

    # 获取 POS Profile
    if not pos_profile:
        pos_profile = frappe.db.get_value(
            "POS Profile",
            {"company": "Solua Home, Lda"},
            "name",
        )

    # 查找当日开店记录
    opening_entry = frappe.db.get_value(
        "POS Opening Entry",
        {"posting_date": today, "user": user},
        ["name", "period_start_date"],
        as_dict=True,
    )

    period_start = opening_entry.period_start_date if opening_entry else datetime.combine(today, datetime.min.time())
    opening_amt = opening_amount

    # 查找当日 POS 发票
    invoices = frappe.get_all(
        "Sales Invoice",
        filters={
            "is_pos": 1,
            "posting_date": today,
            "docstatus": 1,
            "owner": user,
        },
        fields=["name", "grand_total", "customer", "posting_date", "is_return", "return_against"],
    )

    # 各支付方式汇总
    payments_data = frappe.db.sql("""
        SELECT
            p.mode_of_payment,
            SUM(p.amount) as amount
        FROM `tabSales Invoice Payment` p
        INNER JOIN `tabSales Invoice` si ON si.name = p.parent
        WHERE si.is_pos = 1
          AND si.posting_date = %(today)s
          AND si.docstatus = 1
          AND si.owner = %(user)s
        GROUP BY p.mode_of_payment
    """, {"today": today, "user": user}, as_dict=True)

    payments_map = {p.mode_of_payment: float(p.amount) for p in payments_data}

    # 计算总额
    total_grand = sum(inv.grand_total or 0 for inv in invoices)
    total_qty = len(invoices)

    # 创建 POS Closing Entry
    closing = frappe.get_doc({
        "doctype": "POS Closing Entry",
        "period_start_date": period_start,
        "period_end_date": datetime.now(),
        "posting_date": today,
        "posting_time": datetime.now().strftime("%H:%M:%S"),
        "pos_profile": pos_profile,
        "company": "Solua Home, Lda",
        "user": user,
        "status": "Draft",
        "pos_invoices": [
            {
                "pos_invoice": inv.name,
                "posting_date": inv.posting_date,
                "customer": inv.customer,
                "grand_total": inv.grand_total,
                "is_return": inv.is_return or 0,
                "return_against": inv.return_against or "",
            }
            for inv in invoices
        ],
        "grand_total": total_grand,
        "total_quantity": total_qty,
        "payment_reconciliation": [
            {
                "mode_of_payment": mode,
                "opening_amount": opening_amt if mode == "Cash" else 0,
                "expected_amount": amount,
                "closing_amount": amount,  # 默认=实际收款（收银员可修改）
                "difference": 0,
            }
            for mode, amount in payments_map.items()
        ],
    })

    closing.insert(ignore_permissions=True)
    frappe.db.commit()

    return {
        "name": closing.name,
        "status": "created",
        "message": f"交班单已创建：{closing.name}",
        "invoice_count": total_qty,
        "total_amount": total_grand,
    }


@frappe.whitelist()
def get_daily_settlement(report_date=None):
    """日结报表数据

    Args:
        report_date: 日期字符串 (YYYY-MM-DD)，默认今天

    Returns:
        dict: 日结汇总数据
    """
    if not report_date:
        report_date = str(date.today())

    from datetime import datetime as dt
    target_date = dt.strptime(report_date, "%Y-%m-%d").date()

    # 当日全部 POS 发票（所有收银员）
    invoices = frappe.db.sql("""
        SELECT
            si.name, si.grand_total, si.customer, si.owner,
            si.posting_time, si.is_return, si.return_against,
            si.paid_amount, si.base_paid_amount
        FROM `tabSales Invoice` si
        WHERE si.is_pos = 1
          AND si.posting_date = %(date)s
          AND si.docstatus = 1
        ORDER BY si.posting_time
    """, {"date": target_date}, as_dict=True)

    # 各支付方式汇总
    payments = frappe.db.sql("""
        SELECT
            p.mode_of_payment,
            si.owner as cashier,
            SUM(p.amount) as amount,
            COUNT(*) as cnt
        FROM `tabSales Invoice Payment` p
        INNER JOIN `tabSales Invoice` si ON si.name = p.parent
        WHERE si.is_pos = 1
          AND si.posting_date = %(date)s
          AND si.docstatus = 1
        GROUP BY p.mode_of_payment, si.owner
        ORDER BY si.owner, p.mode_of_payment
    """, {"date": target_date}, as_dict=True)

    # 各收银员汇总
    cashier_summary = frappe.db.sql("""
        SELECT
            si.owner as cashier,
            COUNT(*) as invoice_count,
            SUM(si.grand_total) as total_amount,
            SUM(CASE WHEN si.is_return = 1 THEN si.grand_total ELSE 0 END) as return_amount
        FROM `tabSales Invoice` si
        WHERE si.is_pos = 1
          AND si.posting_date = %(date)s
          AND si.docstatus = 1
        GROUP BY si.owner
    """, {"date": target_date}, as_dict=True)

    # 交班记录
    closings = frappe.get_all(
        "POS Closing Entry",
        filters={"posting_date": target_date},
        fields=["name", "user", "status", "docstatus", "grand_total",
                "period_start_date", "period_end_date"],
        order_by="creation",
    )

    # 汇总
    total_sales = sum(inv.grand_total or 0 for inv in invoices)
    total_invoices = len(invoices)
    total_returns = sum(1 for inv in invoices if inv.is_return)
    total_payments = sum(p.amount or 0 for p in payments)

    # 按支付方式汇总（不分收银员）
    payment_by_method = {}
    for p in payments:
        method = p.mode_of_payment
        if method not in payment_by_method:
            payment_by_method[method] = 0
        payment_by_method[method] += float(p.amount or 0)

    return {
        "date": report_date,
        "total_sales": float(total_sales),
        "total_invoices": total_invoices,
        "total_returns": total_returns,
        "total_payments": float(total_payments),
        "payment_by_method": [{"method": k, "amount": v} for k, v in payment_by_method.items()],
        "cashier_summary": [
            {
                "cashier": c.cashier,
                "count": c.invoice_count,
                "total": float(c.total_amount or 0),
                "returns": float(c.return_amount or 0),
            }
            for c in cashier_summary
        ],
        "closings": [
            {
                "name": c.name,
                "user": c.user,
                "status": c.status,
                "grand_total": float(c.grand_total or 0),
                "submitted": c.docstatus == 1,
            }
            for c in closings
        ],
        "invoices": [
            {
                "name": inv.name,
                "grand_total": float(inv.grand_total or 0),
                "customer": inv.customer,
                "cashier": inv.owner,
                "time": str(inv.posting_time or ""),
                "is_return": bool(inv.is_return),
            }
            for inv in invoices[:50]  # 最多返回 50 条
        ],
    }


@frappe.whitelist()
def submit_closing_entry(closing_name):
    """提交交班单"""
    doc = frappe.get_doc("POS Closing Entry", closing_name)
    if doc.docstatus == 1:
        return {"status": "already_submitted"}
    if doc.user != frappe.session.user:
        frappe.throw(_("只能提交自己的交班单"))
    doc.submit()
    frappe.db.commit()
    return {"status": "submitted", "name": doc.name}
