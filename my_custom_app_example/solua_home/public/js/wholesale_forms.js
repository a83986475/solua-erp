// Native-form helpers for wholesale color receiving and mobile stock counting.
(() => {
	const variant_api = "solua_home.api.home.get_color_variants";
	const sales_order_color_api = "solua_home.api.sales.get_sales_order_color_variants";
	const sales_order_item_display_api = "solua_home.api.sales.get_sales_order_item_display";
	const sales_order_upload_api = "solua_home.api.sales.preview_sales_order_upload";
	const sales_order_paste_api = "solua_home.api.sales.preview_sales_order_paste";
	const sales_order_rows_api = "solua_home.api.sales.preview_sales_order_rows";
	const sales_order_search_api = "solua_home.api.sales.search_sales_order_items";
	const print_formats = { "Sales Order": "客户订单确认单（颜色版）", "Delivery Note": "Guia de Remessa" };

	const is_positive_integer = (value) => {
		if (value == null || String(value).trim() === "") return false;
		const number = Number(value);
		return Number.isFinite(number) && Number.isInteger(number) && number > 0;
	};
	const set_table_selection = (rows, value) => rows.forEach((row) => { row.include = value ? 1 : 0; });
	const invert_table_selection = (rows) => rows.forEach((row) => { row.include = row.include ? 0 : 1; });
	if (typeof window !== "undefined") window.solua_home_sales_order_tools = { is_positive_integer, set_table_selection, invert_table_selection };

	const sales_order_context = (frm, warehouse) => ({
		company: frm.doc.company,
		customer: frm.doc.customer,
		price_list: frm.doc.selling_price_list,
		selling_price_list: frm.doc.selling_price_list,
		currency: frm.doc.currency,
		price_list_currency: frm.doc.price_list_currency,
		conversion_rate: frm.doc.conversion_rate,
		plc_conversion_rate: frm.doc.plc_conversion_rate,
		transaction_date: frm.doc.transaction_date,
		set_warehouse: warehouse || frm.doc.set_warehouse || "",
		ignore_pricing_rule: frm.doc.ignore_pricing_rule ? 1 : 0,
	});

	const error_summary = (errors) => {
		if (!errors?.length) return "";
		return `<div class="text-danger small"><b>${__("异常汇总")}</b><ul>${errors.map((error) => `<li>${frappe.utils.escape_html(error.row ? `第 ${error.row} 行：` : "")}${frappe.utils.escape_html(error.item_code ? `${error.item_code}：` : "")}${frappe.utils.escape_html(error.error || "")}</li>`).join("")}</ul></div>`;
	};

	function append_sales_order_rows(frm, rows) {
		for (const source of rows || []) {
			const qty = Number(source.qty);
			const existing = (frm.doc.items || []).find((row) => row.item_code === source.item_code && (row.warehouse || "") === (source.warehouse || ""));
			const row = existing || frm.add_child("items");
			const next_qty = (existing ? Number(existing.qty || 0) : 0) + qty;
			Object.assign(row, {
				item_code: source.item_code,
				item_name: source.item_name,
				description: source.description,
				uom: source.uom,
				stock_uom: source.stock_uom,
				conversion_factor: source.conversion_factor || 1,
				rate: source.rate,
				price_list_rate: source.price_list_rate,
				warehouse: source.warehouse,
				qty: next_qty,
				custom_item_barcode: source.custom_item_barcode || source.barcode || "",
			});
		}
		frm.dirty();
		frm.refresh_field("items");
		frm.trigger?.("calculate_taxes_and_totals");
	}

	function open_sales_order_preview(frm, result, title) {
		const data = (result.rows || []).map((row) => ({ ...row, include: 1 }));
		const dialog = new frappe.ui.Dialog({
			title,
			size: "extra-large",
			fields: [
				{ fieldtype: "HTML", fieldname: "errors", options: error_summary(result.errors) || `<div class="text-muted small">${__("没有异常")}</div>` },
				{ fieldtype: "Table", fieldname: "items", label: __("待加入订单"), cannot_add_rows: true, cannot_delete_rows: true, in_place_edit: true, data,
					fields: [
						{ fieldname: "include", label: __("加入"), fieldtype: "Check", in_list_view: 1, default: 1 },
						{ fieldname: "item_code", label: __("货号"), fieldtype: "Data", read_only: 1, in_list_view: 1 },
						{ fieldname: "item_name", label: __("商品"), fieldtype: "Data", read_only: 1, in_list_view: 1 },
						{ fieldname: "color_code", label: __("色号"), fieldtype: "Data", read_only: 1, in_list_view: 1 },
						{ fieldname: "qty", label: __("数量"), fieldtype: "Int", in_list_view: 1, reqd: 1 },
						{ fieldname: "uom", label: __("单位"), fieldtype: "Data", read_only: 1, in_list_view: 1 },
						{ fieldname: "rate", label: __("单价"), fieldtype: "Currency", read_only: 1, in_list_view: 1 },
						{ fieldname: "warehouse", label: __("仓库"), fieldtype: "Data", read_only: 1, in_list_view: 1 },
					],
				},
			],
			primary_action_label: __("加入销售订单"),
			primary_action: async () => {
				const selected = dialog.fields_dict.items.df.data.filter((row) => row.include);
				const invalid = selected.filter((row) => !is_positive_integer(row.qty));
				if (!selected.length) return frappe.msgprint(__("请至少选择一行"));
				if (invalid.length) return frappe.msgprint(__("数量必须为正整数，请先修正标红行"));
				const response = await frappe.call({ method: sales_order_rows_api, args: { rows: JSON.stringify(selected.map((row) => ({ item_code: row.item_code, qty: row.qty, warehouse: row.warehouse }))), context: JSON.stringify(sales_order_context(frm)) } });
				const resolved = response.message || {};
				append_sales_order_rows(frm, resolved.rows || []);
				if (resolved.errors?.length) frappe.msgprint({ title: __("部分行未加入"), message: error_summary(resolved.errors), indicator: "orange" });
				else frappe.show_alert({ message: __("已加入当前销售订单草稿，请保存"), indicator: "green" });
				dialog.hide();
			},
		});
		dialog.show();
	}

	function open_sales_order_upload(frm) {
		const dialog = new frappe.ui.Dialog({
			title: __("上传订单表格"),
			fields: [
				{ fieldname: "file_url", label: __("CSV/XLSX/XLS 文件"), fieldtype: "Attach", reqd: 1 },
				{ fieldtype: "HTML", options: `<div class="text-muted small">${__("必需列：货号/SKU、数量；可选列：仓库/库位。支持中文、英文常见列名；相同货号会合并数量。")}</div>` },
			],
			primary_action_label: __("读取并预览"),
			primary_action: async (values) => {
				if (!values.file_url) return frappe.msgprint(__("请先选择文件"));
				const response = await frappe.call({ method: sales_order_upload_api, args: { file_url: values.file_url, context: JSON.stringify(sales_order_context(frm)) } });
				dialog.hide();
				open_sales_order_preview(frm, response.message || {}, __("订单表格预览"));
			},
		});
		dialog.show();
	}

	function open_sales_order_paste(frm) {
		const dialog = new frappe.ui.Dialog({
			title: __("粘贴货号 + 数量"),
			fields: [{ fieldname: "text", label: __("从 Excel 复制的两列文本"), fieldtype: "Long Text", reqd: 1, description: __("第一列货号/SKU，第二列数量；可带标题行。") }],
			primary_action_label: __("读取并预览"),
			primary_action: async (values) => {
				const response = await frappe.call({ method: sales_order_paste_api, args: { text: values.text, context: JSON.stringify(sales_order_context(frm)) } });
				dialog.hide();
				open_sales_order_preview(frm, response.message || {}, __("粘贴内容预览"));
			},
		});
		dialog.show();
	}

	function open_sales_order_bulk_picker(frm) {
		let busy = false;
		const dialog = new frappe.ui.Dialog({
			title: __("批量添加物料"),
			size: "extra-large",
			fields: [
				{ fieldname: "warehouse", label: __("明确订单仓库/范围"), fieldtype: "Link", options: "Warehouse", default: frm.doc.set_warehouse || "", reqd: 1 },
				{ fieldtype: "Column Break" },
				{ fieldname: "item_group", label: __("商品组"), fieldtype: "Link", options: "Item Group" },
				{ fieldname: "template", label: __("模板"), fieldtype: "Link", options: "Item" },
				{ fieldname: "color", label: __("颜色/固定色号"), fieldtype: "Data" },
				{ fieldname: "search", label: __("搜索货号"), fieldtype: "Data" },
				{ fieldname: "in_stock", label: __("只看有库存"), fieldtype: "Check" },
				{ fieldtype: "Button", fieldname: "search_items", label: __("搜索") },
				{ fieldtype: "Button", fieldname: "select_all", label: __("当前筛选结果全选") },
				{ fieldtype: "Button", fieldname: "invert_selection", label: __("反选") },
				{ fieldtype: "HTML", fieldname: "hint", options: `<div class="text-muted small">${__("库存 = actual_qty - reserved_qty；价格由 ERPNext 当前价格逻辑读取。")}</div>` },
				{ fieldtype: "Table", fieldname: "results", label: __("物料结果"), cannot_add_rows: true, cannot_delete_rows: true, in_place_edit: true, data: [],
					fields: [
						{ fieldname: "include", label: __("加入"), fieldtype: "Check", in_list_view: 1 },
						{ fieldname: "image", label: __("图片"), fieldtype: "Attach Image", read_only: 1, in_list_view: 1 },
						{ fieldname: "item_code", label: __("货号"), fieldtype: "Data", read_only: 1, in_list_view: 1 },
						{ fieldname: "item_name", label: __("名称"), fieldtype: "Data", read_only: 1, in_list_view: 1 },
						{ fieldname: "color_code", label: __("色号"), fieldtype: "Data", read_only: 1, in_list_view: 1 },
						{ fieldname: "available_qty", label: __("可用库存"), fieldtype: "Float", read_only: 1, in_list_view: 1 },
						{ fieldname: "wholesale_rate", label: __("Wholesale Selling"), fieldtype: "Currency", read_only: 1, in_list_view: 1 },
						{ fieldname: "standard_selling_rate", label: __("Standard Selling"), fieldtype: "Currency", read_only: 1, in_list_view: 1 },
						{ fieldname: "qty", label: __("数量"), fieldtype: "Int", default: 1, in_list_view: 1 },
						{ fieldname: "warehouse", label: __("仓库"), fieldtype: "Data", read_only: 1, in_list_view: 1 },
						{ fieldname: "status", label: __("状态"), fieldtype: "Data", read_only: 1, in_list_view: 1 },
					],
				},
			],
			primary_action_label: __("加入销售订单"),
			primary_action: async () => {
				if (busy) return;
				const rows = dialog.fields_dict.results.df.data.filter((row) => row.include);
				const invalid = rows.filter((row) => !is_positive_integer(row.qty));
				if (!rows.length) return frappe.msgprint(__("请先勾选物料"));
				if (invalid.length) return frappe.msgprint(__("数量必须为正整数"));
				busy = true;
				try {
					const response = await frappe.call({ method: sales_order_rows_api, args: { rows: JSON.stringify(rows.map((row) => ({ item_code: row.item_code, qty: row.qty, warehouse: row.warehouse }))), context: JSON.stringify(sales_order_context(frm, dialog.get_value("warehouse"))) } });
					const result = response.message || {};
					append_sales_order_rows(frm, result.rows || []);
					if (result.errors?.length) frappe.msgprint({ title: __("部分行未加入"), message: error_summary(result.errors), indicator: "orange" });
					else frappe.show_alert({ message: __("已加入当前销售订单草稿，请保存"), indicator: "green" });
					dialog.hide();
				} finally { busy = false; }
			},
		});
		const set_selection = (value) => {
			set_table_selection(dialog.fields_dict.results.df.data, value);
			dialog.fields_dict.results.grid.refresh();
		};
		const invert_selection = () => {
			invert_table_selection(dialog.fields_dict.results.df.data);
			dialog.fields_dict.results.grid.refresh();
		};
		const search = async () => {
			const warehouse = dialog.get_value("warehouse");
			if (!warehouse) return frappe.msgprint(__("请选择明确订单仓库或仓库范围"));
			const response = await frappe.call({ method: sales_order_search_api, args: {
				context: JSON.stringify(sales_order_context(frm, warehouse)),
				filters: JSON.stringify({ warehouse, item_group: dialog.get_value("item_group"), template: dialog.get_value("template"), color: dialog.get_value("color"), search: dialog.get_value("search"), in_stock: dialog.get_value("in_stock") ? 1 : 0 }),
			} });
			const rows = (response.message?.items || []).map((row) => ({ ...row, include: 0, qty: 1 }));
			dialog.fields_dict.results.df.data = rows;
			dialog.fields_dict.results.grid.refresh();
			dialog.fields_dict.hint.$wrapper.html(`<div class="text-muted small">${__("找到 {0} 条，库存口径：actual_qty - reserved_qty", [rows.length])}</div>`);
		};
		dialog.fields_dict.search_items.$input?.on("click", search);
		dialog.fields_dict.select_all.$input?.on("click", () => set_selection(true));
		dialog.fields_dict.invert_selection.$input?.on("click", invert_selection);
		dialog.show();
		search();
	}

	function open_color_picker(frm, kind) {
		const is_receipt = kind === "receipt";
		const is_sales_order = kind === "sales_order";
		const is_reconciliation = kind === "reconciliation";
		const dialog = new frappe.ui.Dialog({
			title: is_receipt ? __("按色扫码收货") : is_sales_order ? __("销售开单选颜色") : __("按色扫码盘点"),
			fields: [
				{ fieldname: "barcode", label: __("厂家外包装条码"), fieldtype: "Data", reqd: 1, description: __("只有厂家外包装条码用于弹出颜色选项；共用条码只识别款式，颜色必须人工选择") },
				{ fieldname: "variant", label: __("固定色号/颜色"), fieldtype: "Select", options: "", hidden: 1 },
				{ fieldname: "variant_preview", fieldtype: "HTML", hidden: 1 },
				...(is_sales_order ? [
					{ fieldname: "variant_select_all", label: __("全选"), fieldtype: "Button", hidden: 1 },
					{ fieldname: "variant_invert", label: __("反选"), fieldtype: "Button", hidden: 1 },
				] : []),
				...(is_sales_order ? [{ fieldname: "variant_items", label: __("可选颜色（可多选）"), fieldtype: "Table", hidden: 1, cannot_add_rows: true, cannot_delete_rows: true, in_place_edit: true, data: [], fields: [
					{ fieldname: "include", label: __("加入"), fieldtype: "Check", in_list_view: 1 },
					{ fieldname: "item_code", label: __("货号"), fieldtype: "Data", read_only: 1, in_list_view: 1 },
					{ fieldname: "color_code", label: __("Cor/色号"), fieldtype: "Data", read_only: 1, in_list_view: 1 },
					{ fieldname: "item_name", label: __("商品"), fieldtype: "Data", read_only: 1, in_list_view: 1 },
					{ fieldname: "available_qty", label: __("可用库存"), fieldtype: "Float", read_only: 1, in_list_view: 1 },
					{ fieldname: "rate", label: __("当前售价"), fieldtype: "Currency", read_only: 1, in_list_view: 1 },
					{ fieldname: "qty", label: __("数量"), fieldtype: "Int", default: 1, in_list_view: 1 },
					{ fieldname: "warehouse", label: __("仓库"), fieldtype: "Data", read_only: 1, in_list_view: 1 },
					{ fieldname: "status", label: __("状态"), fieldtype: "Data", read_only: 1, in_list_view: 1 },
				] }] : []),
				{ fieldname: "qty", label: is_receipt ? __("收货数量（正整数）") : is_sales_order ? __("销售数量（正整数）") : __("本次实盘数量（可为 0）"), fieldtype: "Data", hidden: 1 },
				{ fieldname: "warehouse", label: __("明确仓库"), fieldtype: "Link", options: "Warehouse", default: frm.doc.set_warehouse || frm.doc.last_scanned_warehouse || "", reqd: 1 },
				...(is_receipt ? [{ fieldname: "rate", label: __("最终单位成本"), fieldtype: "Currency", hidden: 1, min: 0.0001, description: __("直接输入外部算好的最终成本，不在系统内分摊到岸费用") }] : []),
				{ fieldname: "duplicate_mode", label: __("已有同色同仓行"), fieldtype: "Select", options: [{ label: __("覆盖数量"), value: "replace" }, { label: __("追加数量"), value: "append" }], default: "replace", hidden: 1 },
				{ fieldname: "hint", fieldtype: "HTML", options: `<div class="text-muted small">${is_sales_order ? __("选择颜色后写入具体变体货号；可连续录入。") : __("没有新增行 = 尚未盘点；明确输入 0 = 实盘为 0。扫码后可连续录入。")}</div>` },
			],
			primary_action_label: __("查询颜色"),
		});
		let variants = [];
		let request_id = 0;
		let busy = false;
		let selected_barcode = "";
		const bind_variant_change = () => dialog.fields_dict.variant.$input?.off("change.solua").on("change.solua", render_preview);
		const reset_selection = () => {
			++request_id;
			selected_barcode = "";
			variants = [];
			for (const field of ["variant", "qty", ...(is_receipt ? ["rate"] : [])]) {
				dialog.set_df_property(field, "reqd", 0);
				dialog.set_df_property(field, "hidden", 1);
			}
			if (is_sales_order) {
				dialog.fields_dict.variant_items.df.data = [];
				dialog.set_df_property("variant_items", "hidden", 1);
				dialog.set_df_property("variant_select_all", "hidden", 1);
				dialog.set_df_property("variant_invert", "hidden", 1);
				dialog.fields_dict.variant_items.grid?.refresh();
			}
			dialog.set_value("variant", "");
			dialog.set_value("qty", "");
			if (is_receipt) dialog.set_value("rate", "");
			dialog.fields_dict.variant_preview.$wrapper.empty();
			dialog.set_primary_action(__("查询颜色"), lookup);
		};

		const render_preview = () => {
			const selected = variants.find((row) => row.name === dialog.get_value("variant"));
			const image = selected?.image ? `<img src="${frappe.utils.escape_html(selected.image)}" alt="" style="max-width:120px;max-height:120px;object-fit:contain">` : `<span class="text-muted">${__("无图片")}</span>`;
			dialog.fields_dict.variant_preview.$wrapper.html(`<div class="solua-wholesale-variant-preview">${image}<span>${frappe.utils.escape_html(selected?.color_code || selected?.color || selected?.item_name || "")}</span></div>`);
		};

		const add_selected_rows = async () => {
			if (busy) return;
			const selected = (dialog.fields_dict.variant_items.df.data || []).filter((row) => row.include);
			const invalid = selected.filter((row) => !is_positive_integer(row.qty));
			if (!selected.length) return frappe.msgprint(__("请至少选择一种颜色"));
			if (invalid.length) return frappe.msgprint(__("数量必须为正整数"));
			busy = true;
			dialog.set_primary_action(__("写入中…"), () => {});
			try {
				const response = await frappe.call({ method: sales_order_rows_api, args: {
					rows: JSON.stringify(selected.map((row) => ({ item_code: row.item_code, qty: row.qty, warehouse: row.warehouse }))),
					context: JSON.stringify(sales_order_context(frm, dialog.get_value("warehouse"))),
				} });
				const result = response.message || {};
				append_sales_order_rows(frm, result.rows || []);
				if (result.errors?.length) frappe.msgprint({ title: __("部分颜色未加入"), message: error_summary(result.errors), indicator: "orange" });
				else frappe.show_alert({ message: __("已批量加入当前销售订单草稿，请保存"), indicator: "green" });
				await dialog.set_value("barcode", "");
				reset_selection();
				dialog.fields_dict.barcode.$input.focus();
			} finally { busy = false; }
		};

		const show_variants = (data) => {
			variants = is_sales_order && data.has_template ? (data.variants || []) : (data.templates || []).flatMap((group) => group.variants || []);
			if (!variants.length) {
				frappe.msgprint({ message: __("未找到可选颜色或无权查看该物料"), indicator: "orange" });
				return;
			}
			if (is_sales_order && data.has_template) {
				const rows = variants.map((row) => ({ ...row, include: 0, qty: 1 }));
				dialog.fields_dict.variant_items.df.data = rows;
				dialog.fields_dict.variant_items.grid?.refresh();
				dialog.set_df_property("variant_items", "hidden", 0);
				dialog.set_df_property("variant_select_all", "hidden", 0);
				dialog.set_df_property("variant_invert", "hidden", 0);
				dialog.set_df_property("variant", "hidden", 1);
				dialog.set_df_property("qty", "hidden", 1);
				dialog.set_df_property("duplicate_mode", "hidden", 1);
				dialog.set_primary_action(__("加入所选颜色"), add_selected_rows);
				return;
			}
			const options = [{label: __("请选择颜色/规格"), value: ""}, ...variants.map((row) => ({ label: `${row.color_code || "—"} · ${row.color || row.item_name} · ${row.item_code}`, value: row.name }))];
			dialog.set_df_property("variant", "options", options);
			dialog.set_value("variant", "");
			dialog.set_df_property("variant", "hidden", 0);
			dialog.set_df_property("variant_preview", "hidden", 0);
			dialog.set_df_property("qty", "hidden", 0);
			dialog.set_df_property("duplicate_mode", "hidden", 0);
			if (is_receipt) dialog.set_df_property("rate", "hidden", 0);
			for (const field of ["variant", "qty", ...(is_receipt ? ["rate"] : [])]) dialog.set_df_property(field, "reqd", 1);
			dialog.set_primary_action(__("加入单据"), add_row);
			bind_variant_change();
			dialog.fields_dict.variant.$input?.focus();
			render_preview();
		};

		const lookup = async () => {
			if (busy) return;
			const barcode = (dialog.get_value("barcode") || "").trim();
			if (!barcode) return;
			reset_selection();
			const current_request = ++request_id;
			dialog.set_primary_action(__("查询中…"), () => {});
			try {
				const args = is_sales_order
					? { barcode, context: JSON.stringify(sales_order_context(frm, dialog.get_value("warehouse"))) }
					: { barcode, barcode_only: 1 };
				const response = await frappe.call({ method: is_sales_order ? sales_order_color_api : variant_api, args });
				if (current_request === request_id && barcode === (dialog.get_value("barcode") || "").trim()) {
					selected_barcode = barcode;
					show_variants(response.message || {});
				}
			} catch (error) {
				if (current_request === request_id) frappe.msgprint(__("查询失败，请重试"));
			} finally {
				if (current_request === request_id && !variants.length) dialog.set_primary_action(__("查询颜色"), lookup);
			}
		};
		if (is_sales_order) {
			dialog.fields_dict.variant_select_all.$input?.on("click", () => {
				set_table_selection(dialog.fields_dict.variant_items.df.data, true);
				dialog.fields_dict.variant_items.grid?.refresh();
			});
			dialog.fields_dict.variant_invert.$input?.on("click", () => {
				invert_table_selection(dialog.fields_dict.variant_items.df.data);
				dialog.fields_dict.variant_items.grid?.refresh();
			});
		}

		const add_row = async () => {
			if (busy) return;
			const item_code = dialog.get_value("variant");
			const qty = Number(dialog.get_value("qty"));
			const rate = Number(dialog.get_value("rate"));
			const warehouse = dialog.get_value("warehouse");
			const raw_qty = dialog.get_value("qty");
			if (frm.doc.docstatus !== 0 || !selected_barcode || selected_barcode !== (dialog.get_value("barcode") || "").trim()
				|| !variants.some((row) => row.name === item_code) || !warehouse || raw_qty == null || String(raw_qty).trim() === ""
				|| !Number.isFinite(qty) || !Number.isInteger(qty) || (is_reconciliation ? qty < 0 : qty <= 0) || (is_receipt && (!Number.isFinite(rate) || rate <= 0))) {
				frappe.msgprint(is_receipt ? __("请完整填写仓库、颜色、正整数数量和最终单位成本") : __("请完整填写仓库、颜色和正整数数量"));
				return;
			}
			busy = true;
			dialog.set_primary_action(__("写入中…"), () => {});
			try {
				const existing = (frm.doc.items || []).find((row) => row.item_code === item_code && row.warehouse === warehouse);
				if (existing) {
					const next_qty = dialog.get_value("duplicate_mode") === "append" ? Number(existing.qty || 0) + qty : qty;
					await Promise.resolve(frappe.model.set_value(existing.doctype, existing.name, "qty", next_qty));
					if (is_receipt) await Promise.resolve(frappe.model.set_value(existing.doctype, existing.name, "rate", rate));
				} else {
					const row = frm.add_child("items");
					await frappe.model.set_value(row.doctype, row.name, "warehouse", warehouse);
					await Promise.resolve(frappe.model.set_value(row.doctype, row.name, "item_code", item_code));
					await frappe.model.set_value(row.doctype, row.name, "warehouse", warehouse);
					await Promise.resolve(frappe.model.set_value(row.doctype, row.name, "qty", qty));
					if (is_receipt) await Promise.resolve(frappe.model.set_value(row.doctype, row.name, "rate", rate));
				}
				frm.refresh_field("items");
				frappe.show_alert({message: __("已加入当前草稿，请保存单据；可继续扫描"), indicator: "green"});
				await dialog.set_value("barcode", "");
				reset_selection();
				dialog.fields_dict.barcode.$input.focus();
			} catch (error) {
				// A native field trigger may have partly filled a row; require review
				// before a retry so append mode cannot silently repeat that write.
				reset_selection();
				frm.refresh_field("items");
				frappe.msgprint(__("录入未完成，请先检查单据行后重新扫描"));
			} finally {
				busy = false;
			}
		};

		bind_variant_change();
		dialog.set_primary_action(__("查询颜色"), lookup);
		dialog.show();
		dialog.fields_dict.barcode.$input.on("input", () => { if (!busy) reset_selection(); });
		dialog.$wrapper.on("hidden.bs.modal", () => { ++request_id; });
		dialog.fields_dict.barcode.$input.on("keydown", (event) => {
			if (event.key === "Enter") { event.preventDefault(); lookup(); }
		});
		dialog.fields_dict.barcode.$input.focus();
	}

	function print_wholesale(frm) {
		const format = print_formats[frm.doctype];
		const has_column_switches = ["Sales Order", "Delivery Note"].includes(frm.doctype);
		const dialog = new frappe.ui.Dialog({
			title: __("打印选项"),
			fields: [
				...(has_column_switches ? [
					{ fieldname: "show_item_name", label: __("显示商品名称"), fieldtype: "Check", default: frm.doc.custom_print_item_name == null ? 1 : frm.doc.custom_print_item_name },
					{ fieldname: "show_sku", label: __("显示 SKU/货号"), fieldtype: "Check", default: frm.doc.custom_print_sku == null ? 1 : frm.doc.custom_print_sku },
					{ fieldname: "show_color_code", label: __("显示色号"), fieldtype: "Check", default: frm.doc.custom_print_color_code == null ? 1 : frm.doc.custom_print_color_code },
					{ fieldname: "show_description", label: __("显示商品描述"), fieldtype: "Check", default: frm.doc.custom_print_description == null ? 1 : frm.doc.custom_print_description },
				] : []),
				...(frm.doctype === "Delivery Note" ? [
					{ fieldname: "show_ordered_before", label: __("显示订购 / 此前已交付"), fieldtype: "Check", default: frm.doc.custom_print_ordered_before == null ? 1 : frm.doc.custom_print_ordered_before },
					{ fieldname: "show_current_remaining", label: __("显示本次 / 剩余"), fieldtype: "Check", default: frm.doc.custom_print_current_remaining == null ? 1 : frm.doc.custom_print_current_remaining },
					{ fieldname: "show_traceability", label: __("显示追溯信息"), fieldtype: "Check", default: frm.doc.custom_print_traceability == null ? 1 : frm.doc.custom_print_traceability },
				] : []),
				{ fieldname: "show_images", label: __("显示颜色图片"), fieldtype: "Check", default: frm.doc.custom_print_color_images ? 1 : 0 },
				{ fieldname: "show_qr", label: __("显示色卡二维码"), fieldtype: "Check", default: frm.doc.custom_print_color_qr ? 1 : 0 },
			],
			primary_action_label: __("保存并打开预览"),
			async primary_action(values) {
				if (dialog.__printing) return;
				dialog.__printing = true;
				try {
				const changes = {};
				if (has_column_switches) {
					if (frm.fields_dict.custom_print_item_name) changes.custom_print_item_name = values.show_item_name ? 1 : 0;
					if (frm.fields_dict.custom_print_sku) changes.custom_print_sku = values.show_sku ? 1 : 0;
					if (frm.fields_dict.custom_print_color_code) changes.custom_print_color_code = values.show_color_code ? 1 : 0;
					if (frm.fields_dict.custom_print_description) changes.custom_print_description = values.show_description ? 1 : 0;
				}
				if (frm.doctype === "Delivery Note" && frm.fields_dict.custom_print_ordered_before) {
					changes.custom_print_ordered_before = values.show_ordered_before ? 1 : 0;
				}
				if (frm.doctype === "Delivery Note" && frm.fields_dict.custom_print_current_remaining) {
					changes.custom_print_current_remaining = values.show_current_remaining ? 1 : 0;
				}
				if (frm.doctype === "Delivery Note" && frm.fields_dict.custom_print_traceability) {
					changes.custom_print_traceability = values.show_traceability ? 1 : 0;
				}
				if (frm.fields_dict.custom_print_color_images) changes.custom_print_color_images = values.show_images ? 1 : 0;
				if (frm.fields_dict.custom_print_color_qr) changes.custom_print_color_qr = values.show_qr ? 1 : 0;
				if (Object.keys(changes).length) await frm.set_value(changes);
				if (frm.is_dirty()) await frm.save(frm.doc.docstatus === 1 ? "Update" : undefined);
				const params = new URLSearchParams({ doctype: frm.doctype, name: frm.doc.name, format, no_letterhead: "0", trigger_print: "1" });
				window.open(`/printview?${params.toString()}`, "_blank");
				dialog.hide();
				} finally {
					dialog.__printing = false;
				}
			},
		});
		dialog.show();
	}

	function make_sales_order_delivery_date_optional(frm) {
		frm.set_df_property?.("delivery_date", "reqd", 0);
		frm.fields_dict?.items?.grid?.update_docfield_property("delivery_date", "reqd", 0);
	}

	frappe.ui.form.on("Sales Order Item", {
		item_code(frm, cdt, cdn) {
			const row = locals[cdt][cdn];
			if (!row.item_code) {
				frappe.model.set_value(cdt, cdn, "custom_item_barcode", "");
				return;
			}
			const item_code = row.item_code;
			frappe.call({ method: sales_order_item_display_api, args: { item_code } }).then((response) => {
				const current = locals[cdt][cdn];
				if (!current || current.item_code !== item_code) return;
				const value = response.message || {};
				frappe.model.set_value(cdt, cdn, "custom_item_barcode", value.barcode || "");
				if (value.description) frappe.model.set_value(cdt, cdn, "description", value.description);
			});
		},
	});

	["Sales Order", "Delivery Note"].forEach((doctype) => frappe.ui.form.on(doctype, {
		setup(frm) {
			if (doctype === "Sales Order") make_sales_order_delivery_date_optional(frm);
		},
		refresh(frm) {
			if (doctype === "Sales Order") make_sales_order_delivery_date_optional(frm);
			if (doctype === "Sales Order" && frm.doc.docstatus === 0) {
				frm.add_custom_button(__("按款式条码选颜色"), () => open_color_picker(frm, "sales_order"), __("工具"));
				frm.add_custom_button(__("上传订单表格"), () => open_sales_order_upload(frm), __("工具"));
				frm.add_custom_button(__("批量添加物料"), () => open_sales_order_bulk_picker(frm), __("工具"));
				frm.add_custom_button(__("粘贴货号 + 数量"), () => open_sales_order_paste(frm), __("工具"));
			}
			const label = __(doctype === "Sales Order" ? "客户订单确认单" : "Guia de Remessa");
			if (!frm.is_new()) frm.add_custom_button(label, () => print_wholesale(frm), __("打印"));
		},
	}));

	frappe.ui.form.on("Purchase Receipt", { refresh(frm) { if (frm.doc.docstatus === 0) frm.add_custom_button(__("按色扫码收货"), () => open_color_picker(frm, "receipt"), __("工具")); } });
	frappe.ui.form.on("Stock Reconciliation", { refresh(frm) {
			if (frm.doc.docstatus === 0) frm.add_custom_button(__("手机扫码盘点"), () => open_color_picker(frm, "reconciliation"), __("工具"));
			if (!frm.__solua_count_note) { frm.__solua_count_note = true; frm.dashboard.add_comment(__("未列出的物料表示尚未盘点；明确列出并输入 0 才表示实盘为 0。"), "blue"); }
		} });
})();
