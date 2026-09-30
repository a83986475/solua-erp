function apply_payment_entry_labels(frm) {
	if (!frm || frm.doctype !== "Payment Entry") return;

	const labels = {
		transaction_references: "Transaction Reference",
		reference_no: "Payment Reference No",
		reference_date: "Payment Reference Date",
	};

	for (const [fieldname, label] of Object.entries(labels)) {
		frm.set_df_property(fieldname, "label", __(label));
	}
}

frappe.ui.form.on("Payment Entry", {
	onload_post_render: apply_payment_entry_labels,
	refresh: apply_payment_entry_labels,
});

apply_payment_entry_labels(
	typeof cur_frm !== "undefined" ? cur_frm : frappe.ui.form.get_opened?.()
);
