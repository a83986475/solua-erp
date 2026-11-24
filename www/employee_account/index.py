import frappe
from frappe.sessions import get_csrf_token


def get_context(context):
    request = getattr(frappe.local, "request", None)
    if str(getattr(request, "path", "") or "").rstrip("/") == "/employee_account":
        frappe.local.response["http_status_code"] = 404
        raise frappe.DoesNotExistError
    context.no_cache = 1
    context.csrf_token = get_csrf_token()
    context.title = "员工账号 / Conta de colaborador"
    context.body_class = "solua-employee-account-page"
    context.logged_in = frappe.session.user != "Guest"
    context.account_allowed = context.logged_in and "Solua Stock Viewer" in frappe.get_roles()
    context.current_user = frappe.session.user if context.logged_in else ""
    context.current_email = frappe.db.get_value("User", frappe.session.user, "email") if context.account_allowed else ""
