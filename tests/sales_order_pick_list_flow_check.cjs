const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");
const vm = require("node:vm");

const root = path.resolve(__dirname, "..");
const script = "public/js/sales_order_pick_list_flow_v20261105.js";
const source = fs.readFileSync(path.join(root, script), "utf8");
assert.ok(fs.readFileSync(path.join(root, "hooks.py"), "utf8").includes(script));

let refresh;
let action;
let calls = [];
let routes = [];
let active = [{name: "STO-PICK-1", docstatus: 0, status: "Draft", items: [{item_code: "ITEM-1", remaining_qty: 2}]}];
const frappe = {
    ui: {form: {on(doctype, handlers) { assert.equal(doctype, "Sales Order"); refresh = handlers.refresh; }}},
    call: async options => {
        calls.push(options);
        if (options.method.includes("get_active_pick_lists")) return {message: active};
        return {message: {doctype: "Delivery Note", name: "DN-1", __islocal: 1}};
    },
    model: {sync() {}},
    set_route(...args) { routes.push(args); },
};
vm.runInNewContext(source, {frappe, __: value => value});

const frm = {
    doc: {name: "SO-1", docstatus: 1, status: "To Deliver"},
    is_new: () => false,
    remove_custom_button() {},
    add_custom_button(label, handler) { assert.equal(label, "继续处理拣货单"); action = handler; },
};

(async () => {
    refresh(frm);
    await new Promise(resolve => setImmediate(resolve));
    assert.equal(typeof action, "function");
    action();
    assert.deepEqual(routes.at(-1), ["Form", "Pick List", "STO-PICK-1"]);

    active = [{name: "STO-PICK-2", docstatus: 1, status: "Open", items: [{item_code: "ITEM-1", remaining_qty: 2}]}];
    action = null;
    refresh(frm);
    await new Promise(resolve => setImmediate(resolve));
    action();
    await new Promise(resolve => setImmediate(resolve));
    assert.equal(calls.at(-1).method, "erpnext.stock.doctype.pick_list.mapper.create_dn_for_pick_lists");
    assert.deepEqual(routes.at(-1), ["Form", "Delivery Note", "DN-1"]);
    console.log("PASS: Sales Order routes Draft Pick Lists to picking and submitted Pick Lists to Delivery Note");
})().catch(error => { console.error(error); process.exitCode = 1; });
