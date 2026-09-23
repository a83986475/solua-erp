// ============================================================================
// solua_home / public/js/item_list_metrics.js
// 物料列表两件事：
//   1) 库存 / 四档售价列：由后端 item_metrics.py 在库存单据、Item Price、Item 保存
//      时维护；这里只挂一个「刷新库存与售价」按钮用于批量导入后手动对齐。
//   2) 列宽：Frappe 按单元格文字长度自动算宽度（get_column_html -> column_max_widths
//      -> apply_column_widths 写行内样式），长文本列常被撑得很宽。下面用一张宽度表
//      在每次重绘后覆盖框架算出来的值。
// 注册：hooks.py -> doctype_list_js["Item"]
// ============================================================================

frappe.provide("solua_home.item_list_metrics");

(function () {
	if (window.__solua_home_item_list_metrics_loaded) return;
	window.__solua_home_item_list_metrics_loaded = true;

	// 列宽（单位 px）。要调哪一列就改这里的数字；删掉某一项即恢复框架自动宽度。
	const COLUMN_WIDTHS = {
		// 本模块新增的库存与价格列
		custom_stock_qty: 110,
		custom_variant_stock_qty: 130,
		custom_rate_cost: 110,
		custom_rate_home: 120,
		custom_rate_wholesale: 110,
		custom_rate_retail: 110,
		// 其余常用自定义/长文本列，默认宽度过宽
		custom_color_code: 90,
		custom_order_code: 130,
		custom_spu_code: 120,
		custom_label_barcode: 150,
		custom_pos_short_name: 110,
		item_group: 100,
		valuation_rate: 120,
		description: 220,
		image: 90,
		custom_swatch_image: 90,
	};

	// 接管列宽：框架在每次重绘后都会调用 apply_column_widths()，它读取
	// column_max_widths 里的像素值写行内 style，所以覆盖这张表即可固定列宽，
	// 不影响渲染、排序、筛选等其它逻辑。
	function pin_column_widths(listview) {
		if (!listview || typeof listview.apply_column_widths !== "function") return false;
		const apply = listview.apply_column_widths;
		listview.apply_column_widths = function () {
			Object.assign(this.column_max_widths, COLUMN_WIDTHS);
			return apply.call(this);
		};
		return true;
	}

	function add_refresh_button(listview) {
		listview.page.add_inner_button(__("刷新库存与售价"), () => {
			frappe.call({
				method: "solua_home.item_metrics.refresh_all_item_metrics",
				freeze: true,
				freeze_message: __("正在重算所有物料的库存与售价…"),
			}).then((response) => {
				const updated = (response && response.message && response.message.updated) || 0;
				frappe.show_alert({
					message: __("已重算 {0} 条物料的库存与售价", [updated]),
					indicator: "green",
				});
				listview.refresh();
			});
		});
	}

	const previous = frappe.listview_settings["Item"] || {};
	const previous_onload = previous.onload;

	frappe.listview_settings["Item"] = Object.assign({}, previous, {
		// 方便其它脚本/调试读取当前生效的列宽
		column_widths: COLUMN_WIDTHS,
		onload(listview) {
			if (typeof previous_onload === "function") previous_onload.call(this, listview);
			pin_column_widths(listview);
			try {
				add_refresh_button(listview);
			} catch (error) {
				// 列表页面结构变化时不影响其它功能
				console.warn("solua_home: 刷新按钮未挂载", error);
			}
		},
	});
})();
