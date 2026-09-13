// solua_home: 批发销售单的图片/二维码两个独立打印开关。

frappe.ui.form.on("Sales Invoice", {
	refresh(frm) {
		if (frm.is_new() || frm.__solua_wholesale_print_button) return;
		frm.__solua_wholesale_print_button = true;

		frm.add_custom_button(__("批发销售单"), () => {
			const dialog = new frappe.ui.Dialog({
				title: __("批发销售单打印选项"),
				fields: [
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
						custom_print_color_images: values.show_images ? 1 : 0,
						custom_print_color_qr: values.show_qr ? 1 : 0,
					});
					save.then(() => frm.save()).then(() => {
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
