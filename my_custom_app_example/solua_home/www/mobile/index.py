import frappe


def get_context(context):
    context.no_cache = 1
    context.title = "管理员移动台"
    context.mobile_order = frappe.form_dict.get("view") == "order"
    roles = set(frappe.get_roles() or [])
    context.mobile_admin = frappe.session.user == "Administrator" or "System Manager" in roles
