// Add a customer Link input to the Pick List list's standard filters.
(() => {
	frappe.provide("frappe.listview_settings");
	const previous = frappe.listview_settings["Pick List"] || {};
	if (previous.solua_customer_filter) return;

	const existing = Array.isArray(previous.custom_filter_configs)
		? previous.custom_filter_configs
		: [];
	frappe.listview_settings["Pick List"] = Object.assign({}, previous, {
		solua_customer_filter: true,
		custom_filter_configs: [
			...existing,
			{
				fieldtype: "Link",
				label: __("Customer"),
				options: "Customer",
				fieldname: "customer",
				condition: "=",
			},
		],
	});
})();
