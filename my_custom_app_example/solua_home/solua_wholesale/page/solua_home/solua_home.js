frappe.pages["solua-home"].on_page_load = function (wrapper) {
	const page = frappe.ui.make_app_page({ parent: wrapper, title: __("Solua Home"), single_column: true });
	page.main.html(`
		<div class="solua-home-page">
			<div class="solua-home-header">
				<div><div class="solua-home-brand"><img class="solua-home-logo" src="/files/solua-logo.jpg" alt="Solua Home">Solua Home</div><div class="solua-home-subtitle">批发经营 · 订单履约 · 配送与库存</div></div>
				<div class="solua-home-header-actions"><span class="solua-home-meta" data-role="company"></span><span class="solua-home-meta" data-role="date"></span><button class="btn btn-sm btn-default" data-action="refresh">${__("刷新")}</button></div>
			</div>
			<div class="solua-home-state" data-role="state">${__("加载中…")}</div>
			<section class="solua-home-section"><h3>${__("经营概览")}</h3><div class="solua-home-cards" data-role="cards"></div></section>
			<div class="solua-home-columns">
				<section class="solua-home-section"><h3>${__("待处理")}</h3><div data-role="pending"></div></section>
				<section class="solua-home-section"><h3>${__("商品查找")}</h3><div class="solua-home-search"><input class="form-control" data-role="search" placeholder="${__("款号、对外货号或原包装条码")}"><button class="btn btn-default" data-action="search">${__("查找")}</button></div><div data-role="results"></div></section>
			</div>
			<section class="solua-home-section"><h3>${__("快捷操作")}</h3><div class="solua-home-actions" data-role="actions"></div></section>
			<section class="solua-home-section"><h3>${__("资料准备")}</h3><div data-role="data-status"></div></section>
		</div>`);

	const root = page.main;
	const text = (value, fallback = "—") => frappe.utils.escape_html(String(value ?? fallback));
	const money = (value, currency) => value == null ? "—" : format_currency(value, currency);
	const route = (doctype, name) => frappe.set_route(name ? "Form" : "List", doctype, name);
	const state_label = (state) => ({ no_permission: __("无权限"), no_data: __("暂无数据"), incomplete: __("库存明细不完整，无法汇总"), error: __("加载失败") }[state] || "");

	function action(label, doctype, name, allowed = false) {
		if (!allowed) return "";
		const purpose = arguments[4]?.purpose || "";
		const new_doc = arguments[4]?.new_doc ? ` data-new-doc="1"` : "";
		return `<button class="btn btn-default btn-sm solua-home-action" data-doctype="${text(doctype)}" data-name="${text(name || "")}"${purpose ? ` data-purpose="${text(purpose)}"` : ""}${new_doc}>${text(label)}</button>`;
	}

	function utility_action(label, key, allowed = false) {
		if (!allowed) return "";
		return `<button class="btn btn-default btn-sm solua-home-action" data-utility="${text(key)}">${text(label)}</button>`;
	}

	function action_group(title, buttons) {
		const visible = buttons.filter(Boolean);
		return visible.length ? `<div class="solua-home-action-group"><h4>${text(title)}</h4><div class="solua-home-actions">${visible.join("")}</div></div>` : "";
	}

	function render(data) {
		root.find('[data-role="company"]').text(data.company || "");
		root.find('[data-role="date"]').text(data.query_time ? `${__("查询时间")} ${data.query_time}` : "");
		root.find('[data-role="state"]').text("");
		const cards = [
			[__("今日已开票额"), money(data.invoiced_today?.amount, data.currency), data.invoiced_today?.state],
			[__("客户未收款"), money(data.outstanding?.amount, data.currency), data.outstanding?.state],
			[__("已确认待交付"), data.orders_pending?.count ?? "—", data.orders_pending?.state],
			[__("今日已送货额"), money(data.delivered_today?.amount, data.currency), data.delivered_today?.state],
			[__("库存预警"), data.low_stock?.count ?? "—", data.low_stock?.state],
		];
		root.find('[data-role="cards"]').html(cards.map(([label, value, state]) => `<div class="solua-home-card"><div class="solua-home-card-label">${text(label)}</div><div class="solua-home-card-value">${["ok", "no_data"].includes(state) ? text(value) : "—"}</div><div class="solua-home-card-state">${text(state_label(state), "")}</div></div>`).join(""));
		const pending = data.orders_pending?.items || [];
		root.find('[data-role="pending"]').html([
			`<div class="solua-home-pending-title">${__("待交付订单")}：${data.orders_pending?.state === "no_permission" ? "—" : data.orders_pending?.count ?? "—"}</div>`,
			pending.length ? pending.map((row) => `<button class="solua-home-list-row" data-doctype="Sales Order" data-name="${text(row.name)}"><span>${text(row.name)}</span><span>${text(row.customer)} · ${text(row.status)}</span></button>`).join("") : `<div class="text-muted">${text(state_label(data.orders_pending?.state), __("暂无待交付订单"))}</div>`,
			`<div class="solua-home-pending-title">${__("逾期应收")}</div>`,
			(data.overdue?.items || []).length ? data.overdue.items.map((row) => `<button class="solua-home-list-row" data-doctype="${text(row.doctype || "Sales Invoice")}" data-name="${text(row.name)}"><span>${text(row.name)}</span><span>${text(row.customer)} · ${text(money(row.base_outstanding_amount, data.currency))}</span></button>`).join("") : `<div class="text-muted">${text(state_label(data.overdue?.state) || __("暂无逾期应收"))}</div>`,
			`<div class="solua-home-pending-title">${__("待到货采购订单")}</div>`,
			(data.pending_purchase?.items || []).map((row) => `<button class="solua-home-list-row" data-doctype="Purchase Order" data-name="${text(row.name)}"><span>${text(row.name)}</span><span>${text(row.supplier)} · ${text(row.status)}</span></button>`).join("") || `<div class="text-muted">${text(state_label(data.pending_purchase?.state) || __("暂无待到货"))}</div>`,
			`<div class="solua-home-pending-title">${__("库存预警")} · ${text(data.warehouse)}</div>`,
			(data.low_stock?.items || []).map((row) => `<button class="solua-home-list-row" data-doctype="Item" data-name="${text(row.name)}"><span>${text(row.item_name)}</span><span>${text(row.actual_qty)} / ${text(row.reorder_level)} ${text(row.stock_uom)}</span></button>`).join("") || `<div class="text-muted">${text(state_label(data.low_stock?.state) || __("暂无预警"))}</div>`,
		].join(""));
		const permissions = data.permissions || {};
		root.find('[data-role="actions"]').html([
			action_group(__("库存管理"), [
				action(__("新建物料"), "Item", null, permissions.new_item, { new_doc: true }),
				action(__("物料出库"), "Stock Entry", null, permissions.new_stock_entry, { purpose: "Material Issue" }),
				action(__("领用（Material Issue）"), "Stock Entry", null, permissions.new_stock_entry, { purpose: "Material Issue" }),
				action(__("损耗（Material Issue）"), "Stock Entry", null, permissions.new_stock_entry, { purpose: "Material Issue" }),
				action(__("手机扫码盘点"), "Stock Reconciliation", null, permissions.new_stock_reconciliation),
				action(__("采购收货"), "Purchase Receipt", null, permissions.new_purchase_receipt),
				action(__("查库存"), "Item", null, permissions.read_item),
			]),
			action_group(__("标签打印"), [
				utility_action(__("打印设置"), "print_settings", permissions.read_print_settings),
				utility_action(__("打印设计"), "print_designer", permissions.read_print_format),
				utility_action(__("标签打印"), "label_print", permissions.read_item),
			]),
			action_group(__("优惠/促销"), [
				utility_action(__("优惠/促销管理"), "promotion", permissions.new_pricing_rule),
			]),
			action_group(__("订单与客户"), [
				action(__("新建销售订单"), "Sales Order", null, permissions.new_sales_order),
				action(__("新建交货单"), "Delivery Note", null, permissions.new_delivery_note),
				action(__("客户/门店"), "Customer", null, permissions.read_customer),
				action(__("供应商"), "Supplier", null, permissions.read_supplier),
			]),
			action_group(__("其他入口"), [
				utility_action(__("POS交班"), "pos_closing", permissions.read_pos_closing),
				utility_action(__("公开色卡"), "colors", true),
				utility_action(__("xPos 现有入口"), "xpos", true),
			]),
		].join(""));
		root.find('[data-role="data-status"]').html(`<span>${__("商品资料")}</span>：${__("缺图片")} ${text(data.item_data?.missing_image)} · ${__("缺固定色号")} ${text(data.item_data?.missing_color_code)}<span class="text-muted">（未加载/无权限不会伪装为 0）</span>`);
	}

	function load() {
		root.find('[data-role="state"]').text(__("加载中…"));
		for (const role of ["cards", "pending", "actions", "data-status"]) root.find(`[data-role="${role}"]`).html("");
		frappe.call({ method: "solua_home.api.home.get_dashboard_data" }).then((response) => {
			if (response.message?.state === "ok") render(response.message);
			else root.find('[data-role="state"]').text(state_label(response.message?.state) || __("加载失败"));
		}).catch(() => root.find('[data-role="state"]').text(__("加载失败，请检查权限或网络")));
	}

	root.on("click", "[data-action=refresh]", load);
	root.on("click", "[data-action=search]", () => {
		const query = root.find('[data-role="search"]').val().trim();
		if (!query) return;
		frappe.call({ method: "solua_home.api.home.search_items", args: { query } }).then((response) => {
			const rows = response.message?.items || [];
			root.find('[data-role="results"]').html(rows.length ? rows.map((row) => `<button class="solua-home-list-row" data-doctype="Item" data-name="${text(row.name)}"><span>${text(row.order_code || row.item_code)}</span><span>${text(row.color_code ? `${row.color_code} · ` : "")}${text(row.color || row.item_name)}</span></button>`).join("") : `<div class="text-muted">${text(state_label(response.message?.state), __("未找到"))}</div>`);
		});
	});
	root.find('[data-role="search"]').on("keydown", (event) => { if (event.key === "Enter") root.find('[data-action="search"]').click(); });
	root.on("click", ".solua-home-action, .solua-home-list-row", function () {
		const doctype = this.dataset.doctype;
		const utility = this.dataset.utility;
		if (utility === "print_settings") return frappe.set_route("Form", "Print Settings");
		if (utility === "print_designer") return frappe.set_route("print-designer");
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
		if (!doctype) return;
		if (this.dataset.newDoc) return frappe.new_doc(doctype);
		if (doctype === "Stock Entry" && this.dataset.purpose) {
			frappe.route_options = { purpose: this.dataset.purpose };
			return frappe.new_doc("Stock Entry");
		}
		if (!this.dataset.name && ["Sales Order", "Delivery Note", "Purchase Receipt", "Stock Reconciliation"].includes(doctype)) return frappe.new_doc(doctype);
		route(doctype, this.dataset.name || null);
	});
	load();
};
