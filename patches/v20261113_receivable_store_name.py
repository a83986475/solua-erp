import frappe

from solua_home.solua_wholesale.report.solua_accounts_receivable.solua_accounts_receivable import (
    BASE_REPORT,
    CUSTOM_REPORT,
    REPORT_NAME,
    add_store_column,
)


def execute():
    if not frappe.db.exists("Report", CUSTOM_REPORT):
        return

    report = frappe.get_doc("Report", CUSTOM_REPORT)
    if report.report_type != "Custom Report" or report.reference_report not in (BASE_REPORT, REPORT_NAME):
        return

    settings = frappe.parse_json(report.json or "{}") or {}
    columns = settings.get("columns")
    previous_columns = list(columns or ())
    if columns:
        add_store_column(columns)
    if report.reference_report != REPORT_NAME or (columns and columns != previous_columns):
        report.reference_report = REPORT_NAME
        report.json = frappe.as_json(settings)
        report.save(ignore_permissions=True)
