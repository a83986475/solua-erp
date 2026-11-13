import frappe
from frappe.desk.query_report import get_report_doc, get_report_result

from solua_home.api.receivable_store import STORE_FIELD, get_invoice_stores


BASE_REPORT = "Accounts Receivable"
REPORT_NAME = "Solua Accounts Receivable"
CUSTOM_REPORT = "应收账款"


def store_column():
    return {"fieldname": STORE_FIELD, "label": "门店名称", "fieldtype": "Data", "width": 140}


def add_store_column(columns):
    if any(column.get("fieldname") == STORE_FIELD for column in columns):
        return
    index = next((index for index, column in enumerate(columns) if column.get("fieldname") == "party"), None)
    columns.insert(index + 1 if index is not None else len(columns), store_column())


def execute(filters=None):
    columns, rows, *extras = get_report_result(get_report_doc(BASE_REPORT), filters)
    add_store_column(columns)
    names = {
        row["voucher_no"] for row in rows
        if row.get("voucher_type") == "Sales Invoice" and row.get("voucher_no")
    }
    stores = get_invoice_stores(names)
    for row in rows:
        if row.get("voucher_type") == "Sales Invoice" and row.get("voucher_no"):
            row[STORE_FIELD] = stores.get(row["voucher_no"]) or "未指定门店"
    return columns, rows, *extras
