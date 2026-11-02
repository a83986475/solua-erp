const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");
const vm = require("node:vm");

const source = fs.readFileSync(path.join(__dirname, "..", "public", "js", "sales_order_available_stock_v20261102.js"), "utf8");
assert.match(source, /const selfReserved = frm\.doc\.docstatus === 1/);
assert.match(source, /Math\.max\(flt\(doc\.reserved_qty\)\s*-\s*selfReserved, 0\)/);
assert.match(source, /flt\(doc\.stock_qty\)\s*-\s*flt\(doc\.delivered_qty\)/);
assert.match(source, /remaining\s*<=\s*available\s*\?\s*"green"\s*:\s*"orange"/);

let events;
const context = {
	frappe: { ui: { form: { on: (doctype, registered) => { events = registered; } } } },
	flt: value => Number(value || 0),
};
vm.runInNewContext(source, context);
let formatter;
const frm = {
	doc: { docstatus: 1, has_unit_price_items: false },
	set_indicator_formatter: (fieldname, callback) => { formatter = callback; },
};
events.setup(frm);
const row = { qty: 20, stock_qty: 20, delivered_qty: 0, conversion_factor: 1, actual_qty: 21, reserved_qty: 20 };
assert.equal(formatter(row), "green");
frm.doc.docstatus = 0;
assert.equal(formatter(row), "orange");
console.log("PASS: Sales Order indicator uses available stock");
