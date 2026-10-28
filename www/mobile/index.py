import frappe
from frappe.sessions import get_csrf_token


def get_context(context):
    context.csrf_token = get_csrf_token()
    context.no_cache = 1
    context.title = "管理员移动台"
    context.body_class = "solua-mobile-page"
    view = str(frappe.form_dict.get("view") or "stock").strip()
    context.mobile_order = view == "order"
    context.mobile_customer = view == "customer"
    context.mobile_orders = view == "orders"
    context.mobile_ticket_center = view == "ticket-center"
    context.mobile_sales = view == "sales"
    context.mobile_order_entry = view == "order-entry"
    context.mobile_reports = view == "reports"
    context.mobile_delivery = view == "delivery"
    context.mobile_stock = view == "stock"
    context.desktop_delivery = context.mobile_delivery and str(frappe.form_dict.get("desktop") or "").strip() == "1"
    if context.desktop_delivery:
        context.title = "送货中心"
        context.body_class += " solua-delivery-desktop"
    elif context.mobile_order_entry:
        context.title = "Nova Encomenda"
        context.body_class += " solua-order-entry-page"
    user_label = str(frappe.session.user or "").split("@", 1)[0].replace("_", " ").replace(".", " ").strip()
    user_parts = user_label.split()
    initials = "".join(part[0] for part in user_parts[:2]) if len(user_parts) > 1 else user_label[:2]
    context.mobile_user_initials = (initials or "U").upper()
    roles = set(frappe.get_roles() or [])
    context.mobile_admin = frappe.session.user == "Administrator" or "System Manager" in roles
