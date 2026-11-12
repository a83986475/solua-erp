const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");
const vm = require("node:vm");

const handlers = {};
const pending = [];
const alerts = [];

class Node {
  constructor() {
    this.attributes = {};
    this.listeners = {};
    this.parentNode = { insertBefore() {} };
  }
  addEventListener(type, handler) { (this.listeners[type] ||= []).push(handler); }
  dispatch(type, target) { for (const handler of this.listeners[type] || []) handler({type, target}); }
  setAttribute(key, value) { this.attributes[key] = value; }
  removeAttribute(key) { delete this.attributes[key]; }
}

async function main() {
  let throwNext = false;
  const root = path.resolve(__dirname, "..");
  const guardSource = fs.readFileSync(path.join(root, "public/js/sales_order_async_item_guard_v20261111.js"), "utf8");
  const hooksSource = fs.readFileSync(path.join(root, "hooks.py"), "utf8");
  assert.ok(hooksSource.includes('doctype_js["Sales Order"].append("public/js/sales_order_async_item_guard_v20261111.js")'));
  assert.ok(guardSource.includes("solua_home.api.sales.get_sales_order_item_display"));
  assert.ok(guardSource.includes("erpnext.stock.utils.get_incoming_rate"));
  const wrapper = new Node();
  const row = {
    name: "row-1",
    doctype: "Sales Order Item",
    item_code: "OLD",
    qty: 1,
    uom: "件",
    item_name: "旧名称",
    description: "旧描述",
    custom_additional_notes: "旧说明",
  };
  const frm = {
    doctype: "Sales Order",
    doc: {name: "new-sales-order", docstatus: 0, items: [row]},
    fields_dict: {items: {grid: {}, wrapper}},
    saveCalls: 0,
    save() { this.saveCalls += 1; return Promise.resolve(); },
    disable_save() { this.saveDisabled = true; },
    enable_save() { this.saveDisabled = false; },
    refresh_field(field) { this.refreshed = field; },
  };
  const nativeSync = (docs) => {
    for (const incoming of Array.isArray(docs) ? docs : [docs]) {
      if (incoming.name === row.name) Object.assign(row, incoming);
    }
    return docs;
  };
  const nativeSetValue = (cdt, cdn, fieldname, value) => {
    Object.assign(row, typeof fieldname === "object" ? fieldname : {[fieldname]: value});
    return Promise.resolve();
  };
  const frappe = {
    model: {sync: nativeSync, set_value: nativeSetValue},
    ui: {form: {on(doctype, events) { handlers[doctype] = {...handlers[doctype], ...events}; }}},
    utils: {is_mobile: () => false},
    flags: {},
    call(options) {
      if (throwNext) {
        throwNext = false;
        throw new Error("never");
      }
      return new Promise((resolve, reject) => pending.push({options, resolve, reject}));
    },
    msgprint(message) { alerts.push(message); },
  };
  frm.call = (options) => frappe.call({...options, doc: frm.doc});
  const document = {createElement() { return new Node(); }};
  const context = {
    frappe, window: {}, document, __: (value) => value, cur_frm: frm,
    Promise, Set, Map, Object, Boolean, String, Array, console, setTimeout,
  };
  vm.runInNewContext(
    fs.readFileSync(path.join(__dirname, "../public/js/sales_order_async_item_guard_v20261111.js"), "utf8"),
    context,
  );
  handlers["Sales Order"].setup(frm);

  const state = frm.__solua_sales_order_item_guard;
  assert.equal(state.pending, 0);

  const target = (field) => ({
    dataset: {name: "row-1"},
    value: row[field],
    getAttribute(name) { return name === "data-fieldname" ? field : null; },
    closest() { return {getAttribute: () => "row-1"}; },
  });

  // The latest item selection and edits are local authority over a stale response.
  row.item_code = "NEW";
  wrapper.dispatch("change", target("item_code"));
  const firstPromise = frm.call({method: "process_item_selection"});
  assert.equal(state.pending, 1);
  assert.equal(wrapper.attributes["aria-busy"], "true");
  assert.equal(frm.saveDisabled, true);

  for (const [field, value] of [
    ["qty", 7],
    ["uom", "箱"],
    ["custom_additional_notes", "最新说明"],
    ["item_name", "手工名称"],
    ["description", "手工描述"],
  ]) {
    row[field] = value;
    wrapper.dispatch("input", target(field));
  }
  const secondPromise = frm.call({method: "erpnext.stock.get_item_details.get_conversion_factor"});
  assert.equal(state.pending, 2, "concurrent item requests must share the lock");

  frappe.model.sync([{
    name: "row-1", item_code: "OLD", qty: 1, uom: "件", item_name: "服务端名称",
    description: "服务端描述", custom_additional_notes: "服务端说明", rate: 99,
  }]);
  pending.shift().resolve({message: {ok: true}});
  await firstPromise;
  assert.equal(state.pending, 1, "first response must not release the second request");
  assert.equal(row.item_code, "NEW");
  assert.equal(row.qty, 7);
  assert.equal(row.uom, "箱");
  assert.equal(row.custom_additional_notes, "最新说明");
  assert.equal(row.item_name, "手工名称");
  assert.equal(row.description, "手工描述");
  assert.equal(row.rate, 99, "untouched server fields still flow through");

  const savePromise = frm.save();
  assert.equal(frm.saveCalls, 0, "save must wait while item requests are pending");
  pending.shift().reject(new Error("offline"));
  await assert.rejects(secondPromise, /offline/);
  await savePromise;
  assert.equal(state.pending, 0);
  assert.equal(wrapper.attributes["aria-busy"], undefined);
  assert.equal(frm.saveCalls, 1);
  assert.equal(frm.saveDisabled, false);

  throwNext = true;
  assert.throws(() => frm.call({method: "process_item_selection"}), /never/);
  assert.equal(state.pending, 0, "synchronous request exceptions must restore the lock");
  assert.ok(alerts.length >= 1, "blocked save should explain why it is waiting");
  console.log("PASS: Sales Order item async guard preserves edits, counts concurrent requests, gates save, and recovers errors");
}

main().catch((error) => {
  console.error(error);
  process.exitCode = 1;
});
