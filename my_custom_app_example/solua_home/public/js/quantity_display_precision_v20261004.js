// Display active sales/stock quantities without decimal places; stored values are unchanged.
(function () {
	"use strict";
	if (window.__solua_qty_display_precision) return;
	window.__solua_qty_display_precision = true;

	const roundForDisplay = (value) => {
		const number = Number(value);
		return Number.isFinite(number) ? Math.sign(number) * Math.round(Math.abs(number)) : value;
	};
	const reportFields = {
		"Item-wise Sales History": new Set(["quantity", "delivered_quantity"]),
		"Sales Order Analysis": new Set(["qty", "delivered_qty", "pending_qty", "billed_qty", "qty_to_bill"]),
		"Item-wise Sales Register": new Set(["stock_qty"]),
		"Stock Balance": new Set(["bal_qty", "opening_qty", "in_qty", "out_qty", "reserved_stock", "alt_uom_bal_qty"]),
		"Stock Ledger": new Set(["in_qty", "out_qty", "qty_after_transaction"]),
		"Template Stock Tree": new Set(["actual_qty", "reserved_qty", "available_qty"]),
	};

	function patchReport(name, settings) {
		const fields = reportFields[name];
		if (!fields || !settings || settings.__solua_qty_precision) return settings;
		const oldFormatter = settings.formatter;
		settings.formatter = function (value, row, column, data, defaultFormatter) {
			if (column && fields.has(column.fieldname)) {
				value = roundForDisplay(value);
				column.precision = "0";
			}
			return typeof oldFormatter === "function"
				? oldFormatter.call(this, value, row, column, data, defaultFormatter)
				: defaultFormatter(value, row, column, data);
		};
		settings.__solua_qty_precision = true;
		return settings;
	}

	if (frappe.query_reports && typeof Proxy === "function") {
		const reports = frappe.query_reports;
		Object.keys(reports).forEach((name) => { reports[name] = patchReport(name, reports[name]); });
		frappe.query_reports = new Proxy(reports, {
			set(target, name, settings) {
				Reflect.set(target, name, patchReport(name, settings));
				return true;
			},
		});
	}

	const formFields = {
		"Sales Invoice": { parent: ["total_qty"], child: ["qty", "stock_qty", "delivered_qty", "actual_qty"] },
		"Sales Order": { parent: ["total_qty"], child: ["qty", "stock_qty", "delivered_qty", "picked_qty", "returned_qty"] },
		Quotation: { parent: ["total_qty"], child: ["qty", "stock_qty"] },
		"Delivery Note": { parent: ["total_qty"], child: ["qty", "stock_qty", "returned_qty", "packed_qty", "received_qty", "installed_qty"] },
		"Stock Entry": { parent: [], child: ["qty", "transfer_qty", "actual_qty", "transferred_qty"] },
		"Pick List": { parent: ["for_qty"], child: ["qty", "picked_qty", "stock_qty", "delivered_qty", "transferred_qty"] },
		"Stock Reconciliation": { parent: [], child: ["qty", "current_qty"] },
		"POS Invoice": { parent: ["total_qty"], child: ["qty", "stock_qty", "delivered_qty"] },
	};
	function setFieldPrecision(field) {
		const df = field && (field.df || field);
		if (df && df.fieldtype === "Float") df.precision = "0";
	}

	Object.keys(formFields).forEach((doctype) => {
		frappe.ui.form.on(doctype, {
			refresh(frm) {
				const fields = formFields[doctype];
				for (const name of fields.parent) setFieldPrecision((frm.meta.fields || []).find((field) => field.fieldname === name));
				for (const field of Object.values(frm.fields_dict || {})) {
					if (field.df && field.df.fieldtype === "Table" && field.grid) {
						for (const name of fields.child) {
							setFieldPrecision(field.grid.get_field(name));
						}
					}
				}
			},
		});
	});

	window.solua_home_quantity_display = { roundForDisplay, reportFields };
})();
