const assert = require("node:assert/strict");
const vm = require("node:vm");
const fs = require("node:fs");
let eligible = false;
const context = {module: {exports: {}}, flt: value => Number(value || 0), __: value => value};
vm.createContext(context);
vm.runInContext(fs.readFileSync(require.resolve("../public/js/payment_entry_labels_v20261004.js"), "utf8"), context);
context.frappe = {call: async () => ({message: {eligible}})};
const {apply_pronto_pagamento, calculate_pronto_pagamento} = context.module.exports;
function form() {
  return {doc: {docstatus: 0, party_type: "Customer", party: "AN LAN", custom_payment_term: "PRONTO PAGAMENTO", mode_of_payment: "Cash",
    references: [{reference_doctype: "Sales Invoice", reference_name: "invoice", allocated_amount: 100}], deductions: [], paid_amount: 100, received_amount: 100},
    events: {set_unallocated_amount() {}}, refresh_fields() {}, set_intro() {}, add_child() {const row = {}; this.doc.deductions.push(row); return row;}};
}
(async () => {
  const frm = form();
  await apply_pronto_pagamento(frm);
  assert.equal(frm.doc.paid_amount, 100);
  assert.equal(frm.doc.deductions.length, 0);
  eligible = true;
  await apply_pronto_pagamento(frm);
  assert.equal(frm.doc.paid_amount, 97);
  assert.equal(frm.doc.deductions[0].amount, 3);
  eligible = false;
  await apply_pronto_pagamento(frm);
  assert.equal(frm.doc.paid_amount, 100);
  assert.equal(frm.doc.deductions.length, 0);
  frm.doc.docstatus = 1;
  eligible = true;
  await apply_pronto_pagamento(frm);
  assert.equal(frm.doc.paid_amount, 100);
  assert.equal(calculate_pronto_pagamento(154500).net, 149865);
  let resolve;
  context.frappe.call = () => new Promise(done => {resolve = done;});
  const stale = form();
  const pending = apply_pronto_pagamento(stale);
  stale.doc.custom_payment_term = "30 DAY CREDIT";
  await apply_pronto_pagamento(stale);
  resolve({message: {eligible: true}});
  await pending;
  assert.equal(stale.doc.paid_amount, 100);
  console.log("PASS: excluded/ordinary customers, clearing, submitted guard, stale response");
})().catch(error => {console.error(error); process.exitCode = 1;});
