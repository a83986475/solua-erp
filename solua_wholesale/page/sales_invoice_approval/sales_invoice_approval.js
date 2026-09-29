frappe.pages["sales-invoice-approval"].on_page_load = function (wrapper) {
	const page = frappe.ui.make_app_page({
		parent: wrapper,
		title: __("销售发票提交检查"),
		single_column: true,
	});

	page.main = $(wrapper).find(".layout-main-section");
	page.main.html(`
		<div class="solua-approval-page">
			<div class="solua-approval-loading text-muted">${__("正在读取发票信息…")}</div>
		</div>
	`);
	frappe.pages["sales-invoice-approval"].page = page;
	frappe.pages["sales-invoice-approval"].wrapper = wrapper;
};

const approval_escape = (value) => frappe.utils.escape_html(String(value ?? ""));
const approval_unique = (values) => [...new Set((values || []).filter(Boolean))];
const approval_link = (doctype, name) => {
	const route = doctype.toLowerCase().replaceAll(" ", "-");
	return `<a href="/app/${route}/${encodeURIComponent(name)}">${approval_escape(name)}</a>`;
};
const approval_money = (value, currency) => {
	if (typeof format_currency === "function") return format_currency(value || 0, currency || "");
	return `${Number(value || 0).toLocaleString(undefined, { maximumFractionDigits: 2 })} ${approval_escape(currency || "")}`.trim();
};
const approval_value = (label, value, class_name = "") => `
	<div class="solua-approval-value ${class_name}">
		<div class="solua-approval-label">${approval_escape(label)}</div>
		<div class="solua-approval-text">${value || "—"}</div>
	</div>
`;

function approval_route_name() {
	const route = frappe.get_route();
	const route_name = route[0] === "sales-invoice-approval" ? route[1] : null;
	return route_name || new URLSearchParams(window.location.search).get("invoice");
}

function load_sales_invoice_approval(page, invoice_name) {
	page.main.html(`<div class="solua-approval-page"><div class="solua-approval-loading text-muted">${__("正在读取发票信息…")}</div></div>`);
	frappe.call({
		method: "solua_home.api.sales.get_sales_invoice_approval_data",
		args: { invoice_name },
	}).then((response) => render_sales_invoice_approval_page(page, response.message || {}));
}

function render_sales_invoice_selector(page) {
	page.main.html(`
		<div class="solua-approval-page">
			<div class="solua-approval-selector">
				<div class="solua-approval-eyebrow">${__("销售发票提交检查")}</div>
				<h1>${__("选择销售发票")}</h1>
				<p class="text-muted">${__("可直接搜索发票；从发票表单进入时会自动带入当前发票。")}</p>
				<div class="solua-approval-invoice-selector"></div>
				<button class="btn btn-primary solua-approval-load" type="button">${__("加载检查")}</button>
			</div>
		</div>
	`);

	let control;
	const load_selected_invoice = () => {
		const invoice_name =
			(control && control.get_input_value && control.get_input_value()) ||
			page.main.find(".solua-approval-invoice-selector input").val();
		if (invoice_name) load_sales_invoice_approval(page, invoice_name);
	};
	const df = {
		fieldtype: "Link",
		fieldname: "invoice_name",
		label: __("销售发票"),
		options: "Sales Invoice",
		onchange: load_selected_invoice,
	};
	control = frappe.ui.form.make_control({
		parent: page.main.find(".solua-approval-invoice-selector"),
		df,
		render_input: true,
	});
	control.refresh();
	page.main.find(".solua-approval-load").on("click", load_selected_invoice);
}

function render_sales_invoice_approval_page(page, data) {
	const invoice = data.invoice || {};
	const approval = data.approval || {};
	const orders = approval_unique(data.sales_orders).map((name) => approval_link("Sales Order", name)).join("、") || `<span class="text-muted">${__("未关联")}</span>`;
	const delivery_notes = approval_unique(data.delivery_notes).map((name) => approval_link("Delivery Note", name)).join("、") || `<span class="text-muted">${__("未找到已提交交货单")}</span>`;
	const permission = invoice.can_submit
		? `<span class="solua-approval-badge is-ok">${__("当前账号具有提交权限")}</span>`
		: `<span class="solua-approval-badge is-warning">${__("当前账号没有提交权限")}</span>`;
	const approval_state = !approval.large_amount
		? `<span class="solua-approval-badge">${__("金额未达到大额审批阈值")}</span>`
		: approval.bypassed
			? `<span class="solua-approval-badge is-ok">${__("管理员角色免审批")}</span>`
			: approval.approver
				? `<span class="solua-approval-badge is-ok">${approval_escape(approval.approver)} · ${approval_escape(approval.approval_date || __("待填写日期"))}</span>`
				: `<span class="solua-approval-badge is-danger">${__("未指定审批人")}</span>`;
	const issue = approval.requires_approver && !approval.approver
		? `<div class="solua-approval-alert is-warning">${__("金额超过 100,000，普通员工提交前必须指定审批人")}</div>`
		: `<div class="solua-approval-alert is-ok">${__("当前审批检查已满足")}</div>`;
	const item_count = (data.items || []).length;

	page.main.html(`
		<div class="solua-approval-page">
			<div class="solua-approval-hero">
				<div>
					<div class="solua-approval-eyebrow">${__("销售发票提交检查")}</div>
					<h1>${approval_escape(invoice.name || "")}</h1>
					<div class="text-muted">${approval_escape(invoice.status || __("草稿"))}</div>
				</div>
				<button class="btn btn-primary solua-approval-open" type="button">${__("打开销售发票")}</button>
			</div>
			${issue}
			<div class="solua-approval-grid">
				<section class="solua-approval-card">
					<h2>${__("基本信息")}</h2>
					<div class="solua-approval-values">
						${approval_value(__("客户"), invoice.customer ? approval_link("Customer", invoice.customer) : "—")}
						${approval_value(__("总计"), approval_money(invoice.grand_total, invoice.currency), "is-emphasis")}
						${approval_value(__("付款到期日"), approval_escape(invoice.due_date || "—"))}
						${approval_value(__("折扣"), `${Number(invoice.discount || 0).toFixed(2)}%`)}
					</div>
				</section>
				<section class="solua-approval-card">
					<h2>${__("关联单据")}</h2>
					<div class="solua-approval-values">
						${approval_value(__("销售订单"), orders)}
						${approval_value(__("已提交交货单"), delivery_notes)}
						${approval_value(__("明细行数"), `${item_count} ${__("行")}`)}
					</div>
				</section>
				<section class="solua-approval-card">
					<h2>${__("提交与审批")}</h2>
					<div class="solua-approval-values">
						${approval_value(__("提交权限"), permission)}
						${approval_value(__("大额审批"), approval_state)}
						${approval_value(__("审批人"), approval.approver ? approval_escape(approval.approver) : __("未指定"))}
					</div>
				</section>
			</div>
			<div class="solua-approval-footer">
				<span class="text-muted">${__("需要修改信息时，点击上方按钮返回发票表单。")}</span>
				<button class="btn btn-default solua-approval-back" type="button">${__("返回发票")}</button>
			</div>
		</div>
	`);
	page.main.find(".solua-approval-open, .solua-approval-back").on("click", () => frappe.set_route("Form", "Sales Invoice", invoice.name));
}

frappe.pages["sales-invoice-approval"].on_page_show = function () {
	const page = frappe.pages["sales-invoice-approval"].page;
	const invoice_name = approval_route_name();
	if (!page) {
		return;
	}
	if (!invoice_name) {
		render_sales_invoice_selector(page);
		return;
	}
	load_sales_invoice_approval(page, invoice_name);
};
