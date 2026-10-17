// Run: node my_custom_app_example/solua_home/tests/print_button_check.cjs
const assert = require("node:assert/strict");
const fs = require("node:fs");
const vm = require("node:vm");
const path = require("node:path");

const handlers = {};
const opened = [];
const sandbox = {
	frappe: {
		ui: {
			form: {
				on(doctype, value) {
					handlers[doctype] = value;
				},
			},
		},
	},
	__: (text) => text,
	window: { open: (...args) => opened.push(args) },
	URLSearchParams,
};
vm.runInNewContext(
	fs.readFileSync(path.join(__dirname, "../public/js/print_button_v20261006.js"), "utf8"),
	sandbox,
);

for (const doctype of ["Sales Order", "Sales Invoice", "Delivery Note", "Pick List"]) {
	let print_calls = 0;
	const frm = {
		doctype,
		doc: { name: "DOC-1" },
		buttons: [],
		is_new: () => false,
		print_doc: () => { print_calls += 1; },
		remove_custom_button(label, group) { this.buttons = this.buttons.filter((button) => button.label !== label || button.group !== group); },
		add_custom_button(label, action, group) { this.buttons.push({ label, action, group }); },
	};
	handlers[doctype].refresh(frm);
	assert.equal(frm.buttons.length, 1, doctype);
	assert.deepEqual(frm.buttons[0].label, "打印", doctype);
	assert.deepEqual(frm.buttons[0].group, "打印", doctype);
	frm.buttons[0].action();
	assert.equal(print_calls, 0, doctype);
	const expected = new URLSearchParams({ doctype, name: "DOC-1" }).toString();
	assert.equal(opened.at(-1)[0], `/api/method/solua_home.api.export.download_pdf?${expected}`, doctype);
	handlers[doctype].refresh(frm);
	assert.equal(frm.buttons.length, 1, `${doctype} must not duplicate the button`);
}

console.log("PASS: compressed PDF button is available once in the print menu for all supported documents");
