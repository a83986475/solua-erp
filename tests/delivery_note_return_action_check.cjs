const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");
const vm = require("node:vm");

const root = path.resolve(__dirname, "..");
const scriptPath = path.join(root, "public", "js", "delivery_note_return_action_v20261010.js");
const hooksPath = path.join(root, "hooks.py");
const source = fs.readFileSync(scriptPath, "utf8");
const hooks = fs.readFileSync(hooksPath, "utf8");

assert.match(hooks, /delivery_note_return_action_v20261010\.js/);

const handlers = {};
const links = [{
	textContent: "换货凭证",
	dataset: { label: encodeURIComponent("换货凭证") },
	setAttribute(name, value) { this[name] = value; },
}];
const domRoot = { querySelectorAll: () => links };
const sandbox = {
	__: (value) => value,
	encodeURIComponent,
	decodeURIComponent,
	setTimeout: (callback) => callback(),
	frappe: { ui: { form: { on(doctype, events) { handlers[doctype] = events; } } } },
};
vm.runInNewContext(source, sandbox, { filename: scriptPath });

handlers["Delivery Note"].refresh({
	doc: { doctype: "Delivery Note", docstatus: 1, is_return: 1 },
	page: { wrapper: { get: () => domRoot } },
});
assert.equal(links[0].textContent, "退货发票/贷记单");
assert.equal(decodeURIComponent(links[0].dataset.label), "退货发票/贷记单");
assert.equal(links[0].title, "生成退货销售发票（贷记单），不是换货单");

const normalLink = { textContent: "换货凭证", dataset: { label: encodeURIComponent("换货凭证") } };
handlers["Delivery Note"].refresh({
	doc: { doctype: "Delivery Note", docstatus: 1, is_return: 0 },
	page: { wrapper: { get: () => ({ querySelectorAll: () => [normalLink] }) } },
});
assert.equal(normalLink.textContent, "换货凭证");

console.log("PASS: submitted return Delivery Note credit-note action is labeled clearly without changing normal Delivery Note actions");
