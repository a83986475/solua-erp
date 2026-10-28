const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");
const vm = require("node:vm");
const root = path.resolve(__dirname, "..");
const script = "public/js/pick_list_order_update_v20261016.js";
assert.ok(fs.readFileSync(path.join(root, "hooks.py"), "utf8").split("\n").some(line => line.trim().startsWith('"Pick List": [') && line.includes(script)));
assert.ok(fs.readFileSync(path.join(__dirname, "release_whitelist.txt"), "utf8").includes(script));
let handler, action, dialog, alerts = [], messages = [], calls = [], dirty = false;
let preview = {
    pick_list: "PICK-1", sales_order: "<script>SO</script>", token: "confirmed-token", changed: true,
    before_rows: 1, after_rows: 2, unplanned: [], changes: [{
        action: "调整", item_code: "<img>", item_name: "Rod", warehouse: "WH", uom: "Box", stock_uom: "Piece",
        before_qty: 2, after_qty: 1, before_stock_qty: 24, after_stock_qty: 12,
    }],
};
const frappe = {
    utils: { escape_html: s => s.replaceAll("&", "&amp;").replaceAll("<", "&lt;").replaceAll(">", "&gt;") },
    ui: {
        form: { on(dt, handlers) { handler = handlers.refresh; } },
        Dialog: class {
            constructor(options) { this.options = options; dialog = this; }
            show() { this.visible = true; }
            hide() { this.visible = false; }
            get_primary_btn() { return { prop() {} }; }
        },
    },
    async call(options) { calls.push(options); return { message: options.method.endsWith("preview") ? preview : { name: "PICK-1", docstatus: 0 } }; },
    msgprint(message) { messages.push(message); },
    show_alert(message) { alerts.push(message); },
};
vm.runInNewContext(fs.readFileSync(path.join(root, script), "utf8"), { frappe, __: s => s });
const frm = {
    doc: { name: "PICK-1", docstatus: 0, purpose: "Delivery" },
    is_new: () => false, is_dirty: () => dirty,
    add_custom_button(label, fn) { action = fn; },
    remove_custom_button() { action = null; },
    async reload_doc() { this.reloaded = true; },
};
(async () => {
    handler(frm);
    assert.equal(typeof action, "function");
    dirty = true;
    await action();
    assert.equal(calls.length, 0, "unsaved edits must not be overwritten");
    dirty = false;
    await action();
    assert.equal(calls.length, 1, "preview must not save");
    assert.equal(dialog.visible, true);
    const html = dialog.options.fields[0].options;
    assert.ok(html.includes("&lt;img&gt;") && html.includes("&lt;script&gt;"));
    assert.ok(html.includes("24 → 12 Piece"), "show box and stock quantities");
    dirty = true;
    await dialog.options.primary_action();
    assert.equal(calls.length, 1, "edits after preview must block apply");
    dirty = false;
    await dialog.options.primary_action();
    assert.equal(calls[1].method, "solua_home.api.pick_list_update.apply");
    assert.equal(calls[1].args.token, preview.token);
    assert.ok(frm.reloaded && alerts.length === 1 && !dialog.visible);
    preview = { ...preview, changed: false, changes: [], unplanned: [{ item_code: "SILVER", planned_qty: 0, order_qty: 24, stock_uom: "Piece" }] };
    await action();
    assert.equal(calls.length, 3, "unchanged preview must not apply");
    assert.ok(messages.at(-1).message.includes("SILVER"));
    frm.doc.docstatus = 1;
    handler(frm);
    assert.equal(action, null, "submitted documents have no update action");
    console.log("PASS: draft button, dirty guards, escaped diff, explicit confirmation, no-op and shortage display");
})().catch(error => { console.error(error); process.exitCode = 1; });
