import frappe
from frappe.sessions import get_csrf_token


def get_context(context):
    context.csrf_token = get_csrf_token()
    context.no_cache = 1
    context.title = "车辆油耗与运输成本 | SOLUA HOME"
    context.language = "zh"
