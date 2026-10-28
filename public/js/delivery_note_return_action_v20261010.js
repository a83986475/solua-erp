// Keep the submitted return Delivery Note action clear: it creates a credit note, not an exchange document.
(() => {
	if (typeof frappe === "undefined" || !frappe.ui?.form?.on) return;

	const RETURN_LABEL = __("退货发票/贷记单");
	const CREDIT_NOTE_LABELS = new Set([__("Credit Note"), "Credit Note", "换货凭证"]);

	function rename_credit_note_action(frm) {
		if (frm?.doc?.doctype !== "Delivery Note" || frm.doc.docstatus !== 1 || !frm.doc.is_return) return;
		const wrapper = frm.page?.wrapper;
		const root = wrapper?.get?.(0) || wrapper?.[0] || wrapper;
		if (!root?.querySelectorAll) return;

		root.querySelectorAll(".dropdown-menu a.dropdown-item").forEach((link) => {
			const text = link.textContent.trim();
			let data_label = link.dataset?.label || "";
			try { data_label = decodeURIComponent(data_label); } catch (error) { /* keep the raw label */ }
			if (!CREDIT_NOTE_LABELS.has(text) && !CREDIT_NOTE_LABELS.has(data_label)) return;
			link.textContent = RETURN_LABEL;
			if (link.dataset) link.dataset.label = encodeURIComponent(RETURN_LABEL);
			link.title = __("生成退货销售发票（贷记单），不是换货单");
		});
	}

	frappe.ui.form.on("Delivery Note", {
		refresh(frm) {
			rename_credit_note_action(frm);
			setTimeout(() => rename_credit_note_action(frm), 0);
			setTimeout(() => rename_credit_note_action(frm), 200);
		},
	});
})();
