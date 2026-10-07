// Run: node my_custom_app_example/solua_home/tests/print_button_check.cjs
const assert = require("node:assert/strict");
const fs = require("node:fs");
const vm = require("node:vm");
const path = require("node:path");

const handlers = {};
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
};
vm.runInNewContext(
	fs.readFileSync(path.join(__dirname, "../public/js/print_button_v20261006.js"), "utf8"),
	sandbox,
);

for (const doctype of ["Sales Order", "Sales Invoice", "Delivery Note", "Pick List"]) {
	let print_calls = 0;
	const frm = {
		doc: { name: "DOC-1" },
		buttons: [],
		is_new: () => false,
		print_doc: () => { print_calls += 1; },
		add_custom_button(label, action, group) { this.buttons.push({ label, action, group }); },
	};
	handlers[doctype].refresh(frm);
	assert.equal(frm.buttons.length, 1, doctype);
	assert.deepEqual(frm.buttons[0].label, "打印", doctype);
	assert.deepEqual(frm.buttons[0].group, "打印", doctype);
	frm.buttons[0].action();
	assert.equal(print_calls, 1, doctype);
	handlers[doctype].refresh(frm);
	assert.equal(frm.buttons.length, 1, `${doctype} must not duplicate the button`);
}

console.log("PASS: native print button is available once in the print menu for all supported documents");
