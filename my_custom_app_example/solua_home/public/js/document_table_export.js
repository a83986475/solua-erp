// ============================================================================
// solua_home / public/js/document_table_export.js
// 销售订单 / 销售单 / 交货单 / 拣货单 两件事：
//   1) 「导出表格」：把明细导成 Excel(.xlsx) 或 CSV，列与打印表格一致，底部带合计行。
//   2) 明细表格底部常显「共 N 行 · 总数量 X」，不用打印也能看到总数量。
// 注册：hooks.py -> app_include_js（脚本自己只对这四个单据生效）
// ============================================================================

(function () {
	if (typeof window !== "undefined" && window.__solua_home_table_export_loaded) return;
	if (typeof window !== "undefined") window.__solua_home_table_export_loaded = true;

	const DOCTYPES = ["Sales Order", "Sales Invoice", "Delivery Note", "Pick List"];
	const OPTIONS_API = "solua_home.api.export.get_export_options";
	const EXPORT_API = "solua_home.api.export.export_document_table";

	// 拣货单的明细行在 locations 子表（Pick List Item）里，其余三张都是 items
	const item_field = (frm) => (frm && frm.doctype === "Pick List" ? "locations" : "items");
	const rows_of = (frm) => ((frm && frm.doc && frm.doc[item_field(frm)]) || []).filter(Boolean);
	const round_qty = (value) => Math.round((Number(value) || 0) * 1000) / 1000;
	const qty_total = (frm) => round_qty(rows_of(frm).reduce((total, row) => total + (Number(row.qty) || 0), 0));
	const amount_total = (frm) =>
		Math.round(rows_of(frm).reduce((total, row) => total + (Number(row.amount) || 0), 0) * 100) / 100;

	// 明细底部那行文字；拣货单没有金额列，只显示行数与总数量。
	function grid_total_text(frm) {
		const parts = [
			__("共 {0} 行", [rows_of(frm).length]),
			`${__("总数量")} ${qty_total(frm)}`,
		];
		if (frm.doctype !== "Pick List") {
			parts.push(`${__("明细金额合计")} ${format_currency(amount_total(frm), (frm.doc && frm.doc.currency) || "")}`);
		}
		return parts.join(" · ");
	}

	function item_grid(frm) {
		const field = item_field(frm);
		return (frm.fields_dict && frm.fields_dict[field] && frm.fields_dict[field].grid) || null;
	}

	function grid_host(frm) {
		const grid = item_grid(frm);
		return (grid && grid.wrapper && grid.wrapper[0]) || null;
	}

	function render_grid_total(frm) {
		const host = grid_host(frm);
		if (!host || typeof document === "undefined") return;
		let footer = host.querySelector(".solua-grid-total");
		if (!footer) {
			footer = document.createElement("div");
			footer.className = "solua-grid-total small text-muted";
			footer.style.padding = "6px 12px";
			footer.style.borderTop = "1px dashed var(--border-color)";
			host.appendChild(footer);
		}
		footer.textContent = grid_total_text(frm);
	}

	// 明细行增删改后框架会重绘 grid，包一层 refresh 才能让底部数字跟着变。
	function hook_grid_refresh(frm) {
		const grid = item_grid(frm);
		if (!grid || typeof grid.refresh !== "function" || grid.__solua_total_hooked) return;
		grid.__solua_total_hooked = true;
		const refresh = grid.refresh;
		grid.refresh = function () {
			const result = refresh.apply(this, arguments);
			render_grid_total(frm);
			return result;
		};
	}

	function download_table(frm, values, columns, fmt) {
		const selected = (columns || []).filter((column) => values[`col_${column.key}`]).map((column) => column.key);
		if (!selected.length) {
			frappe.msgprint(__("请至少勾选一列"));
			return;
		}
		const params = new URLSearchParams({
			doctype: frm.doctype,
			name: frm.doc.name,
			fmt: fmt,
			columns: selected.join(","),
			include_header: values.include_header ? 1 : 0,
			include_total: values.include_total ? 1 : 0,
		});
		window.open(`/api/method/${EXPORT_API}?${params.toString()}`, "_blank");
	}

	function open_export_dialog(frm) {
		frappe.call({ method: OPTIONS_API, args: { doctype: frm.doctype } }).then((response) => {
			const options = (response && response.message) || {};
			const columns = options.columns || [];
			if (!columns.length) {
				frappe.msgprint(__("该单据类型暂不支持导出"));
				return;
			}
			const defaults = options.defaults || columns.map((column) => column.key);
			const dialog = new frappe.ui.Dialog({
				title: __("导出表格 · {0}", [frm.doc.name]),
				fields: [
					{
						fieldtype: "HTML",
						options: `<div class="text-muted small">${__("列与打印表格一致；底部合计行给出数量合计（Excel 可直接求和）。")}</div>`,
					},
					...columns.map((column) => ({
						fieldname: `col_${column.key}`,
						label: column.label,
						fieldtype: "Check",
						default: defaults.includes(column.key) ? 1 : 0,
					})),
					{ fieldtype: "Section Break", label: __("表格选项") },
					{ fieldname: "include_header", label: __("包含单据抬头（单号 / 日期 / 客户）"), fieldtype: "Check", default: 1 },
					{ fieldname: "include_total", label: __("包含底部合计行"), fieldtype: "Check", default: 1 },
				],
				primary_action_label: __("导出 Excel"),
				primary_action(values) {
					download_table(frm, values, columns, "xlsx");
				},
				secondary_action_label: __("导出 CSV"),
				secondary_action() {
					download_table(frm, dialog.get_values(), columns, "csv");
				},
			});
			dialog.show();
		});
	}

	DOCTYPES.forEach((doctype) => {
		frappe.ui.form.on(doctype, {
			refresh(frm) {
				hook_grid_refresh(frm);
				render_grid_total(frm);
				if (frm.is_new() || !frm.doc.name) return;
				frm.add_custom_button(__("导出表格"), () => open_export_dialog(frm), __("打印"));
			},
		});
	});

	if (typeof window !== "undefined") {
		window.solua_home_table_export = {
			DOCTYPES,
			grid_total_text,
			qty_total,
			amount_total,
			download_table,
			open_export_dialog,
		};
	}
})();
