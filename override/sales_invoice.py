# solua_home/override/sales_invoice.py
# =========================================
# 重写 SalesInvoice 类的方法
# 当 hooks.py 中的 doc_events 不够用时，可以用这种方式完全重写方法
# =========================================

import frappe
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
