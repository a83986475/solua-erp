// Use available stock (actual minus reserved) for the Sales Order item indicator.
(function () {
	frappe.ui.form.on("Sales Order", {
		setup(frm) {
			frm.set_indicator_formatter("item_code", function (doc) {
				if (!doc.qty && frm.doc.has_unit_price_items) return "yellow";
				const remaining = flt(doc.stock_qty) - flt(doc.delivered_qty);
				const available = flt(doc.actual_qty) - flt(doc.reserved_qty);
				return remaining <= available ? "green" : "orange";
			});
		},
	});
})();
