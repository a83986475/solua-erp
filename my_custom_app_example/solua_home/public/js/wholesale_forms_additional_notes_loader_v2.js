// Cache-busted loader for the doctype tools; refresh the current form after registration.
(function () {
	const src = "/assets/solua_home/js/wholesale_forms.js?v=print-options-e42aec7758";
	if (document.querySelector("script[data-solua-wholesale-forms]")) return;
	const script = document.createElement("script");
	script.dataset.soluaWholesaleForms = "1";
	script.src = src;
	const refresh_current = () => {
		const current = window.cur_frm;
		if (current && ["Sales Order", "Delivery Note", "Pick List"].includes(current.doctype) && typeof current.trigger === "function") {
			current.trigger("refresh");
		}
	};
	script.onload = () => {
		refresh_current();
		setTimeout(refresh_current, 1000);
	};
	document.head.appendChild(script);
})();
