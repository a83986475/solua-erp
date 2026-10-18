const assert = require("node:assert/strict");
const fs = require("node:fs");
const vm = require("node:vm");

const canvases = [];
const container = {
	style: {},
	innerHTML: "",
	replaceChildren() {
		canvases.length = 0;
	},
	appendChild(canvas) {
		canvases.push(canvas);
	},
};
const control = () => ({ show() {}, hide() {} });
class BasePrintView {
	preview() {
		this.htmlPreview = true;
	}
}
class DesignerPrintView extends BasePrintView {
	designer_pdf() {}
}

const pdfjsLib = {
	getDocument() {
		return {
			promise: Promise.resolve({
				numPages: 2,
				getPage: async () => ({
					getViewport: ({ scale }) => ({ width: 100 * scale, height: 140 * scale }),
					render: () => ({ promise: Promise.resolve() }),
				}),
			}),
		};
	},
};
const frappe = {
	ui: { form: { PrintView: DesignerPrintView } },
	router: { on() {} },
	require: async () => {},
	render_template: () => "loading",
	show_alert() {},
	_: (message) => message,
};
const context = {
	frappe,
	window: { pdfjsLib, location: { origin: "https://erp.test" }, devicePixelRatio: 1 },
	document: {
		getElementById: () => container,
		createElement: () => ({ style: {}, getContext: () => ({}) }),
	},
	URLSearchParams,
	__: frappe._,
	console,
	setInterval: (callback) => (queueMicrotask(callback), 1),
	clearInterval() {},
	setTimeout,
	clearTimeout,
};
vm.runInNewContext(
	fs.readFileSync(require.resolve("../public/js/print_preview_pdfjs.js"), "utf8"),
	context
);

const view = Object.assign(new DesignerPrintView(), {
	frm: { doc: { doctype: "Sales Order", name: "SAL-ORD-1" } },
	selected_format: () => "Sales Order PD v2",
	lang_code: "en",
	print_wrapper: { find: () => ({ hide() {} }) },
	inner_msg: control(),
	full_page_btn: control(),
	pdf_btn: control(),
	letterhead_selector: control(),
	sidebar_dynamic_section: control(),
	print_btn: control(),
	sidebar: control(),
	toolbar_print_format_selector: { $wrapper: control() },
	toolbar_language_selector: { $wrapper: control() },
});

(async () => {
	await new Promise((resolve) => setImmediate(resolve));
	assert.equal(DesignerPrintView.prototype.__solua_pdfjs, true);
	await view.designer_pdf({ print_designer_settings: JSON.stringify({ page: { width: 100, height: 140 } }) });
	assert.equal(canvases.length, 2);

	pdfjsLib.getDocument = () => {
		throw new Error("simulated PDF error");
	};
	await view.designer_pdf({ print_designer_settings: JSON.stringify({ page: { width: 100, height: 140 } }) });
	assert.equal(view.htmlPreview, true);
})().catch((error) => {
	console.error(error);
	process.exitCode = 1;
});
