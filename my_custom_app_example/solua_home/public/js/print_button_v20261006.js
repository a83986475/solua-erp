(() => {
	if (typeof frappe === "undefined" || !frappe.ui?.form?.on) return;

	["Sales Order", "Sales Invoice", "Delivery Note", "Pick List"].forEach((doctype) => {
		frappe.ui.form.on(doctype, {
			refresh(frm) {
				if (frm.is_new() || !frm.doc?.name || frm.__solua_native_print_button) return;
				frm.__solua_native_print_button = true;
				frm.add_custom_button(__("打印"), () => frm.print_doc(), __("打印"));
			},
		});
	});
})();
