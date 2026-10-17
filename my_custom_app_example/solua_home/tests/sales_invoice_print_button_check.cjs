const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");
const vm = require("node:vm");

let refresh;
const sandbox = {
	frappe: { ui: { form: { on(doctype, handlers) { assert.equal(doctype, "Sales Invoice"); refresh = handlers.refresh; } } } },
	__: (text) => text,
};
vm.runInNewContext(fs.readFileSync(path.join(__dirname, "../public/js/sales_invoice_print_button_v20261008.js"), "utf8"), sandbox);

const frm = {
	doc: { name: "ACC-SINV-1", docstatus: 1 },
	is_new: () => false,
	buttons: [],
	remove_custom_button(label, group) { this.buttons = this.buttons.filter((button) => button.label !== label || button.group !== group); },
	add_custom_button(label, action, group) { this.buttons.push({ label, action, group }); },
};
refresh(frm);
assert.deepEqual(frm.buttons.map(({ label, group }) => ({ label, group })), [{ label: "批发销售单", group: "打印" }]);
refresh(frm);
assert.equal(frm.buttons.length, 1, "refresh must restore exactly one wholesale print button");
console.log("PASS: Sales Invoice wholesale print button survives refresh");
