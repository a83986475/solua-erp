(() => {
	const pdfLabel = __("发送到微信");
	const tableLabel = __("发送表格到微信");
	const send = (frm, method, confirmation) => {
		frappe.confirm(confirmation, () => {
			frappe.call({
				method,
				args: { name: frm.doc.name },
				freeze: true,
				freeze_message: __("正在发送到微信…"),
			}).then((response) => {
				if (response?.exc) throw new Error(response.exc);
				frappe.show_alert({
					message: __("已发送：{0}", [response.message?.filename || frm.doc.name]),
					indicator: "green",
				});
			}).catch((error) => {
				frappe.msgprint({
					title: __("发送失败"),
					indicator: "red",
					message: error?.message || __("企业微信发送失败"),
				});
			});
		});
	};

	frappe.ui.form.on("Sales Order", {
		refresh(frm) {
			frm.remove_custom_button?.(pdfLabel, __("工具"));
			frm.remove_custom_button?.(tableLabel, __("工具"));
			if (frm.is_new()) return;
			frm.add_custom_button(pdfLabel, () => {
				send(frm, "solua_home.api.wecom.send_sales_order_customer_pdf_to_wechat", __("将当前销售订单 PDF 发送到企业微信群，继续吗？"));
			}, __("工具"));
			frm.add_custom_button(tableLabel, () => {
				send(frm, "solua_home.api.wecom.send_sales_order_customer_xlsx_to_wechat", __("将当前销售订单表格发送到企业微信群，继续吗？"));
			}, __("工具"));
		},
	});
})();
