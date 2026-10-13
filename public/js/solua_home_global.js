// ============================================================================
// solua_home / public/js/solua_home_global.js
// 全站全局前端增强（app_include_js，Desk 所有页面加载）
//
// 当前功能：
//   1. Link 输入框「有内容时点击」也弹出下拉（frappe 默认只有空值才触发）
//
// 注册方式（hooks.py）：
//   app_include_js = [
//       "/assets/solua_home/js/solua_home_global.js",
//   ]
// ============================================================================

frappe.provide("solua_home.global_js");

(function () {
	"use strict";

	// Sales Order's standard script toggles the child delivery_date requirement
	// from order_type/skip_delivery_note. Keep it optional for this workflow.
	const keepSalesOrderDeliveryDateOptional = (frm) => {
		if (!frm || frm.doctype !== "Sales Order") return;

		const apply = () => {
			if (frm.doc?.docstatus !== 0) return;
			frm.set_df_property?.("delivery_date", "reqd", 0);

			const grid = frm.fields_dict?.items?.grid;
			if (!grid) return;
			if (!grid.__solua_delivery_date_guard && typeof grid.toggle_reqd === "function") {
				const toggle_reqd = grid.toggle_reqd;
				grid.toggle_reqd = function (fieldname, reqd) {
					return toggle_reqd.call(this, fieldname, fieldname === "delivery_date" ? 0 : reqd);
				};
				grid.__solua_delivery_date_guard = true;
			}
			grid.update_docfield_property?.("delivery_date", "reqd", 0);
		};

		apply();
		setTimeout(apply, 0);
		setTimeout(apply, 250);
	};

	const registerSalesOrderDeliveryDateFix = () => {
		if (!frappe.ui?.form?.on || solua_home.global_js.__sales_order_delivery_date_fix) return;
		solua_home.global_js.__sales_order_delivery_date_fix = true;
		frappe.ui.form.on("Sales Order", {
			setup: keepSalesOrderDeliveryDateOptional,
			onload: keepSalesOrderDeliveryDateOptional,
			refresh: keepSalesOrderDeliveryDateOptional,
			order_type: keepSalesOrderDeliveryDateOptional,
			skip_delivery_note: keepSalesOrderDeliveryDateOptional,
		});
	};

	registerSalesOrderDeliveryDateFix();

	// ------------------------------------------------------------
	// Link 输入框有内容时，点击也弹出下拉
	// ------------------------------------------------------------
	// frappe link.js 的 focus 处理器只在输入框为空时才触发 on_input()（弹下拉）；
	// 已有内容时点击毫无反应，必须清空才能重新选。这里覆写 LinkControl.make_input，
	// 给 Link 输入框追加 click 处理器：有内容时点击同样调用 on_input() 弹出下拉。
	// 覆写前调用原逻辑；空值场景仍由 frappe 原 focus 逻辑处理（避免重复触发搜索）。
	const enhanceLinkClickToOpen = () => {
		if (!frappe.ui || !frappe.ui.form || !frappe.ui.form.LinkControl) return false;
		const proto = frappe.ui.form.LinkControl.prototype;
		if (proto.make_input.__solua_click) return true; // 已覆写，幂等

		const origMakeInput = proto.make_input;
		const wrapped = function () {
			origMakeInput.apply(this, arguments);
			const me = this;
			// 只对已存在的输入框绑一次，避免重复绑定
			if (this.$input && !this.$input.data("solua_click_open")) {
				this.$input.data("solua_click_open", true);
				this.$input.on("click", function () {
					if (me.$input.val()) {
						me.on_input();
					}
				});
			}
		};
		wrapped.__solua_click = true;
		proto.make_input = wrapped;
		return true;
	};

	// Frappe's Connections badges are click handlers without hrefs, so the
	// browser cannot offer Ctrl/Cmd-click, middle-click, or "open in new tab".
	const enhanceConnectionLinks = () => {
		if (typeof document === "undefined" || document.__solua_connection_links) return true;
		document.__solua_connection_links = true;
		const update = (root = document) => {
			const frm = window.cur_frm;
			if (!frm?.doc?.name) return;
			root.querySelectorAll?.(".form-links .document-link").forEach((link) => {
				const anchor = link.querySelector(".badge-link");
				const doctype = link.dataset.doctype;
				if (!anchor || !doctype) return;
				const fieldname = link.querySelector(".document-link-badge")?.dataset.fieldname
					|| frm.dashboard?.data?.fieldnames?.[doctype]
					|| frm.dashboard?.data?.non_standard_fieldnames?.[doctype]
					|| frm.dashboard?.data?.fieldname;
				const names = link.dataset.names?.split(",").filter(Boolean);
				const params = new URLSearchParams();
				if (names?.length) params.set("name", JSON.stringify(["in", names]));
				else if (fieldname) params.set(fieldname, frm.doc.name);
				const slug = frappe.router?.slug ? frappe.router.slug(doctype) : doctype.toLowerCase().replace(/[^a-z0-9]+/g, "-");
				anchor.href = `/app/${slug}${params.toString() ? `?${params}` : ""}`;
				anchor.title = __("可按住 Ctrl/⌘、中键或右键在新标签页打开");
			});
		};
		update();
		new MutationObserver(() => update()).observe(document.body, {childList: true, subtree: true, attributes: true, attributeFilter: ["data-names"]});
		return true;
	};

	// LinkControl 可能在脚本加载时尚未就绪，轮询等它加载（最多 15 秒）
	let tries = 0;
	const ensure = () => {
		if (enhanceLinkClickToOpen()) return;
		tries++;
		if (tries <= 30) setTimeout(ensure, 500);
	};
	ensure();
	enhanceConnectionLinks();
})();
