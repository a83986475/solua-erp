import frappe
from frappe.sessions import get_csrf_token


def get_context(context):
    context.csrf_token = get_csrf_token()
    context.no_cache = 1
    context.title = "Consulta de stock"
    context.body_class = "solua-mobile-page solua-stock-employee-page"
    context.mobile_stock_employee = True
    context.mobile_stock_employee_allowed = frappe.session.user != "Guest" and "Solua Stock Viewer" in frappe.get_roles()
