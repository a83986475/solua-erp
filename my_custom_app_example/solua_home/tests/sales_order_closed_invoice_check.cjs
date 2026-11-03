const assert = require("node:assert/strict");
const fs = require("node:fs");
const vm = require("node:vm");
const path = require("node:path");

const handlers = {};
const mapped = [];
const frappe = {
  provide() {},
  ui: { form: { on(doctype, events) { handlers[doctype] = events; } } },
  model: {
    can_create() { return true; },
    open_mapped_doc(options) { mapped.push(options); },
  },
};
const context = { frappe, solua_home: {}, __: value => value };
vm.runInNewContext(
  fs.readFileSync(path.join(__dirname, "../public/js/sales_order_closed_invoice_v20261103.js"), "utf8"),
  context,
);

const buttons = [];
const frm = {
  doc: { docstatus: 1, status: "Closed" },
  remove_custom_button() {},
  add_custom_button(label, fn, group) { buttons.push({ label, fn, group }); },
};
handlers["Sales Order"].refresh(frm);
assert.equal(buttons.length, 1);
assert.equal(buttons[0].label, "为已交付未开票部分开票");
assert.equal(buttons[0].group, "Create");
buttons[0].fn();
assert.equal(mapped.length, 1);
assert.equal(mapped[0].method, "solua_home.api.unbilled.make_sales_invoice_from_closed_sales_order");
assert.equal(mapped[0].freeze, true);

buttons.length = 0;
frm.doc.status = "To Deliver";
handlers["Sales Order"].refresh(frm);
assert.equal(buttons.length, 0);
console.log("PASS: closed Sales Order exposes only the controlled delivered-unbilled invoice action");
