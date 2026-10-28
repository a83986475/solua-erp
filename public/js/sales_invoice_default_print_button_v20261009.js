(() => {
	if (typeof frappe === "undefined" || !frappe.ui?.form?.on) return;

	frappe.ui.form.on("Sales Invoice", {
		refresh(frm) {
			if (frm.is_new() || !frm.doc?.name) return;
			frm.remove_custom_button?.(__("批发销售单"), __("打印"));
			frm.remove_custom_button?.(__("打印销售发票"), __("打印"));
			frm.add_custom_button(__("打印销售发票"), () => {
				const saved = window.solua_home_print_preferences?.read(frm.doctype) || {};
				const fallback = (fieldname, value) => Object.prototype.hasOwnProperty.call(saved, fieldname) ? saved[fieldname] : value;
				const dialog = new frappe.ui.Dialog({
				title: __("打印销售发票选项"),
					fields: [
						{ fieldname: "show_item_name", label: __("显示商品名称"), fieldtype: "Check", default: fallback("show_item_name", frm.doc.custom_print_item_name == null ? 1 : frm.doc.custom_print_item_name) },
						{ fieldname: "show_sku", label: __("显示 SKU/货号"), fieldtype: "Check", default: fallback("show_sku", frm.doc.custom_print_sku == null ? 1 : frm.doc.custom_print_sku) },
						{ fieldname: "show_color", label: __("显示颜色"), fieldtype: "Check", default: fallback("show_color", (frm.doc.custom_print_color_code || frm.doc.custom_print_cor) ? 1 : 0) },
						{ fieldname: "merge_order_code", label: __("合并同款对外货号"), fieldtype: "Check", default: fallback("merge_order_code", frm.doc.custom_print_merge_order_code ? 1 : 0) },
						{ fieldname: "show_description", label: __("显示商品描述"), fieldtype: "Check", default: fallback("show_description", frm.doc.custom_print_description == null ? 1 : frm.doc.custom_print_description) },
						{ fieldname: "show_images", label: __("显示颜色图片"), fieldtype: "Check", default: fallback("show_images", frm.doc.custom_print_color_images ? 1 : 0) },
						{ fieldname: "show_qr", label: __("显示色卡二维码"), fieldtype: "Check", default: fallback("show_qr", frm.doc.custom_print_color_qr ? 1 : 0) },
					],
					primary_action_label: __("保存并打开预览"),
					primary_action(values) {
						const print_values = {
							custom_print_item_name: values.show_item_name ? 1 : 0,
							custom_print_sku: values.show_sku ? 1 : 0,
							custom_print_color_code: values.show_color ? 1 : 0,
							custom_print_cor: values.show_color ? 1 : 0,
							custom_print_merge_order_code: values.merge_order_code ? 1 : 0,
							custom_print_description: values.show_description ? 1 : 0,
							custom_print_color_images: values.show_images ? 1 : 0,
							custom_print_color_qr: values.show_qr ? 1 : 0,
						};
						const save = frm.doc.docstatus === 1
							? frappe.call({ method: "frappe.client.set_value", args: { doctype: frm.doctype, name: frm.doc.name, fieldname: print_values } }).then(() => frm.reload_doc())
							: frm.set_value(print_values).then(() => frm.save());
						save.then(() => {
							const params = new URLSearchParams({ doctype: "Sales Invoice", name: frm.doc.name, no_letterhead: "0", trigger_print: "1" });
							window.open(`/printview?${params.toString()}`, "_blank");
							window.solua_home_print_preferences?.save(frm.doctype, values);
							dialog.hide();
						});
					},
				});
				dialog.show();
			}, __("打印"));
		},
	});
})();
