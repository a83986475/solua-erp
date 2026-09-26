"""Small Jinja data adapter shared by the A4 designer and its Print Formats."""

import frappe


def get_a4_print_data(doc):
	from solua_home.printing.wholesale import get_company_print_info, get_pick_list_print_data, get_wholesale_print_data

	data = get_pick_list_print_data(doc) if doc.doctype == "Pick List" else get_wholesale_print_data(doc)
	if doc.doctype == "Pick List":
		data["company"] = get_company_print_info(doc)
	for row in data.get("items", []):
		item = frappe.db.get_value("Item", row.get("item_code"), ["custom_spu_code", "variant_of", "image"], as_dict=True) or {}
		row["spu"] = item.get("custom_spu_code") or ""
		if not row["spu"] and item.get("variant_of"):
			row["spu"] = frappe.db.get_value("Item", item.variant_of, "custom_spu_code") or ""
		image = row.get("image") or item.get("image") or ""
		row["image"] = image if image.startswith(("/files/", "/private/files/")) else ""
	return data
