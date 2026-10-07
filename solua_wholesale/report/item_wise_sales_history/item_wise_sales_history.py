from frappe.utils import flt

from erpnext.selling.report.item_wise_sales_history.item_wise_sales_history import execute as standard_execute


def execute(filters=None):
    columns, data, message, chart = standard_execute(filters or {})
    data = sorted(
        data,
        key=lambda row: (
            -flt(row.get("quantity")),
            -flt(row.get("amount")),
            str(row.get("item_code") or ""),
        ),
    )
    return columns, data, message, chart
