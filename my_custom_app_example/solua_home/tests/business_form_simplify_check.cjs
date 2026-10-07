const assert = require('assert');
const fs = require('fs');
const vm = require('vm');
const handlers = {};
vm.runInNewContext(fs.readFileSync('my_custom_app_example/solua_home/public/js/business_form_simplify_v20261003.js', 'utf8'), {
    frappe: {ui: {form: {on: (name, events) => handlers[name] = events}}, after_ajax: fn => fn()},
    __: s => s,
    setTimeout: fn => fn(),
});
function form(doctype, extra = {}) {
    const hidden = [], removed = [], changes = [], queries = {};
    return {doc: {doctype, docstatus: 0, ...extra}, fields_dict: new Proxy({}, {get: () => ({})}),
        set_df_property: (field, prop, val) => hidden.push(field),
        remove_custom_button: (button, group) => removed.push([button, group]),
        set_value: (field, value) => {changes.push([field, value]);}, set_query: (field, query) => queries[field] = query, hidden, removed, changes, queries};
}
const invoice = form('Sales Invoice'); handlers['Sales Invoice'].refresh(invoice);
assert(invoice.hidden.includes('is_pos') && invoice.hidden.includes('pos'));
assert(!invoice.hidden.includes('update_stock') && !invoice.hidden.includes('is_return'));
const pos = form('Sales Invoice', {is_pos: 1}); handlers['Sales Invoice'].refresh(pos);
assert.equal(pos.hidden.length, 0);
const dn = form('Delivery Note', {issue_credit_note: 1}); handlers['Delivery Note'].refresh(dn);
assert(dn.hidden.includes('issue_credit_note'));
assert(dn.changes.some(([field, value]) => field === 'issue_credit_note' && value === 0));
assert(dn.removed.some(([button]) => button === 'Delivery Trip'));
assert(!dn.removed.some(([button]) => button === 'Sales Return' || button === 'Sales Invoice'));
console.log('business form simplification checks passed');
const order = form('Sales Order', {order_type: 'Sales'}); handlers['Sales Order'].refresh(order);
assert(order.hidden.includes('is_subcontracted') && order.hidden.includes('order_type'));
assert(order.removed.some(([button]) => button === 'Work Order'));
assert(!order.removed.some(([button]) => ['Purchase Order', 'Pick List', 'Delivery Note'].includes(button)));
for (const dt of ['Purchase Order', 'Purchase Receipt', 'Purchase Invoice']) {
    const purchase = form(dt); handlers[dt].refresh(purchase);
    assert(purchase.hidden.includes('is_subcontracted') && purchase.hidden.includes('apply_tds'));
    assert(!purchase.hidden.includes('update_stock'));
}
const item = form('Item'); handlers.Item.refresh(item);
for (const field of ['has_batch_no', 'has_serial_no', 'is_fixed_asset', 'quality_tab', 'manufacturing']) assert(item.hidden.includes(field));
assert(!item.hidden.includes('stock_uom'));

const entry = form("Stock Entry"); handlers["Stock Entry"].refresh(entry);
const excluded = entry.queries.stock_entry_type().filters.purpose[1];
for (const purpose of ["Manufacture", "Send to Subcontractor", "Repack", "Disassemble"]) assert(excluded.includes(purpose));
for (const purpose of ["Material Receipt", "Material Transfer", "Material Issue"]) assert(!excluded.includes(purpose));
