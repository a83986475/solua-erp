const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");
const vm = require("node:vm");

let refresh;
let dialog;
const opened = [];
const calls = [];
const sandbox = {
	frappe: {
		call(options) { calls.push(options); return Promise.resolve({ message: {} }); },
		ui: {
			form: { on(doctype, handlers) { assert.equal(doctype, "Sales Invoice"); refresh = handlers.refresh; } },
			Dialog: class { constructor(options) { dialog = options; } show() {} hide() {} },
		},
	},
	__: (text) => text,
	URLSearchParams,
	window: { open(url) { opened.push(url); } },
};
vm.runInNewContext(fs.readFileSync(path.join(__dirname, "../public/js/sales_invoice_default_print_button_v20261009.js"), "utf8"), sandbox);

(async () => {
const frm = {
	doctype: "Sales Invoice",
	doc: { name: "ACC-SINV-1", docstatus: 1, custom_print_item_name: 1, custom_print_sku: 1 },
	is_new: () => false,
	reload_doc() { return Promise.resolve(); },
	buttons: [{ label: "批发销售单", group: "打印" }],
	remove_custom_button(label, group) { this.buttons = this.buttons.filter((button) => button.label !== label || button.group !== group); },
	add_custom_button(label, action, group) { this.buttons.push({ label, action, group }); },
	set_value(values) { Object.assign(this.doc, values); return Promise.resolve(); },
	save() { return Promise.resolve(); },
};
refresh(frm);
assert.deepEqual(frm.buttons.map(({ label, group }) => ({ label, group })), [{ label: "打印销售发票", group: "打印" }]);
frm.buttons[0].action();
await dialog.primary_action({ show_item_name: 1, show_sku: 1, show_color: 0, merge_order_code: 0, show_description: 1, show_images: 1, show_qr: 0 });
await new Promise((resolve) => setImmediate(resolve));
assert.equal(opened.length, 1);
assert.equal(calls.length, 1);
assert.equal(calls[0].method, "frappe.client.set_value");
assert.equal(calls[0].args.doctype, "Sales Invoice");
assert.equal(calls[0].args.name, "ACC-SINV-1");
const url = new URL(opened[0], "https://erp.solua.one");
assert.equal(url.pathname, "/printview");
assert.equal(url.searchParams.get("doctype"), "Sales Invoice");
assert.equal(url.searchParams.get("name"), "ACC-SINV-1");
assert.equal(url.searchParams.has("format"), false, "button must use Sales Invoice default format");
console.log("PASS: Sales Invoice button keeps options and opens the default print format");
})().catch((error) => { console.error(error); process.exitCode = 1; });
