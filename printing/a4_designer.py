"""Small Jinja data adapter shared by the A4 designer and its Print Formats."""

import frappe


def get_a4_print_data(doc):
	from solua_home.printing.wholesale import get_company_print_info, get_customer_print_info, get_pick_list_print_data, get_wholesale_print_data
# Keep this module import-free at module scope; lazy-import inside the function only when needed.

	data = get_pick_list_print_data(doc) if doc.doctype == "Pick List" else get_wholesale_print_data(doc)
	# 公司抬头统一走 get_company_print_info：已提交单据的打印快照存于 logo 功能之前，
	# 快照里的 company 只有 name/nuit/address/phone；而设计器模板会隐藏共享 logo，
	# 缺了 logo 整张单据就没有公司标识（草稿单据不走快照反而正常，所以容易漏测）。
	data["company"] = get_company_print_info(doc) or data.get("company") or {}
	if not isinstance(data.get("customer"), dict) and hasattr(doc, "get"):
		data["customer"] = get_customer_print_info(doc)
	for row in data.get("items", []):
		item = frappe.db.get_value("Item", row.get("item_code"), ["custom_spu_code", "variant_of", "image", "custom_swatch_image"], as_dict=True) or {}
		row["spu"] = item.get("custom_spu_code") or ""
		if not row["spu"] and item.get("variant_of"):
			row["spu"] = frappe.db.get_value("Item", item.variant_of, "custom_spu_code") or ""
		image = row.get("image") or item.get("image") or item.get("custom_swatch_image") or ""
		row["image"] = image if image.startswith(("/files/", "/private/files/", "http://", "https://", "data:")) else ""
	return data
