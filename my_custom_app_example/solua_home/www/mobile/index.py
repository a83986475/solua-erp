import frappe


def get_context(context):
    context.no_cache = 1
    context.title = "管理员移动台"
    view = frappe.form_dict.get("view")
    context.mobile_order = view == "order"
    context.mobile_customer = view == "customer"
    roles = set(frappe.get_roles() or [])
    context.mobile_admin = frappe.session.user == "Administrator" or "System Manager" in roles
