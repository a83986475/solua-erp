"""Wholesale level three prices exclude the additional cash-payment discount."""
import frappe
from frappe import _
from frappe.utils import flt

LEVEL_THREE = "Wholesale Selling 3"
DISCOUNT_ACCOUNT = "Discount Allowed - SH"


def excludes_cash_discount(doc):
    customer = doc.get("customer") or (doc.get("party") if doc.get("party_type") == "Customer" else None)
    return doc.get("selling_price_list") == LEVEL_THREE or bool(
        customer and frappe.db.get_value("Customer", customer, "default_price_list") == LEVEL_THREE
    )


def validate_sales_document(doc, method=None):
    if not excludes_cash_discount(doc):
        return
    for row in doc.get("payment_schedule") or []:
        row.discount = 0
        row.discount_type = None
        row.discount_date = None
        row.discounted_amount = 0


def payment_is_excluded(doc):
    if excludes_cash_discount(doc):
        return True
    return any(
        row.reference_doctype == "Sales Invoice" and row.reference_name
        and flt(row.allocated_amount) != 0
        and frappe.db.get_value("Sales Invoice", row.reference_name, "selling_price_list") == LEVEL_THREE
        for row in doc.get("references") or []
    )


def validate_payment_entry(doc, method=None):
    if doc.get("party_type") != "Customer":
        return
    if any(row.account == DISCOUNT_ACCOUNT and flt(row.amount) != 0 for row in doc.get("deductions") or []):
        if payment_is_excluded(doc):
            frappe.throw(_("3级批发价不适用现金付款3%折扣，请移除现金折扣并按应收金额收款。"))


@frappe.whitelist()
def get_eligibility(customer=None, invoice_names=None):
    names = frappe.parse_json(invoice_names or "[]")
    if not isinstance(names, list) or len(names) > 100:
        frappe.throw(_("无效的发票列表"))
    excluded = False
    if customer:
        doc = frappe.get_doc("Customer", customer)
        doc.check_permission("read")
        excluded = doc.default_price_list == LEVEL_THREE
    for name in set(names):
        doc = frappe.get_doc("Sales Invoice", name)
        doc.check_permission("read")
        excluded = excluded or excludes_cash_discount(doc)
    return {"eligible": not excluded}
