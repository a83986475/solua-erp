# solua_home/override/sales_invoice.py
# =========================================
# 重写 SalesInvoice 类的方法
# 当 hooks.py 中的 doc_events 不够用时，可以用这种方式完全重写方法
# =========================================

import frappe
from frappe import _
from frappe.utils import flt
from erpnext.accounts.doctype.sales_invoice.sales_invoice import SalesInvoice


class CustomSalesInvoice(SalesInvoice):
    """
    自定义销售发票类

    使用方式：在 hooks.py 中注册
    extend_doctype_class = {
        "Sales Invoice": "solua_home.override.sales_invoice.CustomSalesInvoice",
    }
    """

    @frappe.whitelist()
    def set_missing_values(self, for_validate=False):
        """Keep POS return payments negative after ERPNext rebuilds them."""
        super().set_missing_values(for_validate)
        if self.is_pos and self.is_return:
            for payment in self.get("payments") or []:
                payment.amount = -abs(flt(payment.amount))

    def verify_payment_amount_is_negative(self):
        """Normalize POS return payments before ERPNext validates them."""
        for payment in self.get("payments") or []:
            payment.amount = -abs(flt(payment.amount))
        return super().verify_payment_amount_is_negative()

    def validate(self):
        """保存时验证（重写父类方法）"""
        # 调用父类的 validate（保留原有所有验证逻辑）
        super().validate()

        # 添加自定义验证
        self.custom_validate_approval()

    def on_submit(self):
        """提交时执行（重写父类方法）"""
        # 调用父类的 on_submit
        super().on_submit()

        # 提交后的自定义逻辑
        self.custom_after_submit()

    def on_cancel(self):
        """取消时执行（重写父类方法）"""
        super().on_cancel()
        self.custom_after_cancel()

    # ==================== 自定义方法 ====================

    def custom_validate_approval(self):
        """自定义审批验证"""
        # 大额审批
        if self.grand_total > 100000 and not self.get("custom_approver"):
            frappe.throw(_("金额超过 100,000，必须指定审批人"))

        if self.get("custom_approver") and not self.get("custom_approval_date"):
            self.set("custom_approval_date", frappe.utils.nowdate())

    def custom_after_submit(self):
        """提交后的自定义操作"""
        # 更新客户信息
        if self.customer:
            frappe.db.set_value(
                "Customer",
                self.customer,
                "custom_last_transaction_date",
                frappe.utils.nowdate(),
            )

        # 记录日志
        frappe.log_error(
            f"发票 {self.name} 已提交，金额: {self.grand_total}",
            "自定义发票日志",
        )

    def custom_after_cancel(self):
        """取消后的自定义操作"""
        frappe.msgprint(_("发票 {0} 已取消，已执行自定义清理逻辑").format(self.name))
