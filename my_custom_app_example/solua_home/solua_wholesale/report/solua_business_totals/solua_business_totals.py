import frappe
from solua_home.api.business_totals import get_total, METRICS


def execute(filters=None):
    filters = filters or {}
    result = get_total(**{key: filters.get(key) for key in ("metric", "period", "from_date", "to_date", "company", "customer") if filters.get(key)})
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
    if result["metric"] == "unbilled":
        columns += [
            {"fieldname": "waiting_days", "label": "已交货天数", "fieldtype": "Int", "width": 110},
            {"fieldname": "invoice_plan", "label": "开票安排", "fieldtype": "Data", "width": 200},
            {"fieldname": "billing_state", "label": "开票状态", "fieldtype": "Data", "width": 110},
            {"fieldname": "price_adjustment", "label": "价格调整", "fieldtype": "Currency", "options": "currency", "width": 130},
            {"fieldname": "action", "label": "开票", "fieldtype": "Data", "width": 150},
        ]
    if result["metric"] == "returns":
        columns += [
            {"fieldname": "billing_state", "label": "退货状态", "fieldtype": "Data", "width": 150},
            {"fieldname": "original_invoice", "label": "原销售发票", "fieldtype": "Link", "options": "Sales Invoice", "width": 210},
            {"fieldname": "action", "label": "处理", "fieldtype": "Data", "width": 150},
        ]
    message = f"{result['from_date']} ~ {result['to_date']}；仅统计已提交单据。"
    if result["metric"] == "receivable":
        message += "按发票日期筛选，显示这些发票当前仍未收回的余额。"
    elif result["metric"] == "orders":
        message += "净额由同期间的开票净额、待交付订单和已交货未开票金额组成；原始订单额与退货、价格调整、贷项及其他差额在首页明细中核对。"
    elif result["metric"] == "paid":
        message += "按收款日期筛选，显示已提交收款单的实际收款金额（支付类型为 Receive 的 Payment Entry 公司币种实收金额）；不包含发票结清、折扣、核销调整或 Pay 退款。"
    elif result["metric"] == "unbilled":
        message += "按交货日期筛选；合计只包含实际待开票商品，价格调整单列且不生成发票。价格调整按已提交正向发票行的本币净额核对，不以 billed_amt 判断；贷项单另列于首页差额明细。已有草稿可直接查看，生成后请核对税费、付款条件再保存和提交。"
    elif result["metric"] == "returns":
        message += "按退货交货单日期核对；已开票且明细精确匹配时可生成未提交贷项草稿，未开票退货不生成贷项，明细不一致必须人工核对。贷项草稿 Update Stock 固定关闭，提交不会再次回增库存。"
    elif result["metric"] == "pending_delivery":
        message += "按订单日期筛选仍需履约的订单；按各行未交付数量和订单价格折算金额，并按比例分摊整单税费和折扣。排除已关闭、已完成及取消订单；开票与否不影响待交付判断。"
    return columns, result["items"], message, None, [{"label": METRICS[result["metric"]], "value": result["amount"], "datatype": "Currency", "currency": result["currency"]}]
