// Pick List list view: the customer quick filter is registered without replacing core settings.
const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");
const vm = require("node:vm");

const base = path.join(__dirname, "..");
const source = fs.readFileSync(
	path.join(base, "public/js/pick_list_customer_filter_v20261010.js"),
	"utf8"
);
const hooks = fs.readFileSync(path.join(base, "hooks.py"), "utf8").replace(/\r\n/g, "\n");
assert.match(
	hooks,
	/"Pick List": \[\s+"public\/js\/sales_order_list_tools\.js",\s+"public\/js\/pick_list_customer_filter_v20261010\.js",\s+\]/,
	"Pick List list hook must load the customer filter"
);
const whitelist = fs.readFileSync(path.join(__dirname, "release_whitelist.txt"), "utf8");
assert(whitelist.includes("my_custom_app_example/solua_home/public/js/pick_list_customer_filter_v20261010.js"));
const inherited = { get_indicator() {}, custom_filter_configs: [{ fieldname: "status" }] };
const context = {
	__: (value) => value,
	console,
	frappe: {
		listview_settings: { "Pick List": inherited },
		provide(namespace) {
			for (const part of namespace.split(".")) this[part] = this[part] || {};
		},
	},
};
vm.createContext(context);

vm.runInContext(source, context);
const settings = context.frappe.listview_settings["Pick List"];
assert.equal(settings.get_indicator, inherited.get_indicator, "core indicator must survive");
assert.equal(settings.solua_customer_filter, true);
assert.equal(JSON.stringify(settings.custom_filter_configs), JSON.stringify([
	{ fieldname: "status" },
	{
		fieldtype: "Link",
		label: "Customer",
		options: "Customer",
		fieldname: "customer",
		condition: "=",
	},
]));

vm.runInContext(source, context);
assert.equal(settings.custom_filter_configs.length, 2, "reloading must not duplicate the filter");
console.log("PASS: Pick List list keeps core settings and adds one customer Link quick filter");
