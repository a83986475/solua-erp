// ============================================================================
// solua_home / public/js/item_variant_wizard.js
// 物料列表「批量生成变体」向导：
//   选模板 → 勾颜色（Cor 属性池）→ 服务端批量建变体（自动继承价格/条码/名称）
// 注册：hooks.py -> page_js = { "item": "public/js/item_variant_wizard.js" }
// ============================================================================

frappe.provide("solua_home.item_variant_wizard");

// 防重复加载：同一页面（列表+表单 meta）重复求值时只执行一次
if (window.__solua_home_item_variant_wizard_loaded) return;
window.__solua_home_item_variant_wizard_loaded = true;

$(function () {
	"use strict";

	if (frappe.boot && frappe.boot.app_include_js) {
		// no-op
	}

	const COLOR_ATTR_NAMES = ["Cor", "Color", "Colour"];

	// ---------- 工具 ----------
	const isItemListPage = () => {
		if (!frappe.router) return false;
		const route = frappe.router.current_route || [];
		return route[0] === "Item" && route.length === 1;
	};

	// ---------- 弹窗 ----------
	const openWizard = () => {
		const d = new frappe.ui.Dialog({
			title: __("批量生成变体"),
			fields: [
				{
					fieldname: "template_item",
					label: __("模板物料"),
					fieldtype: "Link",
					options: "Item",
					reqd: 1,
					get_query: () => ({ filters: { has_variants: 1 } }),
					description: __("选择多规格模板（has_variants=1）"),
				},
				{
					fieldname: "colors_section",
					label: __("选择颜色"),
					fieldtype: "Section Break",
				},
				{
					fieldname: "colors",
					label: __("颜色"),
					fieldtype: "MultiSelect",
					options: [], // 动态填充
					reqd: 0,
					description: __("勾选要生成的颜色；不选 = 全部颜色"),
				},
				{
					fieldname: "price_list",
					label: __("价格表"),
					fieldtype: "Link",
					options: "Price List",
					default: "Standard Selling",
				},
			],
			primary_action_label: __("创建变体"),
			primary_action(values) {
				d.hide();
				createVariants(values);
			},
		});

		// 模板变化时加载该模板可用的属性值（颜色池）
		d.fields_dict.template_item.$input.on("change", () => {
			const tpl = d.get_value("template_item");
			if (!tpl) return;
			frappe.call({
				method: "solua_home.api.variants.get_template_attribute_values",
				args: { template_item: tpl },
				callback: (r) => {
					if (!r.message) return;
					const field = d.fields_dict.colors;
					field.df.options = r.message.map((v) => v.attribute_value);
					field.refresh();
					// 默认全选
					d.set_value("colors", r.message.map((v) => v.attribute_value));
				},
			});
		});

		d.show();
	};

	const createVariants = (values) => {
		frappe.call({
			method: "solua_home.api.variants.bulk_create_variants",
			args: {
				template_item: values.template_item,
				attribute_values: values.colors || [],
				price_list: values.price_list,
			},
			freeze: true,
			freeze_message: __("正在生成变体..."),
			callback: (r) => {
				if (r.exc) {
					frappe.msgprint({
						title: __("变体生成失败"),
						message: __("请查看错误日志"),
						indicator: "red",
					});
					return;
				}
				const res = r.message || {};
				let msg = "";
				if (res.created && res.created.length) {
					msg += __("已创建 {0} 个变体：{1}").format(
						res.created.length,
						res.created.join(", ")
					) + "<br>";
				}
				if (res.skipped && res.skipped.length) {
					msg += __("已存在跳过：{0}").format(res.skipped.join(", ")) + "<br>";
				}
				if (res.errors && res.errors.length) {
					msg += __("失败 {0} 个：{1}").format(
						res.errors.length,
						res.errors.map((e) => `${e.combo}: ${e.error}`).join("; ")
					);
				}
				if (!msg) msg = __("没有生成任何变体");
				frappe.msgprint({ title: __("批量生成结果"), message: msg, indicator: "green" });
				// 刷新物料列表
				if (frappe.ui.form && frappe.ui.form.refresh) {
					// list page refresh
				}
				cur_list && cur_list.refresh && cur_list.refresh();
			},
		});
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
		btn.innerHTML = '<i class="fa fa-th-large" style="margin-right:4px"></i>' + __("批量生成变体");
		btn.addEventListener("click", openWizard);
		toolbar.appendChild(btn);
		injected = true;
	};

	// 轮询等待物料列表页面渲染完成
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

	// 路由变化时重新检查
	if (frappe.router && frappe.router.on) {
		frappe.router.on("change", () => {
			injected = false;
			setTimeout(kick, 800);
		});
	}
});
