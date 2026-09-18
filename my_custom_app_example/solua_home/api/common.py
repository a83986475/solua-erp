# solua_home/api/common.py
# ============================
# 通用功能：内外部 API、工具函数
# ============================

import frappe
from frappe import _


def validate_address(doc, method=None):
    """地址保存时验证"""
    # 示例：地址必填字段检查
    if not doc.city:
        frappe.throw(_("城市为必填项"))

    # 示例：自动补全地址类型
    if not doc.address_type:
        doc.address_type = "Billing"


def validate_contact(doc, method=None):
    """联系人保存时验证"""
    # 示例：手机号格式检查（简单校验）
    if doc.mobile_no and not doc.mobile_no.startswith("1"):
        frappe.msgprint(
            _("手机号 {0} 格式可能不正确，请确认").format(doc.mobile_no),
            alert=True,
        )


# ------------------- 对外 API（可供外部系统调用） -------------------

@frappe.whitelist(allow_guest=False)
def get_customer_summary(customer_name):
    """获取客户摘要信息（可供外部系统调用）"""
    customer = frappe.get_doc("Customer", customer_name)
    return {
        "customer_name": customer.customer_name,
        "customer_group": customer.customer_group,
        "territory": customer.territory,
        "currency": customer.default_currency,
        "status": "active" if customer.disabled == 0 else "disabled",
    }


@frappe.whitelist(allow_guest=False)
def get_today_sales():
    """获取今日销售汇总"""
    today = frappe.utils.nowdate()
    data = frappe.db.sql("""
        SELECT
            COUNT(name) as invoice_count,
            SUM(grand_total) as total_amount
        FROM `tabSales Invoice`
        WHERE posting_date = %s
            AND docstatus = 1
    """, today, as_dict=True)

    return {
        "date": today,
        "invoice_count": data[0].invoice_count or 0,
        "total_amount": data[0].total_amount or 0,
    }


@frappe.whitelist()
def get_zh_translations():
    """返回合并后的简体中文翻译字典（所有 app 的 zh.csv/.po 合并）。

    用途：Print Designer 界面汉化。设计器字段列表裸渲染英文 label（不走 __()），
    且会话语言可能是 en，所以前端拉取此字典做运行时文本替换。
    结果按 24h 缓存，避免每次请求都读 CSV。
    """
    cache_key = "solua_home:zh_translations"
    translations = frappe.cache().get_value(cache_key)
    if translations is None:
        from frappe.translate import get_translations_from_apps

        translations = get_translations_from_apps("zh")
        frappe.cache().set_value(cache_key, translations, expires_in_sec=24 * 60 * 60)
    return translations


# ------------------- 工具函数 -------------------

def send_wechat_notification(user, title, message):
    """发送企业微信通知（示例）"""
    # 实际对接企业微信 API
    # webhook_url = frappe.db.get_single_value("WeChat Settings", "webhook_url")
    # requests.post(webhook_url, json={"msgtype": "text", "text": {"content": message}})
    frappe.log_error(f"通知 {user}: {title} - {message}", "企业微信通知")


def log_api_call(endpoint, request_data, response_data):
    """记录 API 调用日志"""
    frappe.get_doc({
        "doctype": "API Log",
        "endpoint": endpoint,
        "request_data": str(request_data),
        "response_data": str(response_data),
        "timestamp": frappe.utils.now_datetime(),
    }).insert(ignore_permissions=True)
