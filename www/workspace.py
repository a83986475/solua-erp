import frappe


no_cache = 1


def get_context(context):
    if frappe.session.user == "Guest":
        frappe.local.flags.redirect_location = "/login?redirect-to=%2Fworkspace"
        raise frappe.Redirect

    if frappe.db.get_value("User", frappe.session.user, "user_type") != "System User":
        frappe.throw("此工作台仅供 ERP 系统用户使用。", frappe.PermissionError)

    context.no_cache = 1
