// Run: node my_custom_app_example/solua_home/tests/document_table_export_check.cjs
// 单据明细导出（Excel/CSV）与明细底部总数量的前端行为。
const assert = require("node:assert/strict");
const fs = require("node:fs");
const vm = require("node:vm");
const path = require("node:path");

const handlers = {};
const calls = [];
const messages = [];
const opened = [];
const dialogs = [];

class Element {
	constructor(tag) {
		this.tag = tag;
		this.className = "";
		this.textContent = "";
		this.style = {};
		this.children = [];
	}
	querySelector(selector) {
		const name = selector.replace(".", "");
		return this.children.find((child) => child.className.split(" ").includes(name)) || null;
	}
	appendChild(node) {
		this.children.push(node);
		return node;
	}
}

function dialog_stub(options) {
	const dialog = {
		options,
		values: {},
		fields_dict: {},
		get_values() {
			return { ...this.values };
		},
		show() {},
		hide() {},
	};
	for (const field of options.fields || []) {
		if (!field.fieldname) continue;
		dialog.values[field.fieldname] = field.default === undefined ? "" : field.default;
		dialog.fields_dict[field.fieldname] = field;
	}
	dialogs.push(dialog);
	return dialog;
}

const export_options = {
	columns: [
		{ key: "idx", label: "序号", numeric: true },
		{ key: "item_code", label: "货号", numeric: false },
		{ key: "qty", label: "数量", numeric: true },
		{ key: "amount", label: "金额", numeric: true },
		{ key: "ordered_qty", label: "订购数量", numeric: true },
	],
	defaults: ["idx", "item_code", "qty", "amount"],
	formats: [{ value: "xlsx", label: "Excel (.xlsx)" }, { value: "csv", label: "CSV (.csv)" }],
};

const sandbox = {
	window: { open: (url) => opened.push(url) },
	document: { createElement: (tag) => new Element(tag) },
	frappe: {
		ui: {
			Dialog: dialog_stub,
			form: {
				on(doctype, value) {
					handlers[doctype] = value;
				},
			},
		},
		call(options) {
			calls.push(options);
			return Promise.resolve({ message: export_options });
		},
		msgprint: (message) => messages.push(message),
	},
	format_currency: (value, currency) => `${value} ${currency}`,
	__: (text, args) => (Array.isArray(args) ? args.reduce((out, v, i) => out.replace(`{${i}}`, v), text) : text),
	Number,
	String,
	Math,
	Promise,
	URLSearchParams,
	console,
};
vm.runInNewContext(fs.readFileSync(path.join(__dirname, "../public/js/document_table_export.js"), "utf8"), sandbox);
const tools = sandbox.window.solua_home_table_export;
const flush = () => new Promise((resolve) => setImmediate(resolve));

function form(doctype, items, extra = {}) {
	// 拣货单的明细行在 locations 子表里，其余三张都是 items
	const field = doctype === "Pick List" ? "locations" : "items";
	const grid = { wrapper: [new Element("div")], refreshes: 0, refresh() { this.refreshes += 1; } };
	const frm = {
		doctype,
		doc: { name: "DOC-1", currency: "MZN", [field]: items },
		buttons: [],
		fields_dict: { [field]: { grid } },
		item_field: field,
		grid,
		is_new: () => false,
		add_custom_button(label, action, group) { this.buttons.push({ label, action, group }); },
		...extra,
	};
	return frm;
}

const rows = [{ qty: 2.5, amount: 250 }, { qty: 1, amount: 300 }];

(async () => {
	// 只接管这四个单据，不干扰其它表单
	assert.deepEqual(Object.keys(handlers).sort(), ["Delivery Note", "Pick List", "Sales Invoice", "Sales Order"]);
	for (const doctype of ["Sales Order", "Sales Invoice", "Delivery Note", "Pick List"]) {
		assert.equal(typeof handlers[doctype].refresh, "function", doctype);
	}

	// 明细底部：行数 + 总数量（+ 金额）
	const order = form("Sales Order", rows.map((row) => ({ ...row })));
	handlers["Sales Order"].refresh(order);
	const host = order.grid.wrapper[0];
	assert.equal(host.children.length, 1, "the footer must be appended once");
	const footer = host.children[0];
	assert.equal(footer.className, "solua-grid-total small text-muted");
	assert.equal(footer.textContent, "共 2 行 · 总数量 3.5 · 明细金额合计 550 MZN", footer.textContent);
	assert.equal(order.buttons.length, 1);
	assert.equal(order.buttons[0].label, "导出表格");
	assert.equal(order.buttons[0].group, "打印");

	// 明细变化后框架重绘 grid，底部数字跟着变，且不会重复插入
	order.grid.refresh();
	assert.equal(host.children.length, 1, "no duplicate footer after a grid redraw");
	order.doc.items.push({ qty: 0.5, amount: 100 });
	order.grid.refresh();
	assert.equal(footer.textContent, "共 3 行 · 总数量 4 · 明细金额合计 650 MZN", footer.textContent);
	assert.equal(order.grid.refreshes, 2);

	// 拣货单：明细在 locations 子表，且没有金额列
	const pick = form("Pick List", [{ qty: 3 }, { qty: 1.5 }]);
	handlers["Pick List"].refresh(pick);
	assert.equal(pick.item_field, "locations");
	assert.equal(pick.grid.wrapper[0].children[0].textContent, "共 2 行 · 总数量 4.5");
	pick.grid.refresh();
	assert.equal(pick.grid.refreshes, 1, "the locations grid must be hooked, not an items grid");

	// 未保存的新单据不挂按钮，但仍显示总数量
	const fresh = form("Delivery Note", [{ qty: 2 }], { is_new: () => true });
	handlers["Delivery Note"].refresh(fresh);
	assert.equal(fresh.buttons.length, 0, "no export button on an unsaved document");
	assert.equal(fresh.grid.wrapper[0].children[0].textContent.includes("总数量 2"), true);

	// 导出按钮 -> 列选择对话框
	order.buttons[0].action();
	await flush();
	assert.equal(calls.at(-1).method, "solua_home.api.export.get_export_options");
	assert.equal(calls.at(-1).args.doctype, "Sales Order");
	const dialog = dialogs.at(-1);
	assert.equal(dialog.options.title, "导出表格 · DOC-1");
	assert.equal(dialog.options.primary_action_label, "导出 Excel");
	assert.equal(dialog.options.secondary_action_label, "导出 CSV");
	assert(dialog.options.fields.some((field) => field.fieldname === "include_header" && field.default === 1));
	assert(dialog.options.fields.some((field) => field.fieldname === "col_item_code" && field.default === 1));
	assert.equal(dialog.values.col_ordered_qty, 0, "columns outside the defaults start unchecked");
	assert.equal(tools.qty_total(order), 4);
	assert.equal(tools.amount_total(order), 650);

	// 导出 Excel
	dialog.options.primary_action({ ...dialog.values });
	assert.equal(opened.length, 1);
	const xlsx_url = new URL(`http://localhost${opened[0]}`);
	assert.equal(xlsx_url.pathname, "/api/method/solua_home.api.export.export_document_table");
	assert.equal(xlsx_url.searchParams.get("doctype"), "Sales Order");
	assert.equal(xlsx_url.searchParams.get("name"), "DOC-1");
	assert.equal(xlsx_url.searchParams.get("fmt"), "xlsx");
	assert.equal(xlsx_url.searchParams.get("columns"), "idx,item_code,qty,amount");
	assert.equal(xlsx_url.searchParams.get("include_header"), "1");
	assert.equal(xlsx_url.searchParams.get("include_total"), "1");

	// 导出 CSV：勾选变化要带到链接上；取消底部合计行也要生效
	dialog.values.col_ordered_qty = 1;
	dialog.values.include_total = 0;
	dialog.options.secondary_action();
	assert.equal(opened.length, 2);
	const csv_url = new URL(`http://localhost${opened[1]}`);
	assert.equal(csv_url.searchParams.get("fmt"), "csv");
	assert.equal(csv_url.searchParams.get("columns"), "idx,item_code,qty,amount,ordered_qty");
	assert.equal(csv_url.searchParams.get("include_total"), "0");
	assert.equal(csv_url.searchParams.get("include_header"), "1");

	// 一列都不选：提示而不是打开空白文件
	dialog.values.col_idx = 0;
	dialog.values.col_item_code = 0;
	dialog.values.col_qty = 0;
	dialog.values.col_amount = 0;
	dialog.values.col_ordered_qty = 0;
	dialog.options.primary_action({ ...dialog.values });
	assert.equal(opened.length, 2, "an empty selection must not download anything");
	assert.equal(messages.at(-1), "请至少勾选一列");

	// 直接调用导出工具也能用（供其它脚本复用）
	tools.download_table(order, { col_item_code: 1, col_qty: 1 }, export_options.columns, "xlsx");
	assert.equal(opened.length, 3);
	assert.equal(new URL(`http://localhost${opened[2]}`).searchParams.get("columns"), "item_code,qty");

	// 没有 grid 的表单（例如权限裁剪后）不能报错
	const bare = { doctype: "Sales Order", doc: { name: "DOC-2", items: [] }, fields_dict: {}, is_new: () => false,
		add_custom_button() {} };
	handlers["Sales Order"].refresh(bare);

	console.log("PASS: table export button, column dialog, xlsx/csv links, grid total footer");
})().catch((error) => {
	console.error(error);
	process.exitCode = 1;
});
