"""Keep the display precision of active sales and stock quantities at zero."""

import frappe


QUANTITY_FIELDS = {
	"Sales Invoice": ("total_qty",),
	"Sales Invoice Item": ("qty", "stock_qty", "delivered_qty", "actual_qty"),
	"Sales Order": ("total_qty",),
	"Sales Order Item": ("qty", "stock_qty", "delivered_qty", "picked_qty", "returned_qty"),
	"Quotation": ("total_qty",),
	"Quotation Item": ("qty", "stock_qty"),
	"Delivery Note": ("total_qty",),
	"Delivery Note Item": ("qty", "stock_qty", "returned_qty", "packed_qty", "received_qty", "installed_qty"),
	"Stock Entry Detail": ("qty", "transfer_qty", "actual_qty", "transferred_qty"),
	"Pick List": ("for_qty",),
	"Pick List Item": ("qty", "picked_qty", "stock_qty", "delivered_qty", "transferred_qty"),
	"Stock Reconciliation Item": ("qty", "current_qty"),
	"POS Invoice": ("total_qty",),
	"POS Invoice Item": ("qty", "stock_qty", "delivered_qty"),
	"Item": ("custom_stock_qty", "custom_variant_stock_qty"),
}


def ensure_quantity_precision():
	"""Create or update only the listed DocField precision overrides."""
	for doctype, fieldnames in QUANTITY_FIELDS.items():
		meta = frappe.get_meta(doctype)
		for fieldname in fieldnames:
			field = meta.get_field(fieldname)
			if not field or field.fieldtype != "Float":
				continue
			name = frappe.db.get_value(
				"Property Setter",
				{"doc_type": doctype, "field_name": fieldname, "property": "precision", "doctype_or_field": "DocField"},
				"name",
			)
			if name:
				setter = frappe.get_doc("Property Setter", name)
				if str(setter.value) != "0":
					setter.value = "0"
					setter.save(ignore_permissions=True)
			else:
				frappe.make_property_setter({
					"doctype": doctype,
					"doctype_or_field": "DocField",
					"fieldname": fieldname,
					"property": "precision",
					"value": "0",
					"property_type": "Int",
				})
		frappe.clear_cache(doctype=doctype)
