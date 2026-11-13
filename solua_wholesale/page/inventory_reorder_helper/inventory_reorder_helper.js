frappe.pages["inventory-reorder-helper"].on_page_load = function (wrapper) {
	const page = frappe.ui.make_app_page({
		parent: wrapper,
		title: __("库存预警辅助填写"),
		single_column: true,
	});

	page.main = $(wrapper).find(".layout-main-section");
	page.main.html(`
		<div class="solua-reorder-page">
			<div class="solua-reorder-toolbar">
				<div>
					<div class="solua-reorder-eyebrow">${__("库存预警与补货建议")}</div>
					<h1>${__("库存预警辅助填写")}</h1>
					<p class="text-muted">${__("先审核建议数量，再批量写入物料的 Re-order Level 和 Re-order Qty。")}</p>
				</div>
				<div class="solua-reorder-actions">
					<button class="btn btn-default solua-reorder-select-alert" type="button">${__("选择需处理")}</button>
					<button class="btn btn-default solua-reorder-clear" type="button">${__("清除选择")}</button>
					<button class="btn btn-default solua-reorder-use-suggested" type="button">${__("选中项采用建议")}</button>
					<button class="btn btn-primary solua-reorder-refresh" type="button">${__("刷新计算")}</button>
					<button class="btn btn-primary solua-reorder-apply" type="button">${__("预览并写入")}</button>
				</div>
			</div>

			<div class="solua-reorder-filters">
				<label>${__("仓库")}<input class="form-control solua-reorder-warehouse" value="Receiving - SH"></label>
				<label>${__("补货周期（天）")}<input class="form-control solua-reorder-lead" type="number" min="1" max="365" value="60"></label>
				<label>${__("安全缓冲（天）")}<input class="form-control solua-reorder-buffer" type="number" min="0" max="90" value="14"></label>
				<div class="solua-reorder-formula">
					<strong>${__("计算公式")}</strong>
					<span>${__("日均净销量 ×（补货周期 + 安全缓冲）")}</span>
				</div>
			</div>

			<div class="solua-reorder-summary text-muted"></div>
			<div class="solua-reorder-preview" hidden></div>
			<div class="solua-reorder-table-wrap">
				<div class="solua-reorder-loading text-muted">${__("正在读取销售和库存数据…")}</div>
			</div>
		</div>
	`);

	const state = { rows: [], data: null };

	const esc = (value) => frappe.utils.escape_html(String(value ?? ""));
	const num = (value) => Number(value || 0).toLocaleString(undefined, { maximumFractionDigits: 3 });
	const statusClass = (status) => {
		if (status === "缺货或已被预留") return "is-danger";
		if (status === "达到建议预警线" || status === "预计补货前不足") return "is-warning";
		if (status === "库存充足") return "is-ok";
		return "is-muted";
	};
	const filters = () => ({
		warehouse: page.main.find(".solua-reorder-warehouse").val().trim(),
		lead_days: page.main.find(".solua-reorder-lead").val(),
		buffer_days: page.main.find(".solua-reorder-buffer").val(),
	});

	const selectedRows = () =>
		state.rows.filter((row) => page.main.find(`.solua-reorder-check[data-item-code="${CSS.escape(row.item_code)}"]`).prop("checked"));

	const readChanges = () =>
		selectedRows().map((row) => {
			const code = CSS.escape(row.item_code);
			return {
				item_code: row.item_code,
				warehouse: state.data.warehouse,
				reorder_level: Number(page.main.find(`.solua-reorder-level[data-item-code="${code}"]`).val() || 0),
				reorder_qty: Number(page.main.find(`.solua-reorder-qty[data-item-code="${code}"]`).val() || 0),
				before_level: Number(row.current_reorder_level || 0),
				before_qty: Number(row.current_reorder_qty || 0),
			};
		});

	const renderPreview = (changes) => {
		if (!changes.length) {
			page.main.find(".solua-reorder-preview").prop("hidden", false).html(
				`<div class="alert alert-warning">${__("请先勾选需要写入的物料。")}</div>`,
			);
			return;
		}
		const lines = changes
			.map(
				(change) => `
					<tr>
						<td>${esc(change.item_code)}</td>
						<td>${num(change.before_level)} → <strong>${num(change.reorder_level)}</strong></td>
						<td>${num(change.before_qty)} → <strong>${num(change.reorder_qty)}</strong></td>
					</tr>`,
			)
			.join("");
		page.main.find(".solua-reorder-preview").prop("hidden", false).html(`
			<div class="solua-reorder-preview-card">
				<div><strong>${__("修改前后对比")}</strong><span>${changes.length} ${__("条物料")}</span></div>
				<table class="table table-bordered table-sm">
					<thead><tr><th>${__("货号")}</th><th>Re-order Level</th><th>Re-order Qty</th></tr></thead>
					<tbody>${lines}</tbody>
				</table>
				<div class="text-muted">${__("确认无误后，再点击“预览并写入”完成保存。")}</div>
			</div>
		`);
	};

	const renderRows = () => {
		if (!state.rows.length) {
			page.main.find(".solua-reorder-table-wrap").html(
				`<div class="alert alert-info">${__("当前筛选条件没有可显示的库存物料。")}</div>`,
			);
			return;
		}
		const rows = state.rows
			.map((row) => {
				const code = esc(row.item_code);
				const checked = row.status !== "库存充足" && row.status !== "暂无近90天净出库" ? "checked" : "";
				return `
					<tr>
						<td><input class="solua-reorder-check" type="checkbox" data-item-code="${code}" ${checked}></td>
						<td><a href="/app/item/${encodeURIComponent(row.item_code)}" target="_blank">${code}</a></td>
						<td>${esc(row.item_name)}</td>
						<td><span class="solua-reorder-status ${statusClass(row.status)}">${esc(row.status)}</span></td>
						<td class="text-right">${num(row.suggested_warning)}</td>
						<td class="text-right">${num(row.current_reorder_level)}</td>
						<td><input class="form-control input-sm solua-reorder-level" data-item-code="${code}" type="number" min="0" value="${num(row.suggested_warning)}"></td>
						<td class="text-right">${num(row.suggested_order_qty)}</td>
						<td><input class="form-control input-sm solua-reorder-qty" data-item-code="${code}" type="number" min="0" value="${num(row.suggested_order_qty)}"></td>
						<td class="text-right">${num(row.actual_qty)}</td>
						<td class="text-right">${num(row.reserved_qty)}</td>
						<td class="text-right">${num(row.projected_qty)}</td>
						<td class="text-right">${num(row.daily_sales)}</td>
					</tr>`;
			})
			.join("");

		page.main.find(".solua-reorder-table-wrap").html(`
			<table class="table table-bordered solua-reorder-table">
				<thead>
					<tr>
						<th><input class="solua-reorder-check-all" type="checkbox"></th>
						<th>${__("货号")}</th>
						<th>${__("物料")}</th>
						<th>${__("状态")}</th>
						<th>${__("建议预警")}</th>
						<th>${__("当前预警")}</th>
						<th>${__("确认预警")}</th>
						<th>${__("建议订货")}</th>
						<th>${__("确认订货")}</th>
						<th>${__("现货")}</th>
						<th>${__("已预留")}</th>
						<th>${__("预计库存")}</th>
						<th>${__("日均销量")}</th>
					</tr>
				</thead>
				<tbody>${rows}</tbody>
			</table>
		`);
		page.main.find(".solua-reorder-summary").text(
			`${__("共")} ${state.rows.length} ${__("条物料，已自动选择需要处理的项目。")}`,
		);
	};

	const load = () => {
		const current = filters();
		page.main.find(".solua-reorder-refresh").prop("disabled", true);
		page.main.find(".solua-reorder-table-wrap").html(
			`<div class="solua-reorder-loading text-muted">${__("正在读取销售和库存数据…")}</div>`,
		);
		frappe.call({
			method: "solua_home.api.inventory_reorder.get_inventory_reorder_rows",
			args: current,
		})
			.then((response) => {
				state.data = response.message || {};
				state.rows = state.data.rows || [];
				page.main.find(".solua-reorder-preview").prop("hidden", true).empty();
				renderRows();
			})
			.catch(() => {
				page.main.find(".solua-reorder-table-wrap").html(
					`<div class="alert alert-danger">${__("读取失败，请检查仓库名称或联系管理员。")}</div>`,
				);
			})
			.finally(() => page.main.find(".solua-reorder-refresh").prop("disabled", false));
	};

	page.main.find(".solua-reorder-refresh").on("click", load);
	page.main.find(".solua-reorder-select-alert").on("click", () => {
		page.main.find(".solua-reorder-check").prop("checked", true);
		page.main.find(".solua-reorder-check-all").prop("checked", true);
	});
	page.main.find(".solua-reorder-clear").on("click", () => {
		page.main.find(".solua-reorder-check, .solua-reorder-check-all").prop("checked", false);
	});
	page.main.find(".solua-reorder-check-all").on("change", function () {
		page.main.find(".solua-reorder-check").prop("checked", $(this).prop("checked"));
	});
	page.main.find(".solua-reorder-use-suggested").on("click", () => {
		selectedRows().forEach((row) => {
			const code = CSS.escape(row.item_code);
			page.main.find(`.solua-reorder-level[data-item-code="${code}"]`).val(row.suggested_warning);
			page.main.find(`.solua-reorder-qty[data-item-code="${code}"]`).val(row.suggested_order_qty);
		});
		renderPreview(readChanges());
	});
	page.main.find(".solua-reorder-apply").on("click", () => {
		const changes = readChanges();
		renderPreview(changes);
		if (!changes.length) return;
		frappe.confirm(
			__("确认把这些数量写入对应物料的 Re-order Level 和 Re-order Qty 吗？"),
			() => {
				frappe.call({
					method: "solua_home.api.inventory_reorder.apply_inventory_reorder_changes",
					args: { changes: JSON.stringify(changes), warehouse: state.data.warehouse },
				}).then((response) => {
					const updated = response.message?.updated || 0;
					frappe.show_alert({ message: __(`已更新 ${updated} 条物料`), indicator: "green" });
					load();
				});
			},
		);
	});

	load();
};
