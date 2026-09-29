import frappe


def get_context(context):
    context.no_cache = 1
    context.title = "WhatsApp 收件箱"
    context.whatsapp_user = frappe.session.user
