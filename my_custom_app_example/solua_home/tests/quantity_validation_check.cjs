const assert = require("assert");
const fs = require("fs");
const vm = require("vm");
const source = fs.readFileSync("my_custom_app_example/solua_home/public/js/quantity_validation.js", "utf8");
const registrations = {};
const locals = { "Delivery Note Item": { row1: { qty: 25 } } };
const frm = { doc: { doctype: "Delivery Note", is_return: 1, items: [locals["Delivery Note Item"].row1] } };

const jq = () => ({
    attr() { return this; },
    removeAttr() { return this; },
    each() { return this; },
    off() { return this; },
    on() { return this; },
    closest() { return { length: 0 }; },
});
const frappe = {
    ui: { form: { on(name, events) { registrations[name] = events; } } },
    model: {
        set_value(cdt, cdn, fieldname, value) {
            locals[cdt][cdn][fieldname] = value;
            registrations[cdt][fieldname](frm, cdt, cdn);
        },
    },
    throw(message) { throw new Error(message); },
};

vm.runInNewContext(source, {
    $: jq, frappe, locals, window: { cur_frm: frm }, cur_frm: frm, document: {},
    __: (message, args) => args ? message.replace("{0}", args[0]).replace("{1}", args[1]) : message,
});

registrations["Delivery Note Item"].qty(frm, "Delivery Note Item", "row1");
assert.strictEqual(locals["Delivery Note Item"].row1.qty, -25);

const normal_row = { qty: 25 };
const normal_frm = { doc: { doctype: "Delivery Note", is_return: 0, items: [normal_row] } };
locals["Delivery Note Item"].row2 = normal_row;
registrations["Delivery Note Item"].qty(normal_frm, "Delivery Note Item", "row2");
assert.strictEqual(normal_row.qty, 25);

console.log("quantity validation checks passed");
