// ============================================================================
// solua_home / public/js/item_data_wizard.js
// 物料列表「物料资料补全/校验」向导：
//   选模板(系列) → 自动按模板规则预填中文名/SPU/POS简称/最低库存 → 可改可存
//   + 「校验完整性」：全量检查所有物料的档案缺口
// 注册：hooks.py -> page_js = { "item": ["public/js/item_variant_wizard.js",
//                                         "public/js/item_data_wizard.js"] }
// ============================================================================

frappe.provide("solua_home.item_data_wizard");

// 防重复加载：同一页面（列表+表单 meta）重复求值时只执行一次
if (window.__solua_home_item_data_wizard_loaded) return;
window.__solua_home_item_data_wizard_loaded = true;

$(function () {
	"use strict";

	const API = "solua_home.api.item_data";

	const isItemListPage = () => {
		if (!frappe.router) return false;
		const route = frappe.router.current_route || [];
		return route[0] === "Item" && route.length === 1;
	};

	// ---------- 网格渲染 ----------
	const esc = (s) =>
		String(s == null ? "" : s)
			.replace(/&/g, "&amp;")
			.replace(/</g, "&lt;")
			.replace(/>/g, "&gt;")
			.replace(/"/g, "&quot;");

	const statusBadge = (st) => {
		if (!st) return '<span class="badge badge-default">?</span>';
		if (st.missing && st.missing.length)
			return '<span class="badge badge-danger" title="缺: ' + esc(st.missing.join("、")) + '">缺 ' + st.missing.length + " 项</span>";
		if (st.warnings && st.warnings.length)
			return '<span class="badge badge-warning" title="提示: ' + esc(st.warnings.join("、")) + '">提示</span>';
		return '<span class="badge badge-success">完整</span>';
	};

	const renderGrid = (d, rows) => {
		const wrap = d.fields_dict.grid_html.$wrapper.empty();
		if (!rows || !rows.length) {
			wrap.html('<div class="text-muted" style="padding:12px">没有找到物料</div>');
			return;
		}
		const head = [
			"编码", "名称", "中文名", "SPU编码", "规格摘要", "POS简称", "最低库存", "状态",
		].map((h) => `<th>${h}</th>`).join("");
		let body = "";
		rows.forEach((r) => {
			// 预填规则：变体沿用模板（中文名/SPU），POS简称 = 颜色；最低库存空则填 10
			const zh = r.custom_chinese_name || (r.template_zh && r.variant_of ? r.template_zh : "");
			const spu = r.custom_spu_code || (r.template_spu && r.variant_of ? r.template_spu : "");
			const pos = r.custom_pos_short_name || (r.variant_of && r.color ? r.color : "");
			const min = r.custom_min_stock_level > 0 ? r.custom_min_stock_level : 10;
			const tpl = r.variant_of ? "变体" : (r.has_variants ? "模板" : "单品");
			body += `<tr>
				<td><b>${esc(r.name)}</b> <span class="label label-default">${tpl}</span></td>
				<td class="text-muted" style="max-width:160px">${esc(r.item_name)}</td>
				<td><input type="text" class="form-control input-sm" data-field="chinese_name" data-item="${esc(r.name)}" value="${esc(zh)}"></td>
				<td><input type="text" class="form-control input-sm" data-field="spu_code" data-item="${esc(r.name)}" value="${esc(spu)}"></td>
				<td><input type="text" class="form-control input-sm" data-field="spec_summary" data-item="${esc(r.name)}" value="${esc(r.custom_spec_summary || "")}"></td>
				<td><input type="text" class="form-control input-sm" data-field="pos_short_name" data-item="${esc(r.name)}" value="${esc(pos)}"></td>
				<td><input type="number" class="form-control input-sm" data-field="min_stock" data-item="${esc(r.name)}" value="${min}" min="0"></td>
				<td>${statusBadge(r.status)}</td>
			</tr>`;
		});
		wrap.html(`<div style="max-height:420px;overflow:auto">
			<table class="table table-bordered table-hover" style="margin:0;min-width:900px">
				<thead><tr>${head}</tr></thead>
				<tbody>${body}</tbody>
			</table>
		</div>`);
		d.grid_rows = rows;
	};

	// ---------- 加载 ----------
	const loadItems = (d) => {
		const values = d.get_values();
		frappe.call({
			method: API + ".get_item_data",
			args: {
				template_item: values.template_item || null,
				item_group: values.item_group || null,
				search: values.search || null,
			},
			freeze: true,
			freeze_message: __("正在加载物料..."),
			callback: (r) => {
				if (r.exc) return;
				renderGrid(d, r.message || []);
			},
		});
	};

	// ---------- 校验完整性 ----------
	const runValidation = () => {
		frappe.call({
			method: API + ".validate_item_master",
			freeze: true,
			freeze_message: __("正在校验全部物料..."),
			callback: (r) => {
				if (r.exc) return;
				const res = r.message || {};
				let html = `<div style="margin-bottom:8px">
					<span class="label label-primary">共 ${res.total} 个物料</span>
					<span class="label label-success">完整 ${res.complete}</span>
					<span class="label label-danger">缺项 ${res.incomplete}</span>
				</div>`;
				// 字段汇总
				const fs = res.field_summary || {};
				const fieldRows = Object.keys(fs)
					.sort()
					.map((f) => {
						const s = fs[f];
						const pct = s.total ? Math.round(((s.missing || 0) / s.total) * 100) : 0;
						const warnTxt = s.warn ? ` / 提示 ${s.warn}` : "";
						return `<tr><td>${esc(f)}</td><td>${s.missing || 0} 缺${warnTxt} / 共 ${s.total}</td>
							<td><div class="progress" style="margin:0;height:8px;min-width:120px">
								<div class="progress-bar progress-bar-danger" style="width:${pct}%"></div>
							</div></td></tr>`;
					})
					.join("");
				if (fieldRows)
					html += `<h6>字段缺口</h6><table class="table table-bordered table-condensed" style="margin:0">
						<thead><tr><th>字段</th><th>缺口</th><th>比例</th></tr></thead><tbody>${fieldRows}</tbody></table>`;
				// 明细（缺项优先）
				const issues = res.issues || {};
				const codes = Object.keys(issues).sort();
				if (codes.length) {
					html += `<h6>明细（${codes.length} 条）</h6><div style="max-height:240px;overflow:auto">
						<table class="table table-bordered table-condensed" style="margin:0">
						<thead><tr><th>编码</th><th>缺项</th><th>提示</th></tr></thead><tbody>`;
					codes.forEach((c) => {
						const v = issues[c];
						html += `<tr><td><b>${esc(c)}</b></td>
							<td>${v.missing && v.missing.length ? '<span class="text-danger">' + esc(v.missing.join("、")) + "</span>" : '<span class="text-muted">—</span>'}</td>
							<td>${v.warnings && v.warnings.length ? esc(v.warnings.join("、")) : '<span class="text-muted">—</span>'}</td></tr>`;
					});
					html += "</tbody></table></div>";
				} else {
					html += `<div class="alert alert-success" style="margin:8px 0">所有物料档案完整 🎉</div>`;
				}
				frappe.msgprint({
					title: __("物料档案完整性校验"),
					message: html,
					indicator: res.incomplete ? "orange" : "green",
				});
			},
		});
	};

	// ---------- 保存 ----------
	const saveItems = (d) => {
		if (!d.grid_rows || !d.grid_rows.length) {
			frappe.msgprint(__("请先加载物料"));
			return;
		}
		const updates = [];
		d.fields_dict.grid_html.$wrapper
			.find("input[data-item]")
			.each(function () {
				const $in = $(this);
				const field = $in.data("field");
				const item = $in.data("item");
				let rec = updates.find((u) => u.item_code === item);
				if (!rec) {
					rec = { item_code: item };
					updates.push(rec);
				}
				rec[field] = $in.val();
			});
		frappe.call({
			method: API + ".bulk_update_item_data",
			args: { updates: updates },
			freeze: true,
			freeze_message: __("正在保存..."),
			callback: (r) => {
				if (r.exc) return;
				const res = r.message || {};
				let msg = __("已更新 {0} 个物料").format(res.updated.length);
				if (res.errors && res.errors.length)
					msg += "<br>" + __("失败 {0} 个：{1}").format(
						res.errors.length,
						res.errors.map((e) => `${e.item_code}: ${e.error}`).join("; ")
					);
				frappe.msgprint({ title: __("保存结果"), message: msg, indicator: res.errors && res.errors.length ? "orange" : "green" });
				loadItems(d); // 刷新网格状态
				if (cur_list && cur_list.refresh) cur_list.refresh();
			},
		});
	};

	// ---------- 弹窗 ----------
	const openWizard = () => {
		const d = new frappe.ui.Dialog({
			title: __("物料资料补全 / 校验"),
			fields: [
				{
					fieldname: "template_item",
					label: __("系列模板（加载模板+变体）"),
					fieldtype: "Link",
					options: "Item",
					get_query: () => ({ filters: { has_variants: 1 } }),
					description: __("例如 CR-002：自动带上模板和全部颜色变体"),
				},
				{
					fieldname: "item_group",
					label: __("或按物料组"),
					fieldtype: "Link",
					options: "Item Group",
					depends_on: "eval:!doc.template_item",
				},
				{
					fieldname: "search",
					label: __("或按编码/名称搜索"),
					fieldtype: "Data",
					depends_on: "eval:!doc.template_item",
				},
				{
					fieldname: "load_btn",
					fieldtype: "Button",
					label: __("加载物料"),
					click: () => loadItems(d),
				},
				{
					fieldname: "grid_html",
					fieldtype: "HTML",
				},
			],
			primary_action_label: __("保存修改"),
			primary_action: () => saveItems(d),
			secondary_action_label: __("校验全部物料完整性"),
			secondary_action: () => {
				runValidation();
				d.hide();
			},
		});
		// 回车键在搜索框触发加载
		d.fields_dict.search.$input.on("keydown", (e) => {
			if (e.key === "Enter") loadItems(d);
		});
		d.show();
		// 默认自动加载模板系列（若用户在物料表单里打开则跳列表）
	};

	// ---------- 按钮注入 ----------
	let injected = false;
	const injectButton = () => {
		if (injected) return;
		const toolbar = document.querySelector(
			'[data-page-route="Item"] .page-actions .page-actions-buttons, [data-page-route="item"] .page-actions .page-actions-buttons'
		);
		if (!toolbar) return;

		const btn = document.createElement("button");
		btn.className = "btn btn-default btn-sm";
		btn.innerHTML = '<i class="fa fa-pencil-square-o" style="margin-right:4px"></i>' + __("物料资料补全");
		btn.addEventListener("click", openWizard);
		toolbar.appendChild(btn);
		injected = true;
	};

	let tries = 0;
	const kick = () => {
		if (isItemListPage()) {
			injectButton();
			if (!injected && tries++ < 60) setTimeout(kick, 500);
		} else {
			injected = false;
			tries = 0;
			setTimeout(kick, 1000);
		}
	};
	setTimeout(kick, 1500);

	if (frappe.router && frappe.router.on) {
		frappe.router.on("change", () => {
			injected = false;
			setTimeout(kick, 800);
		});
	}
});
