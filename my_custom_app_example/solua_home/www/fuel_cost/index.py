import frappe


def get_context(context):
    context.no_cache = 1
    context.title = "运输成本计算器 | SOLUA HOME"
    context.language = "zh"
