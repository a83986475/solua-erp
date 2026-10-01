// Sales Order list: keep the native merged print and add a separate-PDF download.
(() => {
	frappe.provide("frappe.listview_settings");
	const previous = frappe.listview_settings["Sales Order"] || {};
	const previous_onload = previous.onload;

	frappe.listview_settings["Sales Order"] = Object.assign({}, previous, {
		onload(listview) {
			if (typeof previous_onload === "function") previous_onload.call(this, listview);
			listview.page.add_action_item(__("分别下载订单 PDF"), () => {
				const names = listview.get_checked_items(true) || [];
				if (!names.length) {
					frappe.msgprint(__("请先选择销售订单"));
					return;
				}
				const query = new URLSearchParams({ names: JSON.stringify(names) });
				window.open(`/api/method/solua_home.api.export.download_sales_order_pdfs?${query}`, "_blank");
			});
		},
	});
})();
