// solua_home: 批发销售单的图片、二维码及列显示独立开关。

const invoice_summary_escape = (value) => frappe.utils.escape_html(String(value ?? ""));
const invoice_summary_unique = (values) => [...new Set((values || []).filter(Boolean))];
const invoice_summary_link = (doctype, name) => {
	const route = doctype.toLowerCase().replaceAll(" ", "-");
	return `<a href="/app/${route}/${encodeURIComponent(name)}">${invoice_summary_escape(name)}</a>`;
};
const invoice_summary_field = (fieldname, label) =>
	`<button type="button" class="btn btn-link btn-xs p-0 solua-invoice-approval-field" data-field="${invoice_summary_escape(fieldname)}">${invoice_summary_escape(label)}</button>`;
const invoice_max_discount = (doc) => {
	let pct = Number(doc.additional_discount_percentage || 0);
	if (doc.discount_amount && doc.net_total) pct = Math.max(pct, Number(doc.discount_amount) / Number(doc.net_total) * 100);
	for (const row of doc.items || []) {
		pct = Math.max(pct, Number(row.discount_percentage || 0));
		if (row.discount_amount && row.amount) pct = Math.max(pct, Number(row.discount_amount) / Number(row.amount) * 100);
	}
	return Number.isFinite(pct) ? pct : 0;
};

function render_sales_invoice_approval_summary(frm, context = {}) {
	const wrapper = frm.fields_dict?.custom_sales_invoice_approval_summary?.$wrapper;
	if (!wrapper) return;
	const doc = frm.doc || {};
	const total = Number(doc.grand_total || 0);
	const large_amount = total > 100000;
	const approval_bypassed = frappe.session?.user === "Administrator" || frappe.user?.has_role?.("Accounts Manager");
	const orders = invoice_summary_unique((doc.items || []).map((row) => row.sales_order));
	const direct_delivery_notes = invoice_summary_unique((doc.items || []).map((row) => row.delivery_note));
	const delivery_notes = invoice_summary_unique([
		...direct_delivery_notes,
		...(context.delivery_notes || []).map((row) => row.parent),
	]);
	const discount = invoice_max_discount(doc);
	const approval_settings = context.approval_settings || {};
	const discount_needs_approval = Boolean(approval_settings.custom_enable_discount_approval)
		&& discount > Number(approval_settings.custom_discount_approval_threshold || 0);
	const can_submit = Array.isArray(frm.perm) && frm.perm.some((perm) => perm.submit);
	const permission_text = frm.perm?.length
		? (can_submit ? `<span class="text-success">${__("当前账号具有提交权限")}</span>` : `<span class="text-danger">${__("当前账号没有提交权限")}</span>`)
		: `<span class="text-muted">${__("由当前账号权限控制")}</span>`;
	const issues = [];
	if (large_amount && !approval_bypassed && !doc.custom_approver) {
		issues.push(`${invoice_summary_field("custom_approver", "填写审批人")}：${__("普通员工的大额发票需要审批")}`);
	}
	if (discount_needs_approval && !doc.custom_discount_approved) {
		issues.push(`${invoice_summary_field("custom_approval_password", "输入审批密码")}：折扣 ${discount.toFixed(2)}% 超过阈值`);
	}
	const issue_text = issues.length ? `<ul class="mb-0">${issues.map((item) => `<li>${item}</li>`).join("")}</ul>` : `<span class="text-success">${__("当前检查项已满足")}</span>`;
	const order_text = orders.length ? orders.map((name) => invoice_summary_link("Sales Order", name)).join("、") : `<span class="text-muted">${__("未关联")}</span>`;
	const delivery_text = delivery_notes.length ? delivery_notes.map((name) => invoice_summary_link("Delivery Note", name)).join("、") : `<span class="text-muted">${__("未找到已提交交货单")}</span>`;
	const approval_text = !large_amount
		? __("金额未达到大额审批阈值")
		: approval_bypassed
			? `<span class="text-success">${__("管理员角色免审批")}</span>`
			: doc.custom_approver
				? invoice_summary_escape(doc.custom_approver)
				: `<span class="text-danger">${__("未指定审批人")}</span>`;
	const title = doc.docstatus === 1 ? __("提交前检查") : __("销售发票提交前检查");
	wrapper.html(`<div class="alert ${issues.length ? "alert-warning" : "alert-success"} mb-3"><div><b>${title}</b> · ${invoice_summary_escape(doc.name || "")}</div><div class="mb-2"><b>${__("提交权限")}</b>：${permission_text}</div>${issue_text}<table class="table table-bordered table-sm mt-2 mb-0"><tbody><tr><th>${__("客户")}</th><td>${doc.customer ? invoice_summary_link("Customer", doc.customer) : `<span class="text-danger">${__("未填写")}</span>`}</td><th>${__("总计")}</th><td>${invoice_summary_escape(format_currency(total, doc.currency || ""))}</td></tr><tr><th>${__("销售订单")}</th><td>${order_text}</td><th>${__("交货单")}</th><td>${delivery_text}</td></tr><tr><th>${__("审批人")}</th><td>${approval_text}</td><th>${__("付款到期日")}</th><td>${invoice_summary_escape(doc.due_date || "—")}</td></tr><tr><th>${__("折扣")}</th><td>${invoice_summary_escape(`${discount.toFixed(2)}%`)}</td><th></th><td></td></tr></tbody></table></div>`);
	wrapper.off("click", ".solua-invoice-approval-field").on("click", ".solua-invoice-approval-field", (event) => {
		const field = event.currentTarget.dataset.field;
		frm.scroll_to_field?.(field);
		frm.fields_dict?.[field]?.$input?.focus?.();
	});
}

async function refresh_sales_invoice_approval_summary(frm) {
	if (!frm.fields_dict?.custom_sales_invoice_approval_summary) return;
	const request_id = (frm.__solua_invoice_summary_request || 0) + 1;
	frm.__solua_invoice_summary_request = request_id;
	const order_names = invoice_summary_unique((frm.doc.items || []).map((row) => row.sales_order));
	render_sales_invoice_approval_summary(frm);
	try {
		const [delivery_notes, company] = await Promise.all([
			order_names.length ? frappe.db.get_list("Delivery Note Item", { filters: { against_sales_order: ["in", order_names], docstatus: 1 }, fields: ["parent", "against_sales_order"], limit: 100 }) : [],
			frm.doc.company ? frappe.db.get_value("Company", frm.doc.company, ["custom_enable_discount_approval", "custom_discount_approval_threshold"]) : { message: {} },
		]);
		if (frm.__solua_invoice_summary_request !== request_id) return;
		render_sales_invoice_approval_summary(frm, { delivery_notes, approval_settings: company?.message || {} });
	} catch (error) {
		if (frm.__solua_invoice_summary_request === request_id) render_sales_invoice_approval_summary(frm);
	}
}

frappe.ui.form.on("Sales Invoice", {
	refresh(frm) {
		refresh_sales_invoice_approval_summary(frm);
		if (frm.is_new() || frm.__solua_wholesale_print_button) return;
		frm.__solua_wholesale_print_button = true;

		frm.add_custom_button(__("批发销售单"), () => {
			const saved_options = window.solua_home_print_preferences?.read(frm.doctype) || {};
			const print_default = (fieldname, fallback) => Object.prototype.hasOwnProperty.call(saved_options, fieldname) ? saved_options[fieldname] : fallback;
			const dialog = new frappe.ui.Dialog({
				title: __("批发销售单打印选项"),
			fields: [
				{
					fieldname: "show_item_name",
					label: __("显示商品名称"),
					fieldtype: "Check",
					default: print_default("show_item_name", frm.doc.custom_print_item_name == null ? 1 : frm.doc.custom_print_item_name),
				},
				{
					fieldname: "show_sku",
					label: __("显示 SKU/货号"),
					fieldtype: "Check",
					default: print_default("show_sku", frm.doc.custom_print_sku == null ? 1 : frm.doc.custom_print_sku),
				},
				{
					fieldname: "show_color",
					label: __("显示颜色"),
					fieldtype: "Check",
					default: print_default("show_color", (frm.doc.custom_print_color_code || frm.doc.custom_print_cor) ? 1 : 0),
				},
				{
					fieldname: "merge_order_code",
					label: __("合并同款对外货号"),
					fieldtype: "Check",
					default: print_default("merge_order_code", frm.doc.custom_print_merge_order_code ? 1 : 0),
				},
				{
					fieldname: "show_description",
					label: __("显示商品描述"),
					fieldtype: "Check",
					default: print_default("show_description", frm.doc.custom_print_description == null ? 1 : frm.doc.custom_print_description),
				},
				{
						fieldname: "show_images",
						label: __("显示颜色图片"),
						fieldtype: "Check",
						default: print_default("show_images", frm.doc.custom_print_color_images ? 1 : 0),
					},
					{
						fieldname: "show_qr",
						label: __("显示色卡二维码"),
						fieldtype: "Check",
						default: print_default("show_qr", frm.doc.custom_print_color_qr ? 1 : 0),
					},
				],
				primary_action_label: __("保存并打开预览"),
				primary_action(values) {
					const save = frm.set_value({
						custom_print_item_name: values.show_item_name ? 1 : 0,
						custom_print_sku: values.show_sku ? 1 : 0,
						custom_print_color_code: values.show_color ? 1 : 0,
						custom_print_cor: values.show_color ? 1 : 0,
						custom_print_merge_order_code: values.merge_order_code ? 1 : 0,
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
						window.solua_home_print_preferences?.save(frm.doctype, values);
						dialog.hide();
					});
				},
			});
			dialog.show();
		}, __("打印"));
	},
});
