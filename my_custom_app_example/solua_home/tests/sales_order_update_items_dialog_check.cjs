const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");
const vm = require("node:vm");

const dialogs = [];
class Dialog {
  constructor(options) { this.options = options; dialogs.push(this); }
}
let detail_request;
const frappe = {
  ui: { Dialog, form: { on() {} } },
  utils: { escape_html: String },
  call(options) {
    detail_request = options;
    return Promise.resolve({ message: { item_name: "服务器商品", description: "服务器描述", price_list_rate: 123, uom: "件", warehouse: "W1" } });
  },
};
const erpnext = { utils: { update_child_items(opts) {
  const data = [{ docname: "SOI-1", name: "SOI-1" }];
  new frappe.ui.Dialog({ fields: [{ fieldname: "trans_items", fieldtype: "Table", data, get_data: () => data, fields: [{ fieldname: "item_code" }] }] });
} } };
const scope = { frappe, erpnext, __: value => value, window: {}, document: {}, Promise, Number, String };
vm.runInNewContext(
  fs.readFileSync(path.join(__dirname, "../public/js/wholesale_forms_stock_entry_v20261006.js"), "utf8"),
  scope,
);

const frm = { doc: { doctype: "Sales Order", name: "SO-1", items: [{ name: "SOI-1", additional_notes: "已有备注" }] } };
erpnext.utils.update_child_items({
  frm,
  child_docname: "items",
});
const table = dialogs[0].options.fields[0];
assert.equal(table.data[0].additional_notes, "已有备注");
assert.equal(table.fields.find(field => field.fieldname === "additional_notes").read_only, 0);
assert.equal(frappe.ui.Dialog, Dialog);
const row = table.data[0];
row.item_code = "NEW-ITEM";
const item_code_field = table.fields.find(field => field.fieldname === "item_code");
item_code_field.change.call({ value: "NEW-ITEM", doc: row });
Promise.resolve().then(() => Promise.resolve()).then(() => {
  assert.equal(detail_request.method, "erpnext.stock.get_item_details.get_item_details");
  assert.equal(detail_request.args.ctx.item_code, "NEW-ITEM");
  assert.equal(row.item_name, "服务器商品");
  assert.equal(row.description, "服务器描述");
  assert.equal(row.rate, 123);
  console.log("PASS: Sales Order update dialog exposes editable notes and fetches new item details");
}).catch((error) => {
  console.error(error);
  process.exitCode = 1;
});
