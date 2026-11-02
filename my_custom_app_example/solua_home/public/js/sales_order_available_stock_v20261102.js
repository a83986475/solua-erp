// Use available stock (actual minus other orders' reservations) for the Sales Order item indicator.
(function () {
	frappe.ui.form.on("Sales Order", {
		setup(frm) {
			frm.set_indicator_formatter("item_code", function (doc) {
				if (!doc.qty && frm.doc.has_unit_price_items) return "yellow";
				const remaining = flt(doc.stock_qty) - flt(doc.delivered_qty);
				const selfReserved = frm.doc.docstatus === 1
					? Math.max(flt(doc.stock_qty) - flt(doc.delivered_qty) * (flt(doc.conversion_factor) || 1), 0)
					: 0;
				const available = flt(doc.actual_qty) - Math.max(flt(doc.reserved_qty) - selfReserved, 0);
				return remaining <= available ? "green" : "orange";
			});
		},
	});
})();
