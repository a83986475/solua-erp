// Cache-busted loader for the doctype tools; refresh the current form after registration.
(function () {
	const src = "/assets/solua_home/js/wholesale_forms_stock_entry_v20261017.js?v=stock-entry-tools-20261111a";
	if (window.solua_home_wholesale_forms_ready) return;
	if (document.querySelector("script[data-solua-wholesale-forms]")) return;
	const script = document.createElement("script");
	script.dataset.soluaWholesaleForms = "1";
	script.src = src;
	window.solua_home_wholesale_forms_ready = new Promise((resolve, reject) => {
		script.onload = () => {
			refresh_current();
			setTimeout(refresh_current, 1000);
			resolve();
		};
		script.onerror = () => reject(new Error(__("工具脚本网络加载失败")));
	});
	const refresh_current = () => {
		const current = typeof cur_frm !== "undefined" ? cur_frm : window.cur_frm;
		if (current && ["Sales Order", "Stock Entry", "Delivery Note", "Pick List", "Purchase Receipt", "Stock Reconciliation"].includes(current.doctype) && typeof current.trigger === "function") {
			current.trigger("refresh");
		}
	};
	document.head.appendChild(script);
})();
