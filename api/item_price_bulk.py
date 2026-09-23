"""Preview and update a template's base Item Price across enabled variants."""

import frappe
from frappe import _
from frappe.utils import flt

ALLOWED_ROLES = ("System Manager", "Stock Manager", "Item Manager", "Sales Manager", "Accounts Manager")


def _check_access():
	frappe.only_for(ALLOWED_ROLES)
	if not frappe.has_permission("Item Price", "write"):
		frappe.throw(_("You do not have permission to update Item Price."), frappe.PermissionError)


def _get_plan(item_code, price_list):
	if not item_code or not price_list:
		frappe.throw(_("Select an Item or Item template and Price List."))

	parent = frappe.get_doc("Item", item_code)
	if parent.disabled:
		frappe.throw(_("{0} is disabled.").format(item_code))

	pl = frappe.get_doc("Price List", price_list)
	if not pl.enabled:
		frappe.throw(_("Price List {0} is disabled.").format(price_list))

	if parent.has_variants:
		items = frappe.get_all(
			"Item",
			filters={"variant_of": item_code, "disabled": 0, "is_sales_item": 1},
			fields=["name", "item_name", "stock_uom"],
			order_by="name asc",
		)
		item_type = "template"
	else:
		if not parent.is_sales_item:
			frappe.throw(_("{0} is not enabled for sales.").format(item_code))
		items = [{"name": parent.name, "item_name": parent.item_name, "stock_uom": parent.stock_uom}]
		item_type = "item"
	if not items:
		frappe.throw(_("This template has no enabled sales variants."))

	plan = []
	blocked = []
	for item in items:
		rows = frappe.get_all(
			"Item Price",
			filters={"item_code": item["name"], "price_list": price_list, "selling": 1},
			fields=["name", "price_list_rate", "currency", "uom", "customer", "supplier", "batch_no"],
		)
		base = [
			row for row in rows
			if not row["customer"] and not row["supplier"] and not row["batch_no"]
			and row["currency"] == pl.currency and row["uom"] == item["stock_uom"]
		]
		if len(base) > 1:
			blocked.append({"item_code": item["name"], "reason": _("Multiple base prices match currency and stock UOM")})
			continue
		plan.append({
			"item_code": item["name"],
			"item_name": item["item_name"],
			"uom": item["stock_uom"],
			"currency": pl.currency,
			"price_name": base[0]["name"] if base else None,
			"old_rate": flt(base[0]["price_list_rate"]) if base else None,
			"state": "existing" if base else "missing",
		})
	return {"item_code": item_code, "item_type": item_type, "price_list": price_list, "currency": pl.currency, "variants": plan, "blocked": blocked}


@frappe.whitelist()
def preview(item_code, price_list):
	"""Return a normal Item or a template's enabled variants and prices, without writes."""
	_check_access()
	return _get_plan(item_code, price_list)


@frappe.whitelist()
def apply(item_code, price_list, new_rate):
	"""Update or create a base Item Price for an Item or each enabled template variant."""
	_check_access()
	new_rate = flt(new_rate)
	if new_rate <= 0:
		frappe.throw(_("Price must be greater than zero."))

	plan = _get_plan(item_code, price_list)
	if plan["blocked"]:
		frappe.throw(_("Some variants have ambiguous prices. Nothing was changed; review the preview."))

	changed = []
	for item in plan["variants"]:
		if item["price_name"]:
			doc = frappe.get_doc("Item Price", item["price_name"])
			doc.price_list_rate = new_rate
			doc.save()
		else:
			doc = frappe.get_doc({
				"doctype": "Item Price",
				"item_code": item["item_code"],
				"price_list": price_list,
				"price_list_rate": new_rate,
				"currency": plan["currency"],
				"uom": item["uom"],
				"selling": 1,
			}).insert()
		changed.append({"item_code": item["item_code"], "item_price": doc.name, "price_list_rate": flt(doc.price_list_rate)})

	return {"item_code": item_code, "item_type": plan["item_type"], "price_list": price_list, "currency": plan["currency"], "updated": len(changed), "items": changed}
