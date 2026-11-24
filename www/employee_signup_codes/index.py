import frappe


no_cache = 1


def get_context(context):
    context.no_cache = 1
    context.csrf_token = frappe.sessions.get_csrf_token()
    context.admin_allowed = (
        frappe.session.user == "Administrator" or "System Manager" in frappe.get_roles()
    )
    context.current_user = frappe.session.user
    context.title = "员工注册授权码 / Códigos de registo"
