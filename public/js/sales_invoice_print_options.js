// solua_home: 批发销售单的图片、二维码及列显示独立开关。

const invoice_summary_escape = (value) => frappe.utils.escape_html(String(value ?? ""));
const invoice_summary_unique = (values) => [...new Set((values || []).filter(Boolean))];
const invoice_summary_link = (doctype, name) => {
	const route = doctype.toLowerCase().replaceAll(" ", "-");
	return `<a href="/app/${route}/${encodeURIComponent(name)}">${invoice_summary_escape(name)}</a>`;
};
const invoice_summary_delivery_names = (rows) => (rows || [])
	.map((row) => typeof row === "string" ? row : row?.name || row?.parent)
	.filter(Boolean);
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
const invoice_summary_style = `
.solua-invoice-check { max-width: 1180px; padding: 22px 4px 32px; }
.solua-invoice-check__heading { align-items: center; display: flex; justify-content: space-between; gap: 24px; margin-bottom: 20px; }
.solua-invoice-check__eyebrow { color: var(--text-muted); font-size: 13px; }
.solua-invoice-check__heading h3 { font-size: 24px; margin: 4px 0 0; }
.solua-invoice-check__alert { border-radius: 10px; font-size: 15px; margin-bottom: 20px; padding: 14px 18px; }
.solua-invoice-check__alert.is-ok { background: var(--green-50); color: var(--green-700); }
.solua-invoice-check__alert.is-warning { background: var(--yellow-50); color: var(--yellow-700); }
.solua-invoice-check__grid { display: grid; grid-template-columns: repeat(3, minmax(0, 1fr)); gap: 18px; }
.solua-invoice-check__card { background: var(--card-bg); border: 1px solid var(--border-color); border-radius: 10px; min-height: 190px; padding: 20px; }
.solua-invoice-check__card h4 { font-size: 17px; margin: 0 0 18px; }
.solua-invoice-check__item { margin-bottom: 16px; }
.solua-invoice-check__label { color: var(--text-muted); font-size: 13px; margin-bottom: 4px; }
.solua-invoice-check__value { font-size: 16px; line-height: 1.5; word-break: break-word; }
.solua-invoice-check__value.is-emphasis { font-size: 21px; font-weight: 700; }
@media (max-width: 900px) { .solua-invoice-check__grid { grid-template-columns: 1fr; } }
`;
const invoice_summary_item = (label, value, class_name = "") =>
	`<div class="solua-invoice-check__item"><div class="solua-invoice-check__label">${invoice_summary_escape(label)}</div><div class="solua-invoice-check__value ${class_name}">${value || "—"}</div></div>`;

function render_sales_invoice_approval_summary(frm, context = {}) {
	const wrapper = frm.fields_dict?.custom_sales_invoice_approval_summary?.$wrapper;
	if (!wrapper) return;
	const doc = frm.doc || {};
	const total = Number(doc.grand_total || 0);
	const large_amount = total > 100000;
	const approval_bypassed = frappe.session?.user === "Administrator" || frappe.user?.has_role?.("Accounts Manager");
	const orders = invoice_summary_unique((doc.items || []).map((row) => row.sales_order));
	const direct_delivery_notes = invoice_summary_unique((doc.items || []).map((row) => row.delivery_note));
	const delivery_notes = invoice_summary_unique([...direct_delivery_notes, ...invoice_summary_delivery_names(context.delivery_notes)]);
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
	const issue_text = issues.length ? `<ul class="mb-0">${issues.map((item) => `<li>${item}</li>`).join("")}</ul>` : __("当前检查项已满足");
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
	wrapper.html(`<style>${invoice_summary_style}</style><div class="solua-invoice-check"><div class="solua-invoice-check__heading"><div><div class="solua-invoice-check__eyebrow">${title}</div><h3>${invoice_summary_escape(doc.name || "")}</h3></div><div>${permission_text}</div></div><div class="solua-invoice-check__alert ${issues.length ? "is-warning" : "is-ok"}">${issue_text}</div><div class="solua-invoice-check__grid"><section class="solua-invoice-check__card"><h4>${__("基本信息")}</h4>${invoice_summary_item(__("客户"), doc.customer ? invoice_summary_link("Customer", doc.customer) : `<span class="text-danger">${__("未填写")}</span>`)}${invoice_summary_item(__("总计"), invoice_summary_escape(format_currency(total, doc.currency || "")), "is-emphasis")}${invoice_summary_item(__("付款到期日"), invoice_summary_escape(doc.due_date || "—"))}${invoice_summary_item(__("折扣"), invoice_summary_escape(`${discount.toFixed(2)}%`))}</section><section class="solua-invoice-check__card"><h4>${__("关联单据")}</h4>${invoice_summary_item(__("销售订单"), order_text)}${invoice_summary_item(__("已提交交货单"), delivery_text)}</section><section class="solua-invoice-check__card"><h4>${__("提交与审批")}</h4>${invoice_summary_item(__("大额审批"), approval_text)}${invoice_summary_item(__("审批人"), doc.custom_approver ? invoice_summary_escape(doc.custom_approver) : __("未指定"))}</section></div></div>`);
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
			order_names.length ? frappe.db.get_list("Delivery Note", {
				filters: [["Delivery Note Item", "against_sales_order", "in", order_names], ["docstatus", "=", 1]],
				fields: ["name"],
				distinct: true,
				limit_page_length: 100,
			}) : [],
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
		frm.set_df_property?.("custom_sales_invoice_approval_summary", "hidden", 0);
		refresh_sales_invoice_approval_summary(frm);
		if (frm.is_new() || frm.__solua_wholesale_print_button) return;
		frm.__solua_wholesale_print_button = true;
		frm.add_custom_button(__("提交检查页面"), () => frappe.set_route("sales-invoice-approval", frm.doc.name), __("查看"));

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
					label: __("显示固定色号"),
					fieldtype: "Check",
					default: frm.doc.custom_print_color_code == null ? 1 : frm.doc.custom_print_color_code,
				},
				{
					fieldname: "show_cor",
					label: __("显示 Cor/颜色"),
					fieldtype: "Check",
					default: frm.doc.custom_print_cor == null ? 0 : frm.doc.custom_print_cor,
				},
				{
					fieldname: "merge_order_code",
					label: __("合并同款对外货号"),
					fieldtype: "Check",
					default: frm.doc.custom_print_merge_order_code ? 1 : 0,
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
						custom_print_cor: values.show_cor ? 1 : 0,
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
						dialog.hide();
					});
				},
			});
			dialog.show();
		}, __("打印"));
	},
});
