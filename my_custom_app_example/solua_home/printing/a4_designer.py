"""Small Jinja data adapter shared by the A4 designer and its Print Formats."""

import json

import frappe


def _number(value):
	try:
		return float(value or 0)
	except (TypeError, ValueError):
		return 0.0


def _price_difference_totals(doc, price_difference):
	"""Add display totals without changing the stored transaction snapshot."""
	data = dict(price_difference)
	difference = _number(data.get("difference_total"))
	if doc.doctype == "Sales Invoice" and data.get("original_document"):
		try:
			original = frappe.get_doc("Sales Invoice", data["original_document"])
			old_total = _number(original.get("grand_total"))
		except Exception:
			old_total = _number(data.get("old_total"))
		new_total = old_total - difference
	else:
		new_total = _number(data.get("new_total")) or _number(doc.get("grand_total"))
		old_total = _number(data.get("old_total")) or new_total + difference
	data["old_total"] = old_total
	data["new_total"] = new_total
	refund = data.get("refund_amount")
	if refund is not None:
		data["difference_discount"] = max(difference - _number(refund), 0.0)
	return data


def get_a4_print_data(doc, live=False):
	from solua_home.printing.wholesale import get_company_print_info, get_customer_print_info, get_pick_list_print_data, get_wholesale_print_data
# Keep this module import-free at module scope; lazy-import inside the function only when needed.

	data = get_pick_list_print_data(doc) if doc.doctype == "Pick List" else get_wholesale_print_data(doc, live=live)
	# 公司抬头统一走 get_company_print_info：已提交单据的打印快照存于 logo 功能之前，
	# 快照里的 company 只有 name/nuit/address/phone；而设计器模板会隐藏共享 logo，
	# 缺了 logo 整张单据就没有公司标识（草稿单据不走快照反而正常，所以容易漏测）。
	data["company"] = get_company_print_info(doc, use_snapshot=not live) or data.get("company") or {}
	if not isinstance(data.get("customer"), dict) and hasattr(doc, "get"):
		data["customer"] = get_customer_print_info(doc, use_snapshot=not live)
	for row in data.get("items", []):
		item = frappe.db.get_value("Item", row.get("item_code"), ["custom_spu_code", "variant_of", "image", "custom_swatch_image"], as_dict=True) or {}
		row["spu"] = item.get("custom_spu_code") or ""
		if not row["spu"] and item.get("variant_of"):
			row["spu"] = frappe.db.get_value("Item", item.variant_of, "custom_spu_code") or ""
		image = row.get("image") or item.get("image") or item.get("custom_swatch_image") or ""
		row["image"] = image if image.startswith(("/files/", "/private/files/", "http://", "https://", "data:")) else ""
	# Price-difference layouts use a structured snapshot so the editable A4
	# template can render old/new prices without parsing stored HTML.
	raw_difference = doc.get("custom_price_difference_detail_json") if hasattr(doc, "get") else None
	if raw_difference:
		try:
			price_difference = json.loads(raw_difference) if isinstance(raw_difference, str) else raw_difference
		except (TypeError, ValueError):
			price_difference = None
		if isinstance(price_difference, dict):
			data["price_difference"] = _price_difference_totals(doc, price_difference)
	return data
