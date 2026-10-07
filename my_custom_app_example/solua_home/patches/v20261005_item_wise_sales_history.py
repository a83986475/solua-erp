import frappe


def execute():
	"""Place the standard item-wise sales report in the Solua Wholesale sidebar."""
	report = frappe.db.get_value(
		"Report",
		"Item-wise Sales History",
		["module", "report_type", "is_standard"],
		as_dict=True,
	)
	if not report or report.module == "Solua Wholesale":
		return
	if report.report_type != "Script Report" or report.is_standard != "Yes":
		frappe.throw("Item-wise Sales History is not the expected standard report")
	if report.module != "Selling":
		frappe.throw("Unexpected Item-wise Sales History module: " + str(report.module))
	frappe.db.set_value("Report", "Item-wise Sales History", "module", "Solua Wholesale", update_modified=False)
	frappe.clear_cache()
