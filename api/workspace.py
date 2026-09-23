"""Desk workspace visibility for the Solua Home production UI."""

import frappe


HIDDEN_WORKSPACES = {"Manufacturing", "Projects", "Quality", "Subcontracting"}


@frappe.whitelist()
def get_workspaces():
	"""Hide unused factory workspaces from Desk without changing permissions."""
	from frappe.desk.desktop import get_workspaces as get_standard_workspaces

	workspaces = get_standard_workspaces()
	if frappe.session.user == "Administrator":
		return workspaces

	workspaces["pages"] = [
		page for page in workspaces.get("pages", []) if page.get("name") not in HIDDEN_WORKSPACES
	]
	return workspaces
