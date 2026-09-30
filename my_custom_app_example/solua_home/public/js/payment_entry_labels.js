function apply_payment_entry_labels(frm) {
	const labels = {
		transaction_references: "Transaction Reference",
		reference_no: "Payment Reference No",
		reference_date: "Payment Reference Date",
	};

	for (const [fieldname, label] of Object.entries(labels)) {
		const translated = __(label);
		frm?.set_df_property?.(fieldname, "label", translated);
		const selector = `[data-fieldname="${fieldname}"] ${fieldname === "transaction_references" ? ".section-head" : ".control-label"}`;
		const node = document.querySelector(selector);
		const textNode = [...(node?.childNodes || [])].find((child) => child.nodeType === Node.TEXT_NODE);
		if (textNode) textNode.nodeValue = translated;
	}
	}
}

frappe.ui.form.on("Payment Entry", {
	onload_post_render: apply_payment_entry_labels,
	refresh: apply_payment_entry_labels,
});

apply_payment_entry_labels(
	typeof cur_frm !== "undefined" ? cur_frm : frappe.ui.form.get_opened?.()
);
setTimeout(() => apply_payment_entry_labels(), 0);
