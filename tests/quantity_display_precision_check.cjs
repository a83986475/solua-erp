const assert = require("node:assert/strict");
const fs = require("node:fs");
const vm = require("node:vm");

const handlers = {};
const settings = { formatter(value, row, column, data, defaultFormatter) {
	return defaultFormatter(value, row, column, data);
} };
const frappe = {
	query_reports: { "Item-wise Sales History": settings },
	ui: { form: { on(doctype, events) { handlers[doctype] = events; } } },
};
const window = {};
vm.runInNewContext(fs.readFileSync(require.resolve("../public/js/quantity_display_precision_v20261004.js"), "utf8"), { frappe, window, Proxy, Number, Math, Object });

let defaultCalls = 0;
const defaultFormatter = (value) => { defaultCalls++; return String(value); };
assert.equal(settings.formatter(2.5, 0, { fieldname: "quantity" }, {}, defaultFormatter), "3");
assert.equal(settings.formatter(2.5, 0, { fieldname: "rate" }, {}, defaultFormatter), "2.5");
assert.equal(defaultCalls, 2, "existing/default report formatter remains in use");
assert.equal(settings.__solua_qty_precision, true);

const field = (fieldname, fieldtype = "Float") => ({ fieldname, fieldtype, precision: 3 });
const qty = { df: field("qty") }, rate = field("rate"), totalQty = field("total_qty");
const frm = {
	meta: { fields: [totalQty, rate] },
	fields_dict: { items: { df: { fieldtype: "Table" }, grid: { get_field(name) { return name === "qty" ? qty : name === "rate" ? rate : null; } } } },
};
handlers["Sales Order"].refresh(frm);
assert.equal(qty.df.precision, "0");
assert.equal(totalQty.precision, "0");
assert.equal(rate.precision, 3, "price precision is unchanged");
assert.deepEqual([...window.solua_home_quantity_display.reportFields["Item-wise Sales History"]], ["quantity", "delivered_quantity"]);
console.log("quantity_display_precision_check: OK");
