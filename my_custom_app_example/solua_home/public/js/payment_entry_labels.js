frappe.ui.form.on("Payment Entry", {
	refresh(frm) {
		const labels = {
			transaction_references: "Transaction Reference",
			reference_no: "Payment Reference No",
			reference_date: "Payment Reference Date",
		};

		for (const [fieldname, label] of Object.entries(labels)) {
			frm.set_df_property(fieldname, "label", __(label));
		}
	},
});
