"""Small overrides for submitted child-item updates."""

import frappe

from erpnext.controllers.accounts_controller import update_child_qty_rate as native_update_child_qty_rate


def _items(value):
	return frappe.parse_json(value) if isinstance(value, str) else (value or [])


@frappe.whitelist()
def update_child_qty_rate(parent_doctype, trans_items, parent_doctype_name, child_docname="items"):
	data = _items(trans_items)
	if parent_doctype != "Sales Order" or not any("additional_notes" in row or "pos_additional_notes" in row for row in data):
		return native_update_child_qty_rate(parent_doctype, trans_items, parent_doctype_name, child_docname)

	before = frappe.get_doc(parent_doctype, parent_doctype_name)
	before_names = {row.name for row in before.get(child_docname) or []}
	native_update_child_qty_rate(parent_doctype, trans_items, parent_doctype_name, child_docname)

	after = frappe.get_doc(parent_doctype, parent_doctype_name)
	by_name = {row.name: row for row in after.get(child_docname) or []}
	new_by_code = {}
	for row in after.get(child_docname) or []:
		if row.name not in before_names:
			new_by_code.setdefault(row.item_code, []).append(row)

	for row in data:
		if "additional_notes" not in row:
			continue
		target = by_name.get(row.get("docname"))
		if not target and row.get("item_code"):
			candidates = new_by_code.get(row["item_code"], [])
			target = candidates.pop(0) if candidates else None
		if not target:
			continue
		note = row["additional_notes"] if "additional_notes" in row else row.get("pos_additional_notes") or ""
		fields = ["additional_notes"]
		if frappe.get_meta("Sales Order Item").has_field("pos_additional_notes"):
			fields.append("pos_additional_notes")
		for fieldname in fields:
			if getattr(target, fieldname, None) != note:
				frappe.db.set_value("Sales Order Item", target.name, fieldname, note)
