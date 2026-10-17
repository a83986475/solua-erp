const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");
const vm = require("node:vm");

const handlers = {};
const alerts = [];
class Dialog {
  constructor(options) { this.options = options; this.hidden = false; }
  show() {}
  hide() { this.hidden = true; }
}
const frappe = {
  ui: { form: { on(doctype, events) { handlers[doctype] = events; } }, Dialog },
  msgprint() {},
  show_alert(value) { alerts.push(value); },
};
const context = { frappe, window: {}, __: (value) => value, Number, Map, Array, Object };
vm.runInNewContext(fs.readFileSync(path.join(__dirname, "..", "public", "js", "sales_order_item_query_v20261014.js"), "utf8"), context);

const items = [
  { name: "a", idx: 1, rate: 240, qty: 50 },
  { name: "b", idx: 2, rate: 450, qty: 10 },
  { name: "c", idx: 3, rate: 260, qty: 30 },
];
const frm = {
  doc: { docstatus: 0, items },
  dirtyCalled: false,
  refresh_field(field) { assert.equal(field, "items"); },
  dirty() { this.dirtyCalled = true; },
  remove_custom_button() {},
  add_custom_button() {},
};
handlers["Sales Order"].refresh(frm);
context.window.solua_home_sales_order_item_sort.sortItems(frm, "rate_desc");
assert.deepEqual(frm.doc.items.map((row) => row.name), ["b", "c", "a"]);
assert.deepEqual(frm.doc.items.map((row) => row.idx), [1, 2, 3]);
assert.equal(frm.dirtyCalled, true);
context.window.solua_home_sales_order_item_sort.sortItems(frm, "qty_asc");
assert.deepEqual(frm.doc.items.map((row) => row.name), ["b", "c", "a"]);
context.window.solua_home_sales_order_item_sort.sortItems(frm, "original");
assert.deepEqual(frm.doc.items.map((row) => row.name), ["a", "b", "c"]);
assert.equal(alerts.length, 3);
console.log("PASS: Sales Order item sorting persists order, indexes, and original-order restore");
