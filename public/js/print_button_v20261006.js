(() => {
	if (typeof frappe === "undefined" || !frappe.ui?.form?.on) return;
	const PDF_API = "/api/method/solua_home.api.export.download_pdf";

	const openCompressedPdf = (frm) => {
		const params = new URLSearchParams({ doctype: frm.doctype, name: frm.doc.name });
		window.open(`${PDF_API}?${params.toString()}`, "_blank");
	};

	["Sales Order", "Sales Invoice", "Delivery Note", "Pick List"].forEach((doctype) => {
		frappe.ui.form.on(doctype, {
			refresh(frm) {
				if (frm.is_new() || !frm.doc?.name || frm.__solua_native_print_button) return;
				frm.__solua_native_print_button = true;
				frm.add_custom_button(__("打印"), () => openCompressedPdf(frm), __("打印"));
			},
		});
	});
})();
