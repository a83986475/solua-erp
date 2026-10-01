// Sales Order / Delivery Note / Pick List lists: add separate-PDF downloads.
(() => {
	frappe.provide("frappe.listview_settings");
	const CONFIG = {
		"Sales Order": ["分别下载订单 PDF", "请先选择销售订单"],
		"Delivery Note": ["分别下载交货单 PDF", "请先选择交货单"],
		"Pick List": ["分别下载拣货单 PDF", "请先选择拣货单"],
	};

	Object.entries(CONFIG).forEach(([doctype, [action_label, empty_message]]) => {
		const previous = frappe.listview_settings[doctype] || {};
		const previous_onload = previous.onload;
		frappe.listview_settings[doctype] = Object.assign({}, previous, {
			onload(listview) {
				if (typeof previous_onload === "function") previous_onload.call(this, listview);
				listview.page.add_action_item(__(action_label), () => {
					const names = listview.get_checked_items(true) || [];
					if (!names.length) {
						frappe.msgprint(__(empty_message));
						return;
					}
					const query = new URLSearchParams({ doctype, names: JSON.stringify(names) });
					window.open(`/api/method/solua_home.api.export.download_document_pdfs?${query}`, "_blank");
				});
			},
		});
	});
})();
