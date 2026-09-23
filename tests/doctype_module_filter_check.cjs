// Isolated check for the DocType scope (allowlist) used by the DocType list and the
// Print Format "单据类型" dropdown. No site, no network, no data change.
const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");
const vm = require("node:vm");

const base = path.join(__dirname, "..");
const source = fs.readFileSync(path.join(base, "public/js/doctype_module_filter.js"), "utf8");
// The page script runs in its own vm realm, so compare structures as JSON instead of by prototype.
const same = (actual, expected, label) => assert.equal(JSON.stringify(actual), JSON.stringify(expected), label);

const storage = new Map();
const reloads = [];
const alerts = [];
const context = {
	__: (text) => text,
	console,
	localStorage: {
		getItem: (key) => (storage.has(key) ? storage.get(key) : null),
		setItem: (key, value) => storage.set(key, String(value)),
	},
	location: { reload: () => reloads.push("reload") },
};
context.window = context; // inside the browser-like sandbox, window is the global object
const frappe = {
	provide: (namespace) => {
		let target = context;
		for (const key of namespace.split(".")) {
			target[key] = target[key] || {};
			target = target[key];
		}
		return target;
	},
	show_alert: (options) => alerts.push(options && options.message),
};
context.frappe = frappe;
frappe.listview_settings = { DocType: { primary_action() {}, new_doctype_dialog() {} } };
const formHandlers = {};
frappe.ui = { form: { on: (doctype, handlers) => Object.assign(formHandlers, handlers) } };
class FakeListView {
	// Mimics Frappe: setup_defaults builds this.filters, so a pre-set filter survives the call.
	setup_defaults() {
		this.filters = this.filters || [];
		return Promise.resolve();
	}
}
frappe.views = { ListView: FakeListView };
vm.createContext(context);

const coreSettings = frappe.listview_settings.DocType;
const evaluate = () => vm.runInContext(`(function () {\n${source}\n})`, context)();

evaluate();
const scope = context.solua_home.doctype_scope;

// The core DocType settings object must be extended, never replaced.
assert.equal(frappe.listview_settings.DocType, coreSettings, "settings object replaced");
assert.equal(typeof coreSettings.new_doctype_dialog, "function");
assert.equal(typeof coreSettings.primary_action, "function");
assert.equal(context.__solua_home_doctype_scope_loaded, true);

// The allowlist is a short, explicit set of the doctypes this business works with.
const names = scope.names;
assert(names.length > 20 && names.length < 90, "allowlist size looks wrong: " + names.length);
assert.equal(new Set(names).size, names.length, "allowlist has duplicates");
for (const doctype of ["Sales Invoice", "Sales Order", "Delivery Note", "POS Invoice", "Item", "Purchase Order", "Purchase Receipt", "Purchase Invoice", "Payment Entry", "Journal Entry", "Stock Entry", "Stock Reconciliation", "Customer", "Supplier", "Print Format", "Vehicle", "Retail Settings", "XPOS Branding Settings"]) {
	assert(names.includes(doctype), "allowlist is missing: " + doctype);
}
for (const doctype of ["BOM", "Work Order", "Job Card", "Asset", "Project", "Issue", "Lead", "Opportunity", "Web Form", "Subcontracting Order", "Quality Inspection", "Tax Invoice", "Expense Claim"]) {
	assert(!names.includes(doctype), "allowlist must not contain unused doctype: " + doctype);
}
assert.equal(scope.has("Sales Invoice"), true);
assert.equal(scope.has("BOM"), false);

// List filter: name allowlist in the 3-element form (ListView prepends the doctype itself).
assert.equal(typeof coreSettings.filters, "object");
assert.equal(coreSettings.filters.length, 1);
same(coreSettings.filters[0], ["name", "in", names], "list filter must be the allowlist");

// Toggle button switches to "show all" and reloads; the filter getter follows it.
const buttons = [];
coreSettings.onload({ page: { add_inner_button: (label, action) => buttons.push({ label, action }) } });
assert.equal(buttons.length, 1);
assert.equal(buttons[0].label, "显示全部单据类型");
buttons[0].action();
assert.equal(storage.get("solua_home_doctype_show_all"), "1");
assert.deepEqual(reloads, ["reload"]);
assert.equal(coreSettings.filters.length, 0, "show-all must drop the allowlist filter");
assert.equal(scope.is_show_all(), true);
assert.equal(Object.keys(scope.link_filters()).length, 0, "show-all must unfilter the dropdown");

// Toggling back restores the filter.
const secondButtons = [];
coreSettings.onload({ page: { add_inner_button: (label, action) => secondButtons.push({ label, action }) } });
assert.equal(secondButtons[0].label, "只看常用单据类型");
secondButtons[0].action();
assert.equal(storage.get("solua_home_doctype_show_all"), "0");
same(coreSettings.filters[0], ["name", "in", names], "filter must come back after toggling");
same(scope.link_filters(), { name: ["in", names] }, "dropdown filter must come back after toggling");

// Print Format form: doc_type dropdown is scoped, with its own toggle that never reloads.
const queries = [];
const refreshFields = [];
const formButtons = [];
const fakeForm = {
	set_query: (fieldname, getter) => queries.push({ fieldname, getter }),
	refresh_field: (fieldname) => refreshFields.push(fieldname),
	add_custom_button: (label, action) => formButtons.push({ label, action }),
};
assert.equal(typeof formHandlers.onload, "function", "Print Format onload hook missing");
assert.equal(typeof formHandlers.refresh, "function", "Print Format refresh hook missing");
formHandlers.onload(fakeForm);
assert.equal(queries.length, 1);
assert.equal(queries[0].fieldname, "doc_type");
same(queries[0].getter().filters, { name: ["in", names] }, "doc_type query must use the allowlist");
formHandlers.refresh(fakeForm);
assert.equal(formButtons.length, 1);
assert.equal(formButtons[0].label, "显示全部单据类型");
formButtons[0].action();
assert.equal(Object.keys(queries.at(-1).getter().filters).length, 0, "form toggle must unfilter the dropdown");
assert.equal(refreshFields.at(-1), "doc_type");
assert.equal(alerts.at(-1), "单据类型下拉已显示全部");
// one reload per list toggle so far; the form toggle must not add another
assert.equal(reloads.length, 2, "the form toggle must not reload the desk");
const backButtons = [];
fakeForm.add_custom_button = (label, action) => backButtons.push({ label, action });
formHandlers.refresh(fakeForm);
assert.equal(backButtons[0].label, "只看常用单据类型");
backButtons[0].action();
same(queries.at(-1).getter().filters, { name: ["in", names] }, "form toggle must restore the allowlist");
assert.equal(alerts.at(-1), "单据类型下拉只显示常用");

// Repeated evaluation must not wrap onload twice.
const wrappedOnload = coreSettings.onload;
evaluate();
assert.equal(coreSettings.onload, wrappedOnload, "onload wrapped twice");

// Fallback prototype hook: applies for DocType once, keeps existing filters, ignores other doctypes.
const listview = new FakeListView();
listview.doctype = "DocType";
const other = new FakeListView();
other.doctype = "Item";
listview.setup_defaults()
	.then(() => {
		assert.equal(listview.filters.length, 1, "fallback filter not applied");
		assert.equal(listview.filters[0][0], "DocType");
		assert.equal(listview.filters[0][1], "name");
		assert.equal(listview.filters[0][2], "in");
		same(listview.filters[0][3], names, "fallback filter must use the allowlist");
		listview.filters = [["DocType", "name", "=", "Sales Invoice"]];
		return listview.setup_defaults();
	})
	.then(() => {
		assert.equal(listview.filters.length, 1, "fallback duplicated an existing name filter");
		assert.equal(listview.filters[0][2], "=");
		return other.setup_defaults();
	})
	.then(() => {
		assert.equal(other.filters.length, 0, "fallback must not touch other doctypes");
		console.log("PASS: DocType list and print-format dropdown show only the in-use allowlist; core settings preserved; toggles persist; fallback idempotent");
	})
	.catch((error) => {
		console.error(error);
		process.exitCode = 1;
	});
