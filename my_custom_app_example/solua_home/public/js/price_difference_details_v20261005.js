// Generate the display-only price-difference snapshot used by the editable A4 formats.
(function () {
	if (window.__solua_price_difference_details_loaded) return;
	window.__solua_price_difference_details_loaded = true;

	const API = "solua_home.api.price_difference.generate_detail";
	const DEFAULT_PRICE_LIST = "Wholesale Selling";
	const DOCTYPES = ["Sales Order", "Sales Invoice"];

	function snapshot_original(frm) {
		try {
			const raw = frm.doc.custom_price_difference_detail_json;
			const detail = raw ? JSON.parse(raw) : null;
			return detail && detail.original_document && detail.original_document !== frm.doc.name ? detail.original_document : "";
		} catch (error) {
			return "";
		}
	}

	function open_dialog(frm) {
		const dialog = new frappe.ui.Dialog({
			title: __("生成/刷新差价明细"),
			fields: [
				{ fieldname: "price_list", label: __("新价格表"), fieldtype: "Link", options: "Price List", default: DEFAULT_PRICE_LIST, reqd: 1, description: __("默认使用 Wholesale Selling；可以按需要选择其他销售价格表") },
				{ fieldname: "original_document", label: __("原单据（可选）"), fieldtype: "Link", options: frm.doctype, default: snapshot_original(frm), description: __("替代单据或差价单请填写原销售订单/原销售发票；普通单据留空即可") },
				{ fieldtype: "HTML", options: __("系统会列出全部产品，同款货号自动合并；未变价产品保留并显示 0 差价。只更新打印快照，不修改金额、库存或付款。") },
			],
			primary_action_label: __("生成差价明细"),
			primary_action: async (values) => {
				if (!values.price_list) return frappe.msgprint(__("请选择新价格表"));
				dialog.disable_primary_action?.();
				try {
					const response = await frappe.call({ method: API, args: {
						doctype: frm.doctype,
						name: frm.doc.name,
						price_list: values.price_list,
						original_document: values.original_document || "",
					} });
					const result = response.message || {};
					const warnings = (result.warnings || []).map((warning) => `<li>${frappe.utils.escape_html(warning)}</li>`).join("");
					frappe.msgprint({
						title: __("差价明细已生成"),
						indicator: warnings ? "orange" : "green",
						message: `<div>${__("产品行")}: ${result.rows || 0}<br>${__("旧订单金额")}: ${format_currency(result.old_total || 0)}<br>${__("新价格合计")}: ${format_currency(result.new_total || 0)}<br>${__("价格差价")}: ${format_currency(result.difference_total || 0)}${warnings ? `<hr><b>${__("提示")}</b><ul>${warnings}</ul>` : ""}</div>`,
					});
					dialog.hide();
					await frm.reload_doc();
				} catch (error) {
					frappe.msgprint({ title: __("生成失败"), message: error.message || error, indicator: "red" });
				} finally {
					dialog.enable_primary_action?.();
				}
			},
		});
		dialog.show();
	}

	function refresh(frm) {
		if (!frm.doc.name || frm.is_new?.()) return;
		frm.add_custom_button(__("生成差价明细"), () => open_dialog(frm));
	}

	for (const doctype of DOCTYPES) frappe.ui.form.on(doctype, { refresh });
})();
