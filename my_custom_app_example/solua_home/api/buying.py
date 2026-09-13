# solua_home/api/buying.py
# ============================
# 采购模块的自定义验证和事件处理
# ============================

import frappe
from frappe import _

from solua_home.api.stock import validate_transaction_quantities


def validate_purchase_order(doc, method=None):
    """采购订单保存时验证"""
    validate_transaction_quantities(doc)

    # 示例：采购金额上限控制
    if doc.grand_total > 50000:
        frappe.throw(_("采购金额超过 50,000，需要上级审批"))

    # 示例：检查供应商状态
    supplier_status = frappe.db.get_value("Supplier", doc.supplier, "custom_status")
    if supplier_status == "已停用":
        frappe.throw(_("供应商 {0} 已被停用，无法创建采购订单").format(doc.supplier))


def validate_purchase_invoice(doc, method=None):
    """采购发票验证"""
    validate_transaction_quantities(doc)

    # 示例：发票金额不能超过采购订单金额
    for item in doc.items:
        if item.purchase_order:
            po_amount = frappe.db.get_value(
                "Purchase Order Item",
                {"parent": item.purchase_order, "item_code": item.item_code},
                "amount",
            )
            if po_amount and item.amount > po_amount * 1.1:
                frappe.throw(
                    _("物料 {0} 的发票金额 {1} 超过采购订单金额 {2} 的110%").format(
                        item.item_code, item.amount, po_amount
                    )
                )


def validate_supplier(doc, method=None):
    """供应商保存时验证"""
    # 示例：统一税号格式
    if doc.tax_id:
        doc.tax_id = doc.tax_id.replace(" ", "").upper()
