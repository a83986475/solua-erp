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

const CASH_DISCOUNT_TERM = "PRONTO PAGAMENTO";
const CASH_DISCOUNT_RATE = 3;
const CASH_DISCOUNT_ACCOUNT = "Discount Allowed - SH";
const CASH_DISCOUNT_COST_CENTER = "Main - SH";

function calculate_pronto_pagamento(gross, rate = CASH_DISCOUNT_RATE) {
	const total = Number(gross) || 0;
	const discount = Math.round(((total * rate) / 100) * 100) / 100;
	return { discount, net: Math.round((total - discount) * 100) / 100 };
}

function clear_pronto_pagamento(frm) {
	if (!frm.__solua_cash_discount_applied) return;
	frm.doc.deductions = (frm.doc.deductions || []).filter(
		(row) => row.account !== CASH_DISCOUNT_ACCOUNT,
	);
	frm.__solua_cash_discount_applied = false;
	frm.events.set_unallocated_amount(frm);
	frm.refresh_field("deductions");
}

function apply_pronto_pagamento(frm) {
	if (!frm?.doc) return;
	if (
		frm.doc.custom_payment_term !== CASH_DISCOUNT_TERM ||
		(frm.doc.mode_of_payment && frm.doc.mode_of_payment !== "Cash")
	) {
		clear_pronto_pagamento(frm);
		return;
	}
	const references = (frm.doc.references || []).filter((row) => row.reference_doctype === "Sales Invoice");
	const gross = references.reduce((sum, row) => sum + flt(row.allocated_amount), 0);
	if (!gross) {
		clear_pronto_pagamento(frm);
		return;
	}
	if (
		frm.doc.paid_from_account_currency &&
		frm.doc.paid_to_account_currency &&
		frm.doc.paid_from_account_currency !== frm.doc.paid_to_account_currency
	) {
		clear_pronto_pagamento(frm);
		return;
	}
	const { discount, net } = calculate_pronto_pagamento(gross);
	const rate = frm.doc.payment_type === "Pay" ? flt(frm.doc.target_exchange_rate) || 1 : flt(frm.doc.source_exchange_rate) || 1;

	// Same-currency cash is the supported business case; direct assignment avoids ERPNext reallocating references to net cash.
	frm.doc.paid_amount = net;
	frm.doc.received_amount = net;
	frm.doc.base_paid_amount = flt(net * (flt(frm.doc.source_exchange_rate) || 1), 2);
	frm.doc.base_received_amount = flt(net * (flt(frm.doc.target_exchange_rate) || 1), 2);
	frm.doc.total_allocated_amount = flt(gross, 2);
	frm.doc.base_total_allocated_amount = flt(gross * rate, 2);
	frm.doc.deductions = (frm.doc.deductions || []).filter((row) => row.account !== CASH_DISCOUNT_ACCOUNT);
	const deduction = frm.add_child("deductions");
	deduction.account = CASH_DISCOUNT_ACCOUNT;
	deduction.cost_center = CASH_DISCOUNT_COST_CENTER;
	deduction.amount = discount;
	deduction.description = "PRONTO PAGAMENTO 3%";
	frm.__solua_cash_discount_applied = true;
	frm.events.set_unallocated_amount(frm);
	frm.refresh_fields(["paid_amount", "received_amount", "deductions", "total_allocated_amount"]);
}

if (typeof module !== "undefined" && module.exports) {
	module.exports = { calculate_pronto_pagamento };
}

if (typeof frappe !== "undefined") {
	frappe.ui.form.on("Payment Entry", {
		onload_post_render: apply_payment_entry_labels,
		refresh(frm) {
			apply_payment_entry_labels(frm);
			apply_pronto_pagamento(frm);
		},
		custom_payment_term: apply_pronto_pagamento,
		mode_of_payment: apply_pronto_pagamento,
	});

	frappe.ui.form.on("Payment Entry Reference", {
		allocated_amount: apply_pronto_pagamento,
		references_remove: apply_pronto_pagamento,
	});

	apply_payment_entry_labels(
		typeof cur_frm !== "undefined" ? cur_frm : frappe.ui.form.get_opened?.()
	);
	setTimeout(() => apply_payment_entry_labels(), 0);
}
