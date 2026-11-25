(() => {
	const pdfLabel = __("发送到微信");
	const tableLabel = __("发送表格到微信");
	const autoSendLabel = __("订单更新后自动发送");
	const configureAutoSend = async () => {
		const enabled = await frappe.xcall("solua_home.api.wecom.get_sales_order_auto_send");
		const dialog = new frappe.ui.Dialog({
			title: autoSendLabel,
			fields: [{
				fieldname: "enabled",
				fieldtype: "Check",
				label: __("订单修改保存后发送到微信"),
				description: __("适用于所有销售订单。订单首次提交时始终自动发送 PDF 和 Excel。"),
				default: enabled ? 1 : 0,
			}],
			primary_action_label: __("保存"),
			async primary_action(values) {
				const active = await frappe.xcall("solua_home.api.wecom.set_sales_order_auto_send", {
					enabled: values.enabled ? 1 : 0,
				});
				dialog.hide();
				frappe.show_alert({message: active ? __("订单更新后自动发送已开启") : __("订单更新后自动发送已关闭"), indicator: "green"});
			},
		});
		dialog.show();
	};
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
			frm.remove_custom_button?.(autoSendLabel, __("工具"));
			if (frappe.session.user === "Administrator" || frappe.user.has_role("System Manager")) {
				frm.add_custom_button(autoSendLabel, configureAutoSend, __("工具"));
			}
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
