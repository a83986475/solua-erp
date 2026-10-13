import frappe


def get_context(context):
    context.no_cache = 1
    context.title = "管理员移动台"
    context.body_class = "solua-mobile-page"
    view = str(frappe.form_dict.get("view") or "stock").strip()
    context.mobile_order = view == "order"
    context.mobile_customer = view == "customer"
    context.mobile_orders = view == "orders"
    context.mobile_sales = view == "sales"
    context.mobile_reports = view == "reports"
    context.mobile_delivery = view == "delivery"
    context.mobile_stock = view == "stock"
    context.desktop_delivery = context.mobile_delivery and str(frappe.form_dict.get("desktop") or "").strip() == "1"
    if context.desktop_delivery:
        context.title = "送货中心"
        context.body_class += " solua-delivery-desktop"
    roles = set(frappe.get_roles() or [])
    context.mobile_admin = frappe.session.user == "Administrator" or "System Manager" in roles
