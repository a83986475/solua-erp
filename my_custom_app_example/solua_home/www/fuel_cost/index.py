import frappe


def get_context(context):
    context.no_cache = 1
    context.title = "车辆油耗与运输成本 | SOLUA HOME"
    context.language = "zh"
