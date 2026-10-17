const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");
const vm = require("node:vm");

let refresh;
const sandbox = {
	frappe: { ui: { form: { on(doctype, handlers) { assert.equal(doctype, "Sales Invoice"); refresh = handlers.refresh; } } } },
	__: (text) => text,
};
vm.runInNewContext(fs.readFileSync(path.join(__dirname, "../public/js/sales_invoice_disable_wholesale_print_v20261008.js"), "utf8"), sandbox);

const frm = {
	doc: { name: "ACC-SINV-1" },
	is_new: () => false,
	buttons: [{ label: "批发销售单", group: "打印" }],
	remove_custom_button(label, group) { this.buttons = this.buttons.filter((button) => button.label !== label || button.group !== group); },
};
refresh(frm);
assert.deepEqual(frm.buttons, [], "disabled wholesale format must not remain in the Print menu");
console.log("PASS: disabled Sales Invoice wholesale print button is removed");
