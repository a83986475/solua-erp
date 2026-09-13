// solua_home: Item 模板的颜色库存汇总面板。

frappe.ui.form.on("Item", {
	custom_color_code(frm) {
		if (!frm.fields_dict.custom_order_code || !frm.doc.variant_of || frm.doc.custom_order_code) return;
		const colorCode = String(frm.doc.custom_color_code || "").trim();
		if (colorCode) frm.set_value("custom_order_code", `${frm.doc.variant_of}-${colorCode}`);
	},

	refresh(frm) {
		if (frm.is_new() || !frm.doc.has_variants) return;

		const previous = frm.dashboard.wrapper.find(".solua-color-stock-section");
		if (previous.length) previous.remove();

		const section = $(frm.dashboard.add_section("", __("颜色库存")));
		section.addClass("solua-color-stock-section");
		const body = $("<div class='solua-color-stock-body'></div>").appendTo(section);
		const esc = (value) => String(value == null ? "" : value)
			.replace(/&/g, "&amp;")
			.replace(/</g, "&lt;")
			.replace(/>/g, "&gt;")
			.replace(/\"/g, "&quot;");

		body.html(`
			<div class="form-inline" style="margin-bottom:12px">
				<label style="margin-right:6px">${__("仓库")}</label>
				<select class="form-control input-sm js-color-stock-warehouse">
					<option value="">${__("全部有权限仓库")}</option>
				</select>
				<button class="btn btn-default btn-sm js-color-stock-refresh" style="margin-left:6px">
					${__("刷新")}
				</button>
			</div>
			<div class="text-muted js-color-stock-status">${__("加载中...")}</div>
			<div class="js-color-stock-table"></div>
		`);

		const warehouseSelect = body.find(".js-color-stock-warehouse");
		const table = body.find(".js-color-stock-table");
		const status = body.find(".js-color-stock-status");

		const load = () => {
			status.text(__("加载中..."));
			table.empty();
			frappe.call({
				method: "solua_home.api.variants.get_template_stock_summary",
				args: { template_item: frm.doc.name, warehouse: warehouseSelect.val() || null },
				callback: (r) => {
					if (r.exc || !r.message) {
						status.text(__("库存加载失败，请检查权限或稍后重试。"));
						return;
					}
					const data = r.message;
					status.text(__("库存数量以服务器已入账数据为准。"));
					let rows = "";
					(data.variants || []).forEach((variant) => {
						const color = variant.color_code || (variant.attributes || {}).Cor || "";
						const name = variant.custom_chinese_name || variant.item_name || variant.item_code;
						const code = variant.custom_order_code || variant.item_code;
						rows += `<tr>
							<td>${esc(code)}</td>
							<td>${esc(color)}</td>
							<td>${esc(name)}</td>
							<td class="text-right">${esc(variant.actual_qty)}</td>
							<td>${esc(variant.stock_uom || "")}</td>
						</tr>`;
					});
					table.html(`<div style="overflow:auto">
						<table class="table table-bordered table-condensed" style="margin:0;min-width:650px">
							<thead><tr>
								<th>${__("订货货号")}</th><th>${__("色号")}</th><th>${__("颜色")}</th>
								<th class="text-right">${__("库存")}</th><th>${__("单位")}</th>
							</tr></thead>
							<tbody>${rows || `<tr><td colspan="5" class="text-muted">${__("暂无已启用变体")}</td></tr>`}</tbody>
							<tfoot><tr class="font-weight-bold">
								<td colspan="3">${esc(data.template_code)} ${__("整款合计")}</td>
								<td class="text-right">${esc(data.total_stock)}</td><td></td>
							</tr></tfoot>
						</table>
					</div>`);
				},
			});
		};

		frappe.db.get_list("Warehouse", {
			filters: { is_group: 0, disabled: 0 },
			fields: ["name"],
			order_by: "name asc",
			limit: 500,
		}).then((warehouses) => {
			(warehouses || []).forEach((warehouse) => {
				warehouseSelect.append($("<option>", { value: warehouse.name, text: warehouse.name }));
			});
		});

		warehouseSelect.on("change", load);
		body.find(".js-color-stock-refresh").on("click", load);
		load();
		frm.dashboard.show();
	},
});
