frappe.pages["solua-home"].on_page_load = function (wrapper) {
	const page = frappe.ui.make_app_page({ parent: wrapper, title: __("Solua Home"), single_column: true });
	page.main.html(`
		<div class="solua-home-page">
			<div class="solua-home-header">
				<div><div class="solua-home-brand"><img class="solua-home-logo" src="/files/solua-logo.jpg" alt="Solua Home">Solua Home</div><div class="solua-home-subtitle">批发经营 · 订单履约 · 配送与库存</div></div>
				<div class="solua-home-header-actions"><span class="solua-home-meta" data-role="company"></span><span class="solua-home-meta" data-role="date"></span><button class="btn btn-sm btn-default" data-action="refresh">${__("刷新")}</button></div>
			</div>
			<div class="solua-home-state" data-role="state">${__("加载中…")}</div>
			<section class="solua-home-section" data-section="wholesale-nav"><h3>${__("批发导航与报表")}</h3><div class="solua-home-report-links" data-role="report-links"></div></section>
			<section class="solua-home-section" data-section="quick-actions"><h3>${__("常用功能")}</h3><div class="solua-home-actions" data-role="quick-actions"></div></section>
			<section class="solua-home-section" data-section="overview"><h3>${__("经营概览")}</h3><div class="solua-home-cards" data-role="cards"></div>
				<div class="solua-home-period-control"><label><input type="checkbox" data-common-enabled> ${__("统一金额卡片时间范围")}</label>
				<select class="form-control" aria-label="统一时间范围" data-common-period>${["今天", "本周", "本月", "本季度", "本年", "自定义"].map(period => `<option>${__(period)}</option>`).join("")}</select>
				<span data-common-custom><input type="date" class="form-control" aria-label="统一开始日期" data-common-from> ～ <input type="date" class="form-control" aria-label="统一结束日期" data-common-to></span>
				<span class="text-muted">${__("默认各自设置；关闭统一范围后恢复。")}</span></div>
				<div class="solua-home-period-note text-muted">${__("已付金额按期间发票的结清金额统计，包含已核销预收款及结算调整。")}</div>
				<div class="solua-home-cards solua-home-totals" data-role="totals"></div></section>
			<div class="solua-home-columns">
			<section class="solua-home-section" data-section="pending"><h3>${__("待处理")}</h3><div data-role="pending"></div></section>
			<section class="solua-home-section" data-section="billing"><h3>${__("待开票客户")}</h3><div data-role="billing"></div></section>
				<section class="solua-home-section" data-section="search"><h3>${__("商品查找")}</h3><div class="solua-home-search"><input class="form-control" data-role="search" placeholder="${__("款号、商品名称、颜色或原包装条码")}"><button class="btn btn-default" data-action="search">${__("查找")}</button></div><div data-role="results"></div></section>
			</div>
			<details class="solua-home-section" data-section="actions"><summary data-role="actions-title">${__("全部功能")}</summary><div class="solua-home-actions" data-role="actions"></div></details>
			<details class="solua-home-section" data-section="data-status"><summary data-role="data-status-title">${__("资料准备")}</summary><div data-role="data-status"></div></details>
		</div>`);

	const root = page.main;
	const text = (value, fallback = "—") => frappe.utils.escape_html(String(value ?? fallback));
	const money = (value, currency) => value == null ? "—" : format_currency(value, currency);
	const route = (doctype, name) => frappe.set_route(name ? "Form" : "List", doctype, name);
	const state_label = (state) => ({ no_permission: __("无权限"), no_data: __("暂无数据"), unconfigured: __("未配置库存预警阈值"), incomplete: __("库存明细不完整，无法汇总"), error: __("加载失败") }[state] || "");
	const WHOLESALE_INVOICE_FORMAT = "批发销售单（颜色版）";
	const GROUP_LINK_HINT = __("打开对应模块工作区");
	const DESK_SUBTITLE = __("批发经营 · 订单履约 · 配送与库存");
	const POS_SUBTITLE = __("收银台 · 销售单与交班");
	let current_warehouse = null;
	let dashboard_data = null;
	let totals_generation = 0;
	let common_enabled = false;
	let common_range = {period: "本月", from_date: "", to_date: ""};
	const common_key = `solua-business-common-range:${frappe.session?.user}`;
	try {
		const saved = JSON.parse(window.localStorage?.getItem(common_key) || "{}");
		common_enabled = saved.enabled === true;
		if (["今天", "本周", "本月", "本季度", "本年", "自定义"].includes(saved.period)) common_range = {...common_range, ...saved};
	} catch (_) {}
	function range_valid() {
		return common_range.period !== "自定义" || (common_range.from_date && common_range.to_date && common_range.from_date <= common_range.to_date);
	}
	function sync_period_controls() {
		root.find('[data-common-enabled]').prop("checked", common_enabled);
		root.find('[data-common-period]').val(common_range.period).prop("disabled", !common_enabled);
		root.find('[data-common-from]').val(common_range.from_date);
		root.find('[data-common-to]').val(common_range.to_date);
		root.find('[data-common-custom]').toggle(common_enabled && common_range.period === "自定义");
	}
	sync_period_controls();

	// A row action: with a name it opens the form, with { new_doc: true } it starts a new
	// document, with { view: true } it opens the filtered list the user can browse.
	function action(label, doctype, name, allowed = false, options = {}) {
		if (!allowed) return "";
		const purpose = options.purpose || "";
		const stock_entry_type = options.stock_entry_type || "";
		const new_doc = options.new_doc ? ` data-new-doc="1"` : "";
		const view = options.view ? ` data-view="list"` : "";
		const href = options.href ? ` href="${text(options.href)}"` : "";
		const tag = options.href ? "a" : "button";
		return `<${tag} class="btn btn-default btn-sm solua-home-action" data-doctype="${text(doctype)}" data-name="${text(name || "")}"${purpose ? ` data-purpose="${text(purpose)}"` : ""}${stock_entry_type ? ` data-stock-entry-type="${text(stock_entry_type)}"` : ""}${new_doc}${view}${href}>${text(label)}</${tag}>`;
	}

	function new_action(label, doctype, allowed = false, options = {}) {
		return action(label, doctype, null, allowed, { ...options, new_doc: true });
	}

	function view_action(label, doctype, allowed = false) {
		const slug = frappe.router?.slug ? frappe.router.slug(doctype) : String(doctype).toLowerCase().replace(/[^a-z0-9]+/g, "-");
		return action(label, doctype, null, allowed, { view: true, href: `/app/${slug}` });
	}

	function utility_action(label, key, allowed = false) {
		if (!allowed) return "";
		const hrefs = { print_settings: "/app/print-settings", print_designer: "/app/print-designer", a4_print_designer: "/desk/a4-print-designer", wholesale_print_format: "/app/print-format", sales_invoice_approval: "/desk/sales-invoice-approval" };
		const href = hrefs[key] ? ` href="${text(hrefs[key])}"` : "";
		const tag = href ? "a" : "button";
		return `<${tag} class="btn btn-default btn-sm solua-home-action" data-utility="${text(key)}"${href}>${text(label)}</${tag}>`;
	}

	function report_action(label, report, allowed = false, filters = {}) {
		if (!allowed) return "";
		const today = dashboard_data?.query_time?.slice(0, 10);
		const dated = ["Item-wise Sales History", "Sales Order Analysis", "Sales Register", "Gross Profit", "Stock Balance", "Stock Ledger"].includes(report);
		const dates = dated && today ? {from_date: frappe.datetime.add_months(today, -1), to_date: today} : {};
		return `<button type="button" class="btn btn-default btn-sm" data-report="${text(report)}" data-report-filters="${text(JSON.stringify({company: dashboard_data?.company, ...dates, ...filters}))}">${text(label)}</button>`;
	}

	function filtered_action(label, doctype, allowed, filters) {
		if (!allowed) return "";
		return `<button class="btn btn-default btn-sm solua-home-action" data-doctype="${text(doctype)}" data-filters="${text(JSON.stringify({company: dashboard_data?.company, ...filters}))}">${text(label)}</button>`;
	}

	// The group header doubles as the entrance to the module workspace, so the block is
	// both "jump to the whole module" and "run one of the routines below".
	function group_header(title, link, allowed = true) {
		if (!allowed || !link) return `<h4 class="solua-home-group-title">${text(title)}</h4>`;
		const attrs = [`title="${text(`${title} · ${GROUP_LINK_HINT}`)}"`];
		if (link.workspace) attrs.push(`data-workspace="${text(link.workspace)}"`);
		else if (link.doctype) attrs.push(`data-doctype="${text(link.doctype)}" data-view="list"`);
		else return `<h4 class="solua-home-group-title">${text(title)}</h4>`;
		if (link.fallback) attrs.push(`data-fallback-view="${text(link.fallback)}"`);
		return `<button type="button" class="solua-home-group-title solua-home-group-title-link" ${attrs.join(" ")}><span>${text(title)}</span><span class="solua-home-group-arrow">›</span></button>`;
	}

	function action_group(title, link, buttons, allowed = true) {
		const visible = buttons.filter(Boolean);
		if (!visible.length) return "";
		return `<div class="solua-home-action-group">${group_header(title, link, allowed)}<div class="solua-home-actions">${visible.join("")}</div></div>`;
	}

	function open_workspace(name, fallback_doctype) {
		const slug = frappe.router?.slug ? frappe.router.slug(name) : null;
		if (slug && frappe.workspaces?.[slug]) return frappe.set_route(slug);
		if (fallback_doctype) return route(fallback_doctype, null);
		return frappe.msgprint(__("没有访问「{0}」工作区的权限。", [text(name)]));
	}

	function render(data) {
		dashboard_data = data;
		const pos_mode = data.home_mode === "pos";
		current_warehouse = data.warehouse || null;
		root.find('[data-role="company"]').text(data.company || "");
		root.find('[data-role="date"]').text(data.query_time ? `${__("查询时间")} ${data.query_time}` : "");
		root.find('[data-role="state"]').text(pos_mode && data.pos_profile ? `${__("收银台")}：${data.pos_profile}` : "");
		// 收银员只用 POS：经营概览 / 待处理 / 资料准备整块隐藏，只留收银入口与商品查找
		root.find('[data-section="overview"], [data-section="pending"], [data-section="billing"], [data-section="data-status"]').toggle(!pos_mode);
		root.find('[data-section="wholesale-nav"], [data-section="quick-actions"]').toggle(!pos_mode);
		root.find(".solua-home-columns").toggleClass("solua-home-columns-single", pos_mode);
		root.find('[data-role="actions-title"]').text(pos_mode ? __("收银") : __("全部功能"));
		root.find('[data-section="actions"]').prop("open", pos_mode);
		root.find(".solua-home-subtitle").text(pos_mode ? POS_SUBTITLE : DESK_SUBTITLE);
		const permissions = data.permissions || {};
		const stock_entry_types = data.stock_entry_types || {};
		if (pos_mode) {
			root.find('[data-role="cards"], [data-role="pending"], [data-role="billing"], [data-role="data-status"], [data-role="report-links"], [data-role="quick-actions"]').html("");
			root.find('[data-role="actions"]').html(pos_actions(permissions));
			return;
		}
		render_desk_panels(data);
		root.find('[data-role="report-links"]').html([
			[__("库存树报表"), "Template Stock Tree"], [__("经营金额报表"), "Solua Business Totals"], [__("送货汇总"), "Solua Delivery Summary"]
		].filter(([, report]) => report === "Template Stock Tree" ? permissions.read_bin : report === "Solua Delivery Summary" ? permissions.read_delivery_note : permissions.read_sales_invoice).map(([label, report]) => `<button type="button" class="btn btn-default btn-sm" data-report="${text(report)}" data-report-filters="${text(JSON.stringify({company: data.company, ...(report === "Template Stock Tree" ? {warehouse: data.warehouse} : {})}))}">${text(label)}</button>`).join(""));
		root.find('[data-role="report-links"]').append(`<button type="button" class="btn btn-default btn-sm" data-sidebar-open="1">${__("打开批发侧栏")}</button>`);
		root.find('[data-role="quick-actions"]').html([
			new_action(__("新建销售订单"), "Sales Order", permissions.new_sales_order),
			report_action(__("物料销售明细"), "Item-wise Sales History", permissions.read_sales_order),
			utility_action(__("按订单开交货单"), "delivery_from_order", permissions.new_delivery_note),
			permissions.read_delivery_note && permissions.read_sales_invoice ? `<button class="btn btn-default btn-sm" data-scroll="billing">${__("待开票客户")}</button>` : "",
			new_action(__("新建收款单"), "Payment Entry", permissions.new_payment_entry),
			permissions.read_item ? `<button class="btn btn-default btn-sm" data-focus-search="1">${__("查库存")}</button>` : ""
		].filter(Boolean).join(""));
		root.find('[data-role="actions"]').html(desk_actions(permissions, stock_entry_types));
		load_billing_queue(data);
	}

	// 资料准备：每条检查都点名具体物料，并能直接跳到只含这些物料的列表。
	const ISSUE_FILTER_LIMIT = 200;
	const ISSUE_BODY_LIMIT = 50;

	function issue_row(issue) {
		const key = text(issue.key || "");
		const count = issue.count;
		const names = (issue.items || []).map((row) => row.name);
		const preview = names.slice(0, 3).join("、") + (names.length > 3 ? " …" : "");
		if (!count) return `<div class="solua-home-issue solua-home-issue-ok" data-issue="${key}"><span>${text(issue.label)}</span><span class="solua-home-issue-note">✓ ${__("已齐全")}</span></div>`;
		const body = (issue.items || []).slice(0, ISSUE_BODY_LIMIT).map((row) => `<button class="solua-home-list-row" data-doctype="Item" data-name="${text(row.name)}"><span>${text(row.name)}</span><span>${text(row.item_name || "")}${row.item_group ? ` · ${text(row.item_group)}` : ""}</span></button>`).join("");
		const hidden = Math.max(count - Math.min(names.length, ISSUE_BODY_LIMIT), 0);
		const more = hidden ? `<div class="solua-home-issue-note">${__("还有 {0} 条未列出，请在列表中查看", [hidden])}</div>` : "";
		// A name filter keeps the drill-down honest: the list holds exactly these items.
		const list_button = names.length && !issue.truncated && names.length <= ISSUE_FILTER_LIMIT
			? `<button class="solua-home-list-row solua-home-issue-list" data-doctype="Item" data-filters="${text(JSON.stringify({ name: ["in", names] }))}"><span>${__("在物料列表中只看这 {0} 条", [count])}</span><span>›</span></button>`
			: `<button class="solua-home-list-row solua-home-issue-list" data-doctype="Item" data-view="list"><span>${__("在物料列表中查看")}</span><span>›</span></button>`;
		return `<div class="solua-home-issue" data-issue="${key}"><button type="button" class="solua-home-issue-head" data-issue-toggle="${key}"><span class="solua-home-issue-label">${text(issue.label)} <b>${text(count)}</b></span><span class="solua-home-issue-note">${text(issue.hint || "")}${preview ? " · " + text(preview) : ""}</span><span class="solua-home-issue-arrow">›</span></button><div class="solua-home-issue-body" data-issue-body="${key}">${body}${more}${list_button}</div></div>`;
	}

	function render_item_data(item_data) {
		const target = root.find('[data-role="data-status"]');
		const data = item_data || {};
		const ready = data.state === "ok" && (data.issues || []).every(issue => issue.count === 0);
		root.find('[data-section="data-status"]').prop("open", !ready);
		root.find('[data-role="data-status-title"]').text(ready ? __("资料准备 · 已齐全") : __("资料准备"));
		if (data.state === "no_permission") return target.html(`<div class="text-muted">${__("商品资料")}：— ${__("无权限查看，不会伪装为 0")}</div>`);
		if (!data.item_count) return target.html(`<div class="text-muted">${text(state_label(data.state), __("暂无物料"))}</div>`);
		const issues = data.issues || [];
		if (!issues.length) return target.html(`<button type="button" class="solua-home-list-row" data-doctype="Item" data-view="list"><span>${__("商品资料")} · ${__("共 {0} 条", [data.item_count])}</span><span>${__("查看商品")} ›</span></button>`);
		// Templates never carry a single image or colour code, so they are excluded from the checks.
		const checked = data.checked_count ?? data.item_count;
		const template_note = data.template_count ? __("，模板 {0} 条不计", [data.template_count]) : "";
		target.html(`<div class="solua-home-issue-summary">${__("共 {0} 条启用物料，其中 {1} 条单品/变体参与检查{2}，以下问题点开即可看到具体是哪些：", [data.item_count, checked, template_note])}</div>${issues.map(issue_row).join("")}<button type="button" class="solua-home-list-row" data-doctype="Item" data-view="list"><span>${__("查看全部物料")}</span><span>›</span></button>`);
	}

	function render_desk_panels(data) {
		const links = [
			["Sales Register", {company: data.company, from_date: data.query_time?.slice(0, 10), to_date: data.query_time?.slice(0, 10)}],
			["Accounts Receivable", {company: data.company}],
			["Sales Order Analysis", {company: data.company, status: ["To Deliver", "To Deliver and Bill"], from_date: "2000-01-01", to_date: data.query_time?.slice(0, 10)}],
			["Solua Delivery Summary", {company: data.company, from_date: data.query_time?.slice(0, 10), to_date: data.query_time?.slice(0, 10)}],
			["Stock Projected Qty", {company: data.company, warehouse: data.warehouse}],
		];
		const cards = [
			[__("今日已开票额"), money(data.invoiced_today?.amount, data.currency), data.invoiced_today?.state],
			[__("客户未收款"), money(data.outstanding?.amount, data.currency), data.outstanding?.state],
			[__("已确认待交付"), data.orders_pending?.count ?? "—", data.orders_pending?.state],
			[__("今日已送货额"), money(data.delivered_today?.amount, data.currency), data.delivered_today?.state],
			[__("库存预警"), data.low_stock?.count ?? "—", data.low_stock?.state],
		];
		root.find('[data-role="cards"]').html(cards.map(([label, value, state], index) => `<button type="button" class="solua-home-card" data-report="${text(links[index][0])}" data-report-filters="${text(JSON.stringify(links[index][1]))}" ${state === "no_permission" ? "disabled" : ""}><div class="solua-home-card-label">${text(label)} ›</div><div class="solua-home-card-value">${["ok", "no_data"].includes(state) ? text(value) : "—"}</div><div class="solua-home-card-state">${text(state_label(state), "")}</div></button>`).join(""));
		load_totals(data);
		const pending = data.orders_pending?.items || [];
		root.find('[data-role="pending"]').html([
			`<div class="solua-home-pending-title">${__("待交付订单")}：${data.orders_pending?.state === "no_permission" ? "—" : data.orders_pending?.count ?? "—"} ${data.orders_pending?.state !== "no_permission" ? `<button class="btn btn-link btn-xs solua-home-list-row" data-doctype="Sales Order" data-filters='${text(JSON.stringify({company: data.company, docstatus: 1, per_delivered: ["<", 100], status: ["not in", ["Closed", "Completed", "Cancelled"]]}))}'>${__("查看全部")}</button>` : ""}</div>`,
			pending.length ? pending.map((row) => `<button class="solua-home-list-row" data-doctype="Sales Order" data-name="${text(row.name)}"><span>${text(row.name)} · ${text(row.delivery_date || "")}</span><span>${text(row.customer)} · ${row.remaining_by_uom?.map(q => `${text(q.qty)} ${text(q.uom)}`).join("、") || "—"} ${__("待交付")}</span></button>`).join("") : `<div class="text-muted">${data.orders_pending?.state === "no_data" ? __("暂无待交付订单") : text(state_label(data.orders_pending?.state))}</div>`,
			`<div class="solua-home-pending-title">${__("逾期应收")}：${data.overdue_count ?? "—"} ${data.overdue_counts?.["Sales Invoice"] ? `<button class="btn btn-link btn-xs solua-home-list-row" data-doctype="Sales Invoice" data-filters='${text(JSON.stringify({company: data.company, docstatus: 1, outstanding_amount: [">", 0], due_date: ["<", data.query_time?.slice(0, 10)], ...(data.overdue_sales_invoice_exclude_topups ? {custom_is_topup: 0} : {})}))}'>${__("销售发票")} ${data.overdue_counts["Sales Invoice"]}</button>` : ""} ${data.overdue_counts?.["POS Invoice"] ? `<button class="btn btn-link btn-xs solua-home-list-row" data-doctype="POS Invoice" data-filters='${text(JSON.stringify({company: data.company, docstatus: 1, consolidated_invoice: ["is", "not set"], outstanding_amount: [">", 0], due_date: ["<", data.query_time?.slice(0, 10)]}))}'>POS ${data.overdue_counts["POS Invoice"]}</button>` : ""}</div>`,
			(data.overdue?.items || []).length ? data.overdue.items.map((row) => `<button class="solua-home-list-row" data-doctype="${text(row.doctype || "Sales Invoice")}" data-name="${text(row.name)}"><span>${text(row.name)} · ${text(row.due_date)} · ${text(row.overdue_days)} ${__("天逾期")}</span><span>${text(row.customer)} · ${text(money(row.base_outstanding_amount, data.currency))}</span></button>`).join("") : `<div class="text-muted">${data.overdue?.state === "no_data" ? __("暂无逾期应收") : text(state_label(data.overdue?.state))}</div>`,
			`<div class="solua-home-pending-title">${__("待到货采购订单")}：${data.pending_purchase?.count ?? "—"} ${data.pending_purchase?.state !== "no_permission" ? `<button class="btn btn-link btn-xs solua-home-list-row" data-doctype="Purchase Order" data-filters='${text(JSON.stringify({company: data.company, docstatus: 1, per_received: ["<", 100], status: ["not in", ["Closed", "Completed", "Cancelled"]]}))}'>${__("查看全部")}</button>` : ""}</div>`,
			(data.pending_purchase?.items || []).map((row) => `<button class="solua-home-list-row" data-doctype="Purchase Order" data-name="${text(row.name)}"><span>${text(row.name)} · ${text(row.transaction_date)}</span><span>${text(row.supplier)} · ${text(row.status)}</span></button>`).join("") || `<div class="text-muted">${data.pending_purchase?.state === "no_permission" ? text(state_label(data.pending_purchase.state)) : __("暂无待到货采购订单")}</div>`,
			`<div class="solua-home-pending-title">${__("库存预警")} · ${text(data.warehouse)} · ${data.low_stock?.count ?? "—"} ${data.low_stock?.item_codes?.length ? `<button class="btn btn-link btn-xs solua-home-list-row" data-doctype="Item" data-filters="${text(JSON.stringify({name: ["in", data.low_stock.item_codes]}))}">${__("查看全部")}</button>` : ""}</div>`,
			data.low_stock?.state === "incomplete" ? `<div class="text-muted">${text(state_label(data.low_stock.state))}</div>` : "",
			(data.low_stock?.items || []).map((row) => `<button class="solua-home-list-row" data-doctype="Item" data-name="${text(row.name)}"><span>${text(row.item_name)}</span><span>${text(row.actual_qty)} / ${text(row.reorder_level)} ${text(row.stock_uom)}</span></button>`).join("") || `<div class="text-muted">${data.low_stock?.state === "unconfigured" ? __("未配置库存预警阈值") : data.low_stock?.state === "no_data" ? __("暂无库存预警") : text(state_label(data.low_stock?.state))}</div>`,
			`<div class="solua-home-pending-title">${__("待完成发票草稿")}：${data.draft_sales_count ?? "—"} ${data.draft_sales?.state !== "no_permission" ? `<button class="btn btn-link btn-xs solua-home-list-row" data-doctype="Sales Invoice" data-filters="${text(JSON.stringify({company: data.company, docstatus: 0}))}">${__("查看全部")}</button>` : ""}</div>`,
			(data.draft_sales?.items || []).map((row) => `<button class="solua-home-list-row" data-doctype="Sales Invoice" data-name="${text(row.name)}"><span>${text(row.name)}</span><span>${text(row.customer)} · ${text(money(row.base_grand_total, data.currency))}</span></button>`).join("") || `<div class="text-muted">${data.draft_sales?.state === "no_permission" ? text(state_label(data.draft_sales.state)) : __("暂无待完成发票草稿")}</div>`,
		].join(""));
		root.find('[data-role="data-status"]').html("");
		render_item_data(data.item_data);
	}

	function load_billing_queue(data) {
		frappe.call({method: "solua_home.api.home.get_billing_queue", args: {company: data.company}}).then(response => {
			const queue = response.message || {};
			const target = root.find('[data-role="billing"]');
			if (queue.state === "no_permission") return target.html(`<div class="text-muted">${__("无权限查看待开票数据")}</div>`);
			if (!queue.customers?.length) return target.html(`<div class="text-muted">${__("暂无待开票交货单")}</div>`);
			const groups = queue.customers.map(customer => `<details class="solua-home-billing-customer"><summary>${text(customer.customer)} · ${text(money(customer.amount, data.currency))} · ${__("最长待开票 {0} 天", [text(customer.waiting_days)])}${customer.has_draft ? ` · ${__("已有草稿")}` : ""}</summary>${(customer.jobs || []).map(job => {
				const draft = job.draft_invoices?.[0];
				return `<div class="solua-home-billing-row"><button class="solua-home-list-row" data-doctype="Delivery Note" data-name="${text(job.name)}"><span>${text(job.name)} · ${text(job.date)}</span><span>${text(money(job.amount, data.currency))} · ${text(job.waiting_days)} ${__("天")}</span></button>${draft ? job.draft_invoices.map(name => `<button class="btn btn-default btn-xs solua-home-open-invoice" data-prepare-invoice="${text(job.name)}" data-draft-name="${text(name)}">${__("打开草稿")} · ${text(name)}</button>`).join("") : (queue.can_invoice ? `<button class="btn btn-default btn-xs" data-prepare-invoice="${text(job.name)}">${__("生成发票草稿")}</button>` : "")}</div>`;
			}).join("")}</details>`).join("");
			target.html(`<div class="solua-home-pending-title">${__("共 {0} 个客户，{1} 张交货单；包含全部历史待开票交货，不受金额卡片期间限制。", [queue.count, queue.delivery_note_count])}</div><div class="text-muted solua-home-period-note">${__("显示剩余商品金额，已扣除退货及开票部分，不含税费和整单折扣。")}</div>${groups}`);
		}).catch(() => root.find('[data-role="billing"]').html(`<div class="text-muted">${__("待开票数据加载失败")}</div>`));
	}

	function load_totals(data) {
		const generation = ++totals_generation;
		const labels = {orders: "总订单金额", invoices: "总开票金额", receivable: "总应收款", paid: "总已付金额", unbilled: "未开票金额"};
		const section = root.find('[data-role="totals"]');
		section.html(Object.entries(labels).map(([key, label]) => `<button type="button" class="solua-home-card" data-total="${key}"><div class="solua-home-card-label">${text(__(label))} ›</div><div class="solua-home-card-value" data-total-value="${key}">—</div><div class="solua-home-card-state" data-total-period="${key}">${__("加载中…")}</div></button>`).join(""));
		if (common_enabled && !range_valid()) {
			root.find('[data-total]').prop("disabled", true);
			root.find('[data-total-period]').text(__("请选择有效的开始和结束日期"));
			return;
		}
		for (const metric of Object.keys(labels)) {
			let settings = {period: metric === "unbilled" ? "本年" : "本月"};
			try { settings = {...settings, ...JSON.parse(window.localStorage?.getItem(`solua-business-period:${frappe.session?.user}:${metric}`) || "{}")}; } catch (_) {}
			if (common_enabled) settings = {period: common_range.period, from_date: common_range.from_date, to_date: common_range.to_date};
			frappe.call({method: "solua_home.api.business_totals.get_total", args: {metric, company: data.company, ...settings}}).then(response => {
				if (generation !== totals_generation) return;
				const result = response.message || {};
				root.find(`[data-total-value="${metric}"]`).text(["ok", "no_data"].includes(result.state) ? money(result.amount, data.currency) : "—");
				root.find(`[data-total-period="${metric}"]`).text(result.from_date ? `${settings.period} · ${result.from_date} ~ ${result.to_date}` : state_label(result.state));
			}).catch(() => { if (generation === totals_generation) root.find(`[data-total-period="${metric}"]`).text(__("加载失败")); });
		}
	}

	// 收银员的入口：只用 POS（收银台 / 交班 / 查看自己开的 POS 销售单）
	function pos_actions(permissions) {
		return action_group(__("收银"), null, [
			utility_action(__("开始收银（xPos）"), "xpos", true),
			utility_action(__("POS交班"), "pos_closing", permissions.read_pos_closing),
			view_action(__("POS 销售单"), "POS Invoice", permissions.read_pos_invoice),
		]);
	}

	function desk_actions(permissions, stock_entry_types) {
		return [
			action_group(__("销售"), { workspace: "Selling", fallback: "Sales Order" }, [
				new_action(__("新建销售订单"), "Sales Order", permissions.new_sales_order),
				view_action(__("销售订单"), "Sales Order", permissions.read_sales_order),
				report_action(__("销售订单分析报表"), "Sales Order Analysis", permissions.read_sales_order),
				report_action(__("物料销售明细"), "Item-wise Sales History", permissions.read_sales_order),
				new_action(__("新建交货单"), "Delivery Note", permissions.new_delivery_note),
				utility_action(__("按销售订单开交货单"), "delivery_from_order", permissions.new_delivery_note),
				view_action(__("交货单"), "Delivery Note", permissions.read_delivery_note),
				report_action(__("送货汇总报表"), "Solua Delivery Summary", permissions.read_delivery_note),
				view_action(__("拣货单"), "Pick List", permissions.read_pick_list),
				view_action(__("销售发票"), "Sales Invoice", permissions.read_sales_invoice),
				report_action(__("销售发票明细报表"), "Sales Register", permissions.read_sales_invoice),
				filtered_action(__("待完成发票草稿"), "Sales Invoice", permissions.read_sales_invoice, {docstatus: 0}),
				filtered_action(__("销售退货"), "Sales Invoice", permissions.read_sales_invoice, {is_return: 1}),
				view_action(__("POS 销售单"), "POS Invoice", permissions.read_pos_invoice),
				view_action(__("报价单"), "Quotation", permissions.read_quotation),
				view_action(__("客户/门店"), "Customer", permissions.read_customer),
				view_action(__("价格表"), "Item Price", permissions.read_item_price),
				utility_action(__("优惠/促销管理"), "promotion", permissions.new_pricing_rule),
			], Boolean(permissions.read_sales_order || permissions.new_sales_order || permissions.read_delivery_note || permissions.new_delivery_note || permissions.read_sales_invoice || permissions.read_pos_invoice || permissions.read_quotation || permissions.new_pricing_rule)),
			action_group(__("库存"), { workspace: "Stock", fallback: "Item" }, [
				new_action(__("新建物料"), "Item", permissions.new_item),
				view_action(__("物料列表"), "Item", permissions.read_item),
				report_action(__("库存树报表"), "Template Stock Tree", permissions.read_bin, {warehouse: current_warehouse}),
				report_action(__("库存余额报表"), "Stock Balance", permissions.read_stock_ledger && permissions.read_item, {warehouse: current_warehouse ? [current_warehouse] : []}),
				report_action(__("库存流水报表"), "Stock Ledger", permissions.read_stock_ledger && permissions.read_item, {warehouse: current_warehouse ? [current_warehouse] : []}),
				action(__("库存入库"), "Stock Entry", null, permissions.new_stock_entry, { purpose: "Material Receipt", stock_entry_type: "Material Receipt" }),
				action(__("物料出库"), "Stock Entry", null, permissions.new_stock_entry, { purpose: "Material Issue", stock_entry_type: stock_entry_types.issue || "Material Issue" }),
				action(__("领用"), "Stock Entry", null, permissions.new_stock_entry, { purpose: "Material Issue", stock_entry_type: stock_entry_types.consumption || "领用" }),
				action(__("损耗"), "Stock Entry", null, permissions.new_stock_entry, { purpose: "Material Issue", stock_entry_type: stock_entry_types.wastage || "损耗" }),
				view_action(__("出入库记录"), "Stock Entry", permissions.read_stock_entry),
				new_action(__("手机扫码盘点"), "Stock Reconciliation", permissions.new_stock_reconciliation),
				view_action(__("盘点单"), "Stock Reconciliation", permissions.read_stock_reconciliation),
				view_action(__("仓库与库位"), "Warehouse", permissions.read_warehouse),
			], Boolean(permissions.read_item || permissions.new_item || permissions.new_stock_entry || permissions.read_stock_entry || permissions.read_stock_reconciliation || permissions.read_warehouse)),
			action_group(__("采购"), { workspace: "Buying", fallback: "Purchase Order" }, [
				new_action(__("新建采购订单"), "Purchase Order", permissions.new_purchase_order),
				view_action(__("采购订单"), "Purchase Order", permissions.read_purchase_order),
				new_action(__("采购收货"), "Purchase Receipt", permissions.new_purchase_receipt),
				view_action(__("收货记录"), "Purchase Receipt", permissions.read_purchase_receipt),
				view_action(__("采购发票"), "Purchase Invoice", permissions.read_purchase_invoice),
				view_action(__("供应商"), "Supplier", permissions.read_supplier),
			], Boolean(permissions.read_purchase_order || permissions.new_purchase_order || permissions.new_purchase_receipt || permissions.read_purchase_receipt || permissions.read_purchase_invoice || permissions.read_supplier)),
			action_group(__("财务"), { workspace: "Invoicing", fallback: "Sales Invoice" }, [
				report_action(__("经营金额报表"), "Solua Business Totals", permissions.read_sales_invoice),
				report_action(__("应收账款报表"), "Accounts Receivable", permissions.read_sales_invoice, {report_date: dashboard_data?.query_time?.slice(0, 10)}),
				report_action(__("销售毛利报表"), "Gross Profit", permissions.read_sales_invoice),
				filtered_action(__("未收款发票"), "Sales Invoice", permissions.read_sales_invoice, {docstatus: 1, outstanding_amount: [">", 0]}),
				view_action(__("销售发票"), "Sales Invoice", permissions.read_sales_invoice),
				utility_action(__("销售发票提交检查"), "sales_invoice_approval", permissions.read_sales_invoice),
				view_action(__("采购发票"), "Purchase Invoice", permissions.read_purchase_invoice),
				new_action(__("新建收款单"), "Payment Entry", permissions.new_payment_entry),
				view_action(__("收付款单"), "Payment Entry", permissions.read_payment_entry),
			], Boolean(permissions.read_sales_invoice || permissions.read_purchase_invoice || permissions.read_payment_entry || permissions.new_payment_entry)),
			action_group(__("打印与标签"), { doctype: "Print Format" }, [
				utility_action(__("打印设置"), "print_settings", permissions.read_print_settings),
				utility_action(__("打印设计"), "print_designer", permissions.read_print_format),
				utility_action(__("A4 打印设计器"), "a4_print_designer", permissions.read_print_format),
				utility_action(__("销售单格式"), "wholesale_print_format", permissions.read_print_format),
				utility_action(__("标签打印"), "label_print", permissions.read_item),
			], Boolean(permissions.read_print_settings || permissions.read_print_format || permissions.read_item)),
			action_group(__("其他入口"), null, [
				utility_action(__("POS交班"), "pos_closing", permissions.read_pos_closing),
				utility_action(__("公开色卡"), "colors", true),
				utility_action(__("xPos 收银台"), "xpos", true),
			]),
		].join("");
	}

	function load() {
		root.find('[data-role="state"]').text(__("加载中…"));
		for (const role of ["cards", "pending", "actions", "data-status"]) root.find(`[data-role="${role}"]`).html("");
		frappe.call({ method: "solua_home.api.home.get_dashboard_data" }).then((response) => {
			if (response.message?.state === "ok") render(response.message);
			else root.find('[data-role="state"]').text(state_label(response.message?.state) || __("加载失败"));
		}).catch(() => root.find('[data-role="state"]').text(__("加载失败，请检查权限或网络")));
	}

	function open_print_format_editor() {
		const route_to_format = (exists) => {
			if (exists) return frappe.set_route("Form", "Print Format", WHOLESALE_INVOICE_FORMAT);
			frappe.route_options = { doc_type: "Sales Invoice" };
			frappe.set_route("List", "Print Format");
		};
		if (frappe.db?.exists) {
			return frappe.db.exists("Print Format", WHOLESALE_INVOICE_FORMAT)
				.then((exists) => route_to_format(Boolean(exists)))
				.catch(() => route_to_format(true));
		}
		route_to_format(true);
	}

	function open_delivery_from_order() {
		if (typeof frappe.ui.Dialog !== "function") {
			return frappe.msgprint(__("当前环境不支持按订单开单，请新建交货单后选择销售订单。"));
		}
		const dialog = new frappe.ui.Dialog({
			title: __("按销售订单创建交货单"),
			fields: [{
				fieldname: "sales_order",
				label: __("销售订单"),
				fieldtype: "Link",
				options: "Sales Order",
				reqd: 1,
				description: __("仅列出已确认且尚未全部交付的订单"),
				get_query: () => ({
					filters: {
						docstatus: 1,
						per_delivered: ["<", 100],
						status: ["not in", ["Closed", "Completed", "Cancelled"]],
					},
				}),
			}],
			primary_action_label: __("创建交货单"),
			primary_action(values) {
				if (!values.sales_order) return;
				dialog.hide();
				frappe.call({
					method: "erpnext.selling.doctype.sales_order.sales_order.make_delivery_note",
					args: { source_name: values.sales_order },
					freeze: true,
					freeze_message: __("正在按订单生成交货单…"),
					callback: (response) => {
						if (!response.message) return;
						frappe.model.sync(response.message);
						frappe.set_route("Form", "Delivery Note", response.message.name);
					},
				});
			},
		});
		dialog.show();
	}

	root.on("click", "[data-issue-toggle]", function () {
		root.find(`[data-issue-body="${this.dataset.issueToggle}"]`).toggleClass("solua-home-issue-open");
		if (this.classList) this.classList.toggle("solua-home-issue-open");
	});
	root.on("click", "[data-action=refresh]", load);
	root.on("click", "[data-report], [data-total]", function () {
		if (this.dataset.total) {
			if (common_enabled && !range_valid()) return frappe.msgprint(__("请选择有效的开始和结束日期"));
			frappe.route_options = {metric: this.dataset.total, company: dashboard_data?.company, ...(common_enabled ? {...common_range, use_route_period: 1} : {})};
			return frappe.set_route("query-report", "Solua Business Totals");
		}
		frappe.route_options = JSON.parse(this.dataset.reportFilters || "{}");
		frappe.set_route("query-report", this.dataset.report);
	});
	root.on("click", "[data-action=search]", () => {
		const query = root.find('[data-role="search"]').val().trim();
		if (!query) return;
		frappe.call({ method: "solua_home.api.home.search_items", args: { query, company: dashboard_data?.company, warehouse: current_warehouse } }).then((response) => {
			const rows = response.message?.items || [];
			const stock_tree_filters = {company: dashboard_data?.company, warehouse: response.message?.warehouse};
			const stock_tree_link = dashboard_data?.permissions?.read_bin ? ` · <button class="btn btn-link btn-xs" data-report="Template Stock Tree" data-report-filters='${text(JSON.stringify(stock_tree_filters))}'>${__("打开库存树")}</button>` : "";
			root.find('[data-role="results"]').html(rows.length ? `<div class="text-muted">${__("库存仓库：{0}", [text(response.message.warehouse || "—")])}${stock_tree_link}</div>` + rows.map((row) => {
				const color = row.color || "";
				const color_code = row.color_code && row.color_code !== color ? ` · ${__("色号")} ${text(row.color_code)}` : "";
				const stock = row.stock_state === "ok" ? `${__("实际")} ${text(row.actual_qty)} / ${__("预留")} ${text(row.reserved_qty)} / ${__("可用")} ${text(row.available_qty)} ${text(row.stock_uom)}` : row.stock_state === "no_data" ? text(__("当前仓库没有库存记录")) : text(__("无权限查看库存"));
				return `<button class="solua-home-list-row" data-doctype="Item" data-name="${text(row.name)}"><span>${text(row.item_code || row.name)}${row.item_code !== row.name ? ` · ${text(row.name)}` : ""}</span><span>${row.has_variants ? `${text(row.template_name || row.item_name)} · ${text(__("模板，按颜色查看库存"))}` : `${text(row.template_name || row.item_name)}${color ? ` · ${text(color)}` : ""}${color_code} · ${stock}`}</span></button>`;
			}).join("") : `<div class="text-muted">${text(state_label(response.message?.state), __("未找到"))}</div>`);
		}).catch(() => root.find('[data-role="results"]').html(`<div class="text-muted">${__("查询失败，请刷新后重试")}</div>`));
	});
	root.on("click", "[data-prepare-invoice]", function () {
		const button = this; button.disabled = true;
		frappe.call({method: "solua_home.api.unbilled.prepare_invoice", args: {delivery_note: this.dataset.prepareInvoice}, freeze: true, freeze_message: __("正在核对未开票数量…")}).then(response => {
			const result = response.message || {};
			if (button.dataset.draftName) {
				if (!result.draft_invoices?.includes(button.dataset.draftName)) return frappe.msgprint(__("该草稿已不存在，请刷新待开票清单。"));
				return frappe.set_route("Form", "Sales Invoice", button.dataset.draftName);
			}
			if (result.draft_invoices?.length === 1) return frappe.set_route("Form", "Sales Invoice", result.draft_invoices[0]);
			if (result.draft_invoices?.length > 1) { frappe.route_options = {name: ["in", result.draft_invoices]}; return frappe.set_route("List", "Sales Invoice"); }
			if (!result.invoice) return;
			frappe.model.sync(result.invoice);
			frappe.set_route("Form", "Sales Invoice", result.invoice.name);
			frappe.show_alert({message: __("发票草稿已打开，尚未保存"), indicator: "orange"});
		}).catch(() => frappe.msgprint(__("无法生成发票草稿，请刷新队列后重试。"))).finally(() => { button.disabled = false; });
	});
	root.on("click", "[data-focus-search]", () => root.find('[data-role="search"]').trigger("focus"));
	root.on("click", "[data-scroll]", function () { root.find(`[data-section="${this.dataset.scroll}"]`)[0]?.scrollIntoView({behavior: "smooth"}); });
	root.on("change", "[data-common-enabled]", function () {
		common_enabled = !!this.checked;
		window.localStorage?.setItem(common_key, JSON.stringify({...common_range, enabled: common_enabled}));
		sync_period_controls(); load_totals(dashboard_data);
	});
	root.on("change", "[data-common-period]", function () {
		common_range.period = this.value;
		window.localStorage?.setItem(common_key, JSON.stringify({...common_range, enabled: common_enabled}));
		sync_period_controls(); load_totals(dashboard_data);
	});
	root.on("change", "[data-common-from], [data-common-to]", function () {
		common_range[this.dataset.commonFrom !== undefined ? "from_date" : "to_date"] = this.value;
		window.localStorage?.setItem(common_key, JSON.stringify({...common_range, enabled: common_enabled}));
		load_totals(dashboard_data);
	});
	root.find('[data-role="search"]').on("keydown", (event) => { if (event.key === "Enter") root.find('[data-action="search"]').click(); });
	root.on("click", ".solua-home-group-title-link, .solua-home-action, .solua-home-list-row, [data-sidebar-open]", function (event) {
		if (this.dataset.sidebarOpen) {
			const sidebar = frappe.app?.sidebar;
			if (sidebar?.setup && sidebar?.open) { sidebar.setup("Solua Wholesale"); sidebar.open(); return; }
			return window.open("/desk/solua-home?sidebar=Solua%20Wholesale", "_blank", "noopener");
		}
		if (this.tagName === "A") {
			if (event?.metaKey || event?.ctrlKey || event?.shiftKey || event?.button !== 0) return;
			event.preventDefault();
		}
		const doctype = this.dataset.doctype;
		const utility = this.dataset.utility;
		if (this.dataset.workspace) return open_workspace(this.dataset.workspace, this.dataset.fallbackView || doctype || null);
		if (utility === "print_settings") return frappe.set_route("Form", "Print Settings");
		if (utility === "print_designer") return frappe.set_route("print-designer");
		if (utility === "a4_print_designer") return frappe.set_route("a4-print-designer");
		if (utility === "wholesale_print_format") return open_print_format_editor();
		if (utility === "sales_invoice_approval") return frappe.set_route("sales-invoice-approval");
		if (utility === "label_print") {
			if (typeof window.solua_home?.label_print?.open === "function") return window.solua_home.label_print.open();
			return frappe.msgprint(__("标签打印功能尚未加载，请刷新后重试。"));
		}
		if (utility === "promotion") {
			if (typeof window.solua_home?.promotion_wizard?.open === "function") return window.solua_home.promotion_wizard.open();
			return frappe.msgprint(__("优惠功能尚未加载，请刷新后重试。"));
		}
		if (utility === "pos_closing") {
			if (typeof window.solua_home?.pos?.open_closing === "function") return window.solua_home.pos.open_closing();
			return frappe.msgprint(__("POS交班功能尚未加载，请刷新后重试。"));
		}
		if (utility === "colors") return window.open("/colors", "_blank");
		if (utility === "xpos") return window.open("/desk/x-pos?sidebar=X%20POS", "_blank", "noopener");
		if (utility === "delivery_from_order") return open_delivery_from_order();
		if (!doctype) return;
		if (doctype === "Stock Entry" && this.dataset.purpose) {
			// Always replace route_options so a previous stock operation cannot leak
			// into the next one when the user returns to the homepage.
			frappe.route_options = {
				purpose: this.dataset.purpose,
				stock_entry_type: this.dataset.stockEntryType || this.dataset.purpose,
			};
			return frappe.new_doc("Stock Entry");
		}
		if (this.dataset.newDoc) {
			frappe.route_options = null;
			return frappe.new_doc(doctype);
		}
		// Deep link with filters: the item list opens narrowed down to the offending records.
		if (this.dataset.filters) {
			let filters = null;
			try { filters = JSON.parse(this.dataset.filters); } catch (error) { filters = null; }
			frappe.route_options = filters;
			return route(doctype, null);
		}
		if (this.dataset.view === "list") {
			frappe.route_options = null;
			return route(doctype, null);
		}
		if (!this.dataset.name && ["Sales Order", "Delivery Note", "Purchase Receipt", "Stock Reconciliation"].includes(doctype)) return frappe.new_doc(doctype);
		route(doctype, this.dataset.name || null);
	});
	load();
	wrapper.solua_home_refresh = load;
};

frappe.pages["solua-home"].on_page_show = wrapper => {
 if (wrapper.solua_home_shown) wrapper.solua_home_refresh?.();
 wrapper.solua_home_shown = true;
};
