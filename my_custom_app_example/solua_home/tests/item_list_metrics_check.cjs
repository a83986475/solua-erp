// Item list script: column widths are pinned and the refresh button stays wired.
const assert = require("node:assert/strict"), fs = require("node:fs"), vm = require("node:vm"), path = require("node:path");
const base = path.join(__dirname, "..");
const source = fs.readFileSync(path.join(base, "public/js/item_list_metrics.js"), "utf8");

const calls = [], alerts = [], buttons = [];
let loaded = 0, inherited = 0;
const sandbox = {
	window: {},
	frappe: {
		provide: () => {},
		// Another app already registered Item list settings; the merge must keep them.
		listview_settings: { Item: { inherited_key: 1, onload() { inherited += 1; } } },
		call: (options) => { calls.push(options); return Promise.resolve({ message: { updated: 93 } }); },
		show_alert: (alert) => alerts.push(alert),
	},
	__: (text, args) => (Array.isArray(args) ? args.reduce((out, v, i) => out.replace(`{${i}}`, v), text) : text),
	console,
};
vm.runInNewContext(source, sandbox);
const settings = sandbox.frappe.listview_settings["Item"];
assert(settings && typeof settings.onload === "function", "Item list settings must be registered");
assert.equal(settings.inherited_key, 1, "other apps' settings must survive the merge");
assert.equal(inherited, 0, "the inherited onload runs when the list loads, not at load time");
const firstPass = settings.column_widths;
assert(firstPass.custom_stock_qty === 110 && firstPass.custom_rate_wholesale === 110, firstPass);
assert(firstPass.description === 220 && firstPass.image === 90, "long text and image columns must be narrowed too");

// Pin column widths: the framework recomputes them on every render, ours must win.
let originalCalls = 0;
const listview = {
	column_max_widths: { custom_stock_qty: 173, description: 900 },
	apply_column_widths() { originalCalls += 1; return this.column_max_widths; },
	refresh() { loaded += 1; },
	page: { add_inner_button: (label, action) => buttons.push({ label, action }) },
};
settings.onload.call({}, listview);
assert.equal(inherited, 1, "the inherited onload must still run");
const applied = listview.apply_column_widths();
assert.equal(originalCalls, 1, "the framework method must still run");
assert.equal(applied.custom_stock_qty, 110, "our width must replace the computed one");
assert.equal(applied.description, 220, "computed 900px must be capped");
assert.equal(applied.custom_rate_retail, 110, "columns not yet rendered still get a width");
assert.equal(applied.item_name, undefined, "columns without a configured width stay automatic");

// The refresh and bulk-price buttons are both registered on the Item list.
assert.equal(buttons.length, 2);
assert(buttons[0].label, "刷新库存与售价");
assert(buttons[1].label, "批量修改物料价格");
buttons[0].action();
assert.equal(calls.at(-1).method, "solua_home.item_metrics.refresh_all_item_metrics");
return Promise.resolve().then(() => {
	assert.equal(loaded, 1, "the list must refresh after the recompute");
	assert(alerts.at(-1).message.includes("93"), alerts.at(-1));
	assert.equal(alerts.at(-1).indicator, "green");

	// Older/newer framework without apply_column_widths must not break the page.
	const plain = { page: { add_inner_button: () => {} } };
	settings.onload.call({}, plain);
	assert.equal(typeof plain.apply_column_widths, "undefined");

	// A second script evaluation must not double-register.
	vm.runInNewContext(source, sandbox);
	assert.equal(sandbox.frappe.listview_settings["Item"], settings, "settings object must be reused");
	console.log("PASS: Item list pins the stock/price column widths (computed widths cannot grow them back), keeps an inherited onload, and the refresh button still recomputes through the backend");
});
