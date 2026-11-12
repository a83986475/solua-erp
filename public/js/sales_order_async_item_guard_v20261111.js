// Prevent Sales Order item-detail responses from replacing edits made while the request is pending.
(() => {
	if (frappe.call.__solua_sales_order_item_guard) return;

	const nativeCall = frappe.call;
	function isSalesOrderItemRequest(options) {
		const method = typeof options === "string" ? options : options?.method;
		return method === "process_item_selection"
			|| method === "solua_home.api.sales.get_sales_order_item_display"
			|| method === "erpnext.stock.utils.get_incoming_rate"
			|| method?.startsWith("erpnext.stock.get_item_details.")
			|| method?.startsWith("erpnext.accounts.doctype.pricing_rule.pricing_rule.");
	}

	function setPending(frm, pending) {
		const field = frm.fields_dict?.items;
		const wrapper = field?.$wrapper;
		if (!wrapper) return;

		if (pending) {
			if (!frm.__solua_item_request_count) {
				wrapper.attr("aria-busy", "true").prop("inert", true);
				wrapper.find(".solua-item-request-status").remove();
				wrapper.before(
					$('<div class="solua-item-request-status text-muted small" role="status"></div>')
						.text(__("商品信息加载中，请稍候…"))
				);
				frm.disable_save?.();
			}
			frm.__solua_item_request_count = (frm.__solua_item_request_count || 0) + 1;
			return;
		}

		frm.__solua_item_request_count = Math.max(0, (frm.__solua_item_request_count || 1) - 1);
		if (frm.__solua_item_request_count) return;
		wrapper.removeAttr("aria-busy").prop("inert", false);
		wrapper.prev(".solua-item-request-status").remove();
		frm.enable_save?.();
	}

	frappe.call = function (...args) {
		const options = args[0];
		const frm = typeof cur_frm !== "undefined" ? cur_frm : window.cur_frm;
		const guarded = frm?.doctype === "Sales Order"
			&& frm.doc.docstatus === 0
			&& isSalesOrderItemRequest(options);
		if (!guarded) return nativeCall.apply(this, args);

		setPending(frm, true);
		try {
			return Promise.resolve(nativeCall.apply(this, args)).finally(() => setPending(frm, false));
		} catch (error) {
			setPending(frm, false);
			throw error;
		}
	};
	frappe.call.__solua_sales_order_item_guard = true;
})();
