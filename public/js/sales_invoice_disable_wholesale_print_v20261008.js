(() => {
	if (typeof frappe === "undefined" || !frappe.ui?.form?.on) return;

	frappe.ui.form.on("Sales Invoice", {
		refresh(frm) {
			if (frm.is_new() || !frm.doc?.name) return;
			frm.remove_custom_button?.(__("批发销售单"), __("打印"));
		},
	});
})();
