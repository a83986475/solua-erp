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

	// LinkControl 可能在脚本加载时尚未就绪，轮询等它加载（最多 15 秒）
	let tries = 0;
	const ensure = () => {
		if (enhanceLinkClickToOpen()) return;
		tries++;
		if (tries <= 30) setTimeout(ensure, 500);
	};
	ensure();
})();
