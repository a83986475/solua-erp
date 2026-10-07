import frappe


def execute():
	"""Point the standard report at Solua's accounting-aware implementation."""
	report = frappe.db.get_value(
		"Report",
		"Profitability Analysis",
		["module", "report_type", "is_standard"],
		as_dict=True,
	)
	if not report or report.module == "Solua Wholesale":
		return
	if report.report_type != "Script Report" or report.is_standard != "Yes":
		frappe.throw("Profitability Analysis is not the expected standard Script Report")
	if report.module != "Accounts":
		frappe.throw("Unexpected Profitability Analysis module: " + str(report.module))
	frappe.db.set_value("Report", "Profitability Analysis", "module", "Solua Wholesale", update_modified=False)
	frappe.clear_cache()
