// solua_home: 批发销售单的图片、二维码及列显示独立开关。

frappe.ui.form.on("Sales Invoice", {
	refresh(frm) {
		if (frm.is_new() || frm.__solua_wholesale_print_button) return;
		frm.__solua_wholesale_print_button = true;

		frm.add_custom_button(__("批发销售单"), () => {
			const dialog = new frappe.ui.Dialog({
				title: __("批发销售单打印选项"),
			fields: [
				{
					fieldname: "show_item_name",
					label: __("显示商品名称"),
					fieldtype: "Check",
					default: frm.doc.custom_print_item_name == null ? 1 : frm.doc.custom_print_item_name,
				},
				{
					fieldname: "show_sku",
					label: __("显示 SKU/货号"),
					fieldtype: "Check",
					default: frm.doc.custom_print_sku == null ? 1 : frm.doc.custom_print_sku,
				},
				{
					fieldname: "show_color_code",
					label: __("显示色号"),
					fieldtype: "Check",
					default: frm.doc.custom_print_color_code == null ? 1 : frm.doc.custom_print_color_code,
				},
				{
					fieldname: "show_description",
					label: __("显示商品描述"),
					fieldtype: "Check",
					default: frm.doc.custom_print_description == null ? 1 : frm.doc.custom_print_description,
				},
				{
						fieldname: "show_images",
						label: __("显示颜色图片"),
						fieldtype: "Check",
						default: frm.doc.custom_print_color_images ? 1 : 0,
					},
					{
						fieldname: "show_qr",
						label: __("显示色卡二维码"),
						fieldtype: "Check",
						default: frm.doc.custom_print_color_qr ? 1 : 0,
					},
				],
				primary_action_label: __("保存并打开预览"),
				primary_action(values) {
					const save = frm.set_value({
						custom_print_item_name: values.show_item_name ? 1 : 0,
						custom_print_sku: values.show_sku ? 1 : 0,
						custom_print_color_code: values.show_color_code ? 1 : 0,
						custom_print_description: values.show_description ? 1 : 0,
						custom_print_color_images: values.show_images ? 1 : 0,
						custom_print_color_qr: values.show_qr ? 1 : 0,
					});
					save.then(() => frm.save(frm.doc.docstatus === 1 ? "Update" : undefined)).then(() => {
						const params = new URLSearchParams({
							doctype: "Sales Invoice",
							name: frm.doc.name,
							format: "批发销售单（颜色版）",
							no_letterhead: "0",
							trigger_print: "1",
						});
						window.open(`/printview?${params.toString()}`, "_blank");
						dialog.hide();
					});
				},
			});
			dialog.show();
		}, __("打印"));
	},
});
