// Register the visible buttons before the larger wholesale-tools script arrives.
(() => {
	const run = (frm, name, ...args) => Promise.resolve(window.solua_home_wholesale_forms_ready)
		.then(() => {
			const action = window.solua_home_wholesale_actions?.[name];
			if (typeof action !== "function") throw new Error("wholesale tools are not ready");
			return action(frm, ...args);
		})
		.catch((error) => frappe.msgprint({
			title: __("工具加载失败"),
			message: error?.message || __("请刷新页面后重试"),
			indicator: "red",
		}));
	const add = (frm, label, name, ...args) => frm.add_custom_button(__(label), () => run(frm, name, ...args), __("工具"));
	const add_print = (frm, label) => frm.add_custom_button(__(label), () => run(frm, "print_wholesale"), __("打印"));

	frappe.ui.form.on("Sales Order", {
		refresh(frm) {
			if (frm.doc.docstatus === 0) {
				add(frm, "按款式条码选颜色", "open_color_picker", "sales_order");
				add(frm, "上传订单表格", "open_sales_order_upload");
				add(frm, "批量添加物料", "open_sales_order_bulk_picker");
				add(frm, "粘贴货号 + 数量", "open_sales_order_paste");
				add(frm, "刷新库存", "refresh_sales_order_stock");
				add(frm, "批量修改数量", "open_sales_order_quantity_update");
			}
			if (!frm.is_new()) add_print(frm, "客户订单确认单");
		},
	});

	frappe.ui.form.on("Stock Entry", {
		refresh(frm) {
			["按款式条码选颜色", "上传物料表格", "批量添加物料", "粘贴货号 + 数量", "刷新库存"].forEach((label) => frm.remove_custom_button?.(__(label), __("工具")));
			if (frm.doc.docstatus !== 0) return;
			add(frm, "按款式条码选颜色", "open_color_picker", "stock_entry");
			add(frm, "上传物料表格", "open_sales_order_upload");
			add(frm, "批量添加物料", "open_sales_order_bulk_picker");
			add(frm, "粘贴货号 + 数量", "open_sales_order_paste");
			add(frm, "刷新库存", "refresh_sales_order_stock");
		},
	});
	frappe.ui.form.on("Delivery Note", {
		refresh(frm) { if (!frm.is_new()) add_print(frm, "Guia de Remessa"); },
	});
	frappe.ui.form.on("Pick List", {
		refresh(frm) { if (!frm.is_new()) add_print(frm, "拣货单"); },
	});
	frappe.ui.form.on("Purchase Receipt", {
		refresh(frm) { if (frm.doc.docstatus === 0) add(frm, "按色扫码收货", "open_color_picker", "receipt"); },
	});
	frappe.ui.form.on("Stock Reconciliation", {
		refresh(frm) { if (frm.doc.docstatus === 0) add(frm, "手机扫码盘点", "open_color_picker", "reconciliation"); },
	});

	if (typeof window !== "undefined") window.solua_home_wholesale_button_shell = true;
})();
