// ============================================================================
// solua_home / public/js/doctype_module_filter.js
// 单据类型白名单：本项目实际会用到的 DocType
//
//   ① DocType 列表（/desk/doctype）默认只显示 IN_USE_DOCTYPES 里的单据类型
//   ② 打印格式（Print Format）编辑页的「单据类型」下拉框同样只列这份清单
//   ③ 只影响“筛选条件 / 下拉候选”，不删除、不停用、不修改任何 DocType、字段或数据
//   ④ 列表右上角按钮、打印格式表单按钮可在「只看常用单据类型 / 显示全部单据类型」
//      之间切换（按浏览器记忆，localStorage），切换后候选立即放开为全部 800+ 个
//
// 注册：hooks.py
//   doctype_list_js = {"DocType": ["public/js/doctype_module_filter.js"]}   → 列表
//   doctype_js      = {"Print Format": "public/js/doctype_module_filter.js"} → 表单下拉
//
// 说明：DocType 的列表脚本由 meta.py 先加载 core 的 doctype_list.js（含 primary_action /
//       new_doctype_dialog），再由 doctype_list_js 钩子追加本文件，因此这里只做追加合并。
// ============================================================================

frappe.provide("frappe.listview_settings");
frappe.provide("solua_home.doctype_scope");

// 防重复加载：同一页面（列表 + 表单 meta）重复求值时只执行一次
if (window.__solua_home_doctype_scope_loaded) return;
window.__solua_home_doctype_scope_loaded = true;

(function () {
	"use strict";

	// ────────────────────────────────────────────────────────────────────────
	// 会用到的单据类型（按用途分组；要增减只改这张表）
	// ────────────────────────────────────────────────────────────────────────
	const IN_USE_DOCTYPES = [
		// 销售与交货
		"Quotation",
		"Sales Order",
		"Delivery Note",
		"Sales Invoice",
		"POS Invoice",
		"POS Opening Entry",
		"POS Closing Entry",
		"Pick List",
		"Vehicle",
		// 采购
		"Request for Quotation",
		"Purchase Order",
		"Purchase Receipt",
		"Purchase Invoice",
		// 收付款与总账
		"Payment Entry",
		"Journal Entry",
		// 商品与库存
		"Item",
		"Item Price",
		"Price List",
		"Item Group",
		"Item Attribute",
		"Warehouse",
		"UOM",
		"Stock Entry",
		"Stock Entry Type",
		"Stock Reconciliation",
		// 客户、供应商与地址
		"Customer",
		"Customer Group",
		"Supplier",
		"Supplier Group",
		"Sales Person",
		"Territory",
		"Address",
		"Contact",
		// 公司与价格规则
		"Company",
		"Currency",
		"Country",
		"Mode of Payment",
		"Payment Term",
		"Payment Terms Template",
		"Sales Taxes and Charges Template",
		"Purchase Taxes and Charges Template",
		"Tax Category",
		"Cost Center",
		"Pricing Rule",
		// 打印与系统设置
		"Letter Head",
		"Print Format",
		"Print Heading",
		"Print Style",
		"Report",
		"DocType",
		"Custom Field",
		"Property Setter",
		"Workspace",
		"User",
		"Role",
		"File",
		"Data Import",
		// X POS 收银与自建单据
		"POS Profile",
		"POS Opening Shift",
		"POS Closing Shift",
		"POS Cash Movement",
		"POS Offer",
		"POS Coupon",
		"XPOS Branding Settings",
		"Scale Barcode Settings",
		"Product Bundle Definition",
		"Retail Settings",
	];

	const STORAGE_KEY = "solua_home_doctype_show_all";
	const ALLOWED = new Set(IN_USE_DOCTYPES);

	let memory_show_all = null;
	const show_all = () => {
		if (memory_show_all !== null) return memory_show_all;
		try {
			return window.localStorage.getItem(STORAGE_KEY) === "1";
		} catch (error) {
			return false;
		}
	};
	const set_show_all = (value) => {
		memory_show_all = Boolean(value);
		try {
			window.localStorage.setItem(STORAGE_KEY, value ? "1" : "0");
		} catch (error) {
			// 隐私模式或存储被禁用：本次会话仍按内存值生效
		}
	};

	// 列表筛选（ListView 会在前面自动补上本单据类型 DocType）
	const list_filters = () => (show_all() ? [] : [["name", "in", IN_USE_DOCTYPES]]);
	// Link 下拉框筛选（打印格式的 doc_type 用它）
	const link_filters = () => (show_all() ? {} : { name: ["in", IN_USE_DOCTYPES] });
	const toggle_label = () => (show_all() ? __("只看常用单据类型") : __("显示全部单据类型"));

	solua_home.doctype_scope = {
		names: IN_USE_DOCTYPES,
		has: (name) => ALLOWED.has(name),
		is_show_all: show_all,
		set_show_all: set_show_all,
		list_filters: list_filters,
		link_filters: link_filters,
		toggle_label: toggle_label,
	};

	// ────────────────────────────────────────────────────────────────────────
	// ① DocType 列表：默认只显示白名单
	// ────────────────────────────────────────────────────────────────────────
	function add_toggle_button(listview) {
		const page = listview && listview.page;
		if (!page || typeof page.add_inner_button !== "function") return;
		page.add_inner_button(toggle_label(), () => {
			set_show_all(!show_all());
			window.location.reload();
		});
	}

	const settings = frappe.listview_settings["DocType"] || (frappe.listview_settings["DocType"] = {});
	const filters_property = Object.getOwnPropertyDescriptor(settings, "filters");
	if (!filters_property || !filters_property.get) {
		Object.defineProperty(settings, "filters", {
			configurable: true,
			enumerable: true,
			get: list_filters,
		});
	}
	const previous_onload = settings.onload;
	settings.onload = function (listview) {
		if (typeof previous_onload === "function") previous_onload.call(this, listview);
		add_toggle_button(listview);
	};

	// 兜底：万一列表实例在读取 settings 之后才构造，构造完成时再补一次（幂等，不重复添加）
	const ListView = frappe.views && frappe.views.ListView;
	if (ListView && ListView.prototype && !ListView.prototype.__solua_doctype_scope) {
		const original_setup_defaults = ListView.prototype.setup_defaults;
		ListView.prototype.setup_defaults = function () {
			const result = original_setup_defaults.apply(this, arguments);
			if (
				this.doctype === "DocType"
				&& !show_all()
				&& Array.isArray(this.filters)
				&& !this.filters.some((filter) => filter[1] === "name")
			) {
				this.filters.push(["DocType", "name", "in", IN_USE_DOCTYPES]);
			}
			return result;
		};
		ListView.prototype.__solua_doctype_scope = true;
	}

	// ────────────────────────────────────────────────────────────────────────
	// ② 打印格式表单：doc_type 下拉只列白名单（编辑打印格式是这份清单的主要用途）
	// ────────────────────────────────────────────────────────────────────────
	const form_events = frappe.ui && frappe.ui.form && frappe.ui.form.on;
	if (typeof form_events === "function") {
		const apply_scope = (frm) => {
			if (frm && typeof frm.set_query === "function") {
				frm.set_query("doc_type", () => ({ filters: link_filters() }));
			}
		};
		frappe.ui.form.on("Print Format", {
			onload(frm) {
				apply_scope(frm);
			},
			refresh(frm) {
				apply_scope(frm);
				if (typeof frm.add_custom_button !== "function") return;
				frm.add_custom_button(toggle_label(), () => {
					set_show_all(!show_all());
					apply_scope(frm);
					if (typeof frm.refresh_field === "function") frm.refresh_field("doc_type");
					frappe.show_alert({
						message: show_all() ? __("单据类型下拉已显示全部") : __("单据类型下拉只显示常用"),
						indicator: "blue",
					});
				});
			},
		});
	}
})();
