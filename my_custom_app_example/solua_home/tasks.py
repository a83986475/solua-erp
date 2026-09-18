# solua_home/tasks.py
# ========================
# 定时任务（由 hooks.py 中的 scheduler_events 触发）
# ========================

import frappe
from frappe import _
from frappe.utils import nowdate, add_days, flt


def daily_tasks():
    """每日执行的任务"""
    check_overdue_invoices()
    check_low_stock_items()
    frappe.log_error("每日任务执行完毕", "solua_home 定时任务")


def weekly_tasks():
    """每周执行的任务"""
    generate_weekly_report()
    frappe.log_error("每周任务执行完毕", "solua_home 定时任务")


def custom_cron_task():
    """自定义 cron 表达式触发的任务（每天凌晨2点）"""
    cleanup_old_logs()
    frappe.log_error("凌晨清理任务执行完毕", "solua_home 定时任务")


# ==================== 具体任务实现 ====================


def check_overdue_invoices():
    """检查逾期发票并发送通知"""
    overdue_invoices = frappe.db.sql("""
        SELECT
            name, customer, grand_total, outstanding_amount,
            DATEDIFF(CURDATE(), due_date) as overdue_days
        FROM `tabSales Invoice`
        WHERE docstatus = 1
            AND outstanding_amount > 0
            AND due_date < CURDATE()
            AND DATEDIFF(CURDATE(), due_date) >= 30
    """, as_dict=True)

    for inv in overdue_invoices:
        # 记录超期发票
        frappe.log_error(
            f"发票 {inv.name} 已逾期 {inv.overdue_days} 天，"
            f"未结金额: {inv.outstanding_amount}",
            "逾期发票提醒",
        )

        # 可以在这里发送邮件或企业微信通知
        # send_wechat_notification("admin", "逾期提醒", f"发票{inv.name}已逾期")

    if overdue_invoices:
        frappe.msgprint(
            _("发现 {0} 张逾期超过30天的发票").format(len(overdue_invoices))
        )


def check_low_stock_items():
    """检查低库存物料"""
    low_stock_items = frappe.db.sql("""
        SELECT
            i.item_code, i.item_name,
            i.custom_min_stock_level,
            SUM(b.actual_qty) as current_qty
        FROM `tabItem` i
        LEFT JOIN `tabBin` b ON b.item_code = i.item_code
        WHERE i.custom_min_stock_level > 0
            AND i.custom_min_stock_level IS NOT NULL
            AND i.is_stock_item = 1
        GROUP BY i.item_code
        HAVING current_qty < i.custom_min_stock_level
    """, as_dict=True)

    for item in low_stock_items:
        frappe.log_error(
            f"物料 {item.item_code} ({item.item_name}) "
            f"当前库存: {item.current_qty}, "
            f"最低库存: {item.custom_min_stock_level}",
            "低库存提醒",
        )


def generate_weekly_report():
    """生成周报数据"""
    week_start = add_days(nowdate(), -7)

    data = frappe.db.sql("""
        SELECT
            COUNT(si.name) as invoice_count,
            SUM(si.grand_total) as total_sales
        FROM `tabSales Invoice` si
        WHERE si.posting_date >= %s
            AND si.docstatus = 1
    """, week_start, as_dict=True)

    frappe.log_error(
        f"本周销售汇总: {data[0].invoice_count} 张发票, "
        f"总金额: {data[0].total_sales}",
        "周报",
    )


def cleanup_old_logs():
    """清理30天前的旧日志"""
    # 清理 Error Log
    frappe.db.sql("""
        DELETE FROM `tabError Log`
        WHERE creation < DATE_SUB(NOW(), INTERVAL 30 DAY)
    """)

    # 清理 Activity Log
    frappe.db.sql("""
        DELETE FROM `tabActivity Log`
        WHERE creation < DATE_SUB(NOW(), INTERVAL 30 DAY)
    """)

    frappe.db.commit()
