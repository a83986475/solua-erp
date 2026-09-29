const assert = require("assert");
const fs = require("fs");
const vm = require("vm");

const root = `${__dirname}/..`;
const quickEntryPath = `${root}/public/js/item_quick_entry.js`;
const stockPath = `${root}/api/stock.py`;
const quickEntry = fs.readFileSync(quickEntryPath, "utf8");
const stock = fs.readFileSync(stockPath, "utf8");

class QuickEntryForm {
	set_meta_and_mandatory_fields() {
		this.meta = {
			fields: [
				{ fieldname: "valuation_rate", fieldtype: "Currency" },
				{ fieldname: "standard_rate", fieldtype: "Currency" },
			],
		};
		this.docfields = this.existing ? [{ fieldname: "standard_rate" }] : [];
	}

	render_dialog() {
		const field = () => ({
			set_label(value) {
				this.label = value;
			},
			set_description(value) {
				this.description = value;
			},
		});
		this.dialog = { fields_dict: { valuation_rate: field(), standard_rate: field() } };
	}

	get_field(fieldname) {
		return this.dialog.fields_dict[fieldname];
	}
}

const context = {
	frappe: {
		ui: { form: { QuickEntryForm } },
	},
	setTimeout,
};
vm.runInNewContext(quickEntry, context);
const form = new context.frappe.ui.form.ItemQuickEntryForm();
form.set_meta_and_mandatory_fields();
form.set_meta_and_mandatory_fields();

assert.deepStrictEqual(
	form.docfields.map(({ fieldname, label, description }) => ({ fieldname, label, description })),
	[
		{ fieldname: "valuation_rate", label: "成本价", description: "库存物料成本必须大于 0" },
		{ fieldname: "standard_rate", label: "一级批发售价", description: "保存后写入 Wholesale Selling" },
	]
);

const existingForm = new context.frappe.ui.form.ItemQuickEntryForm();
existingForm.existing = true;
existingForm.set_meta_and_mandatory_fields();
existingForm.render_dialog();
assert.deepStrictEqual(
	Object.values(existingForm.dialog.fields_dict).map(({ label, description }) => ({ label, description })),
	[
		{ label: "成本价", description: "库存物料成本必须大于 0" },
		{ label: "一级批发售价", description: "保存后写入 Wholesale Selling" },
	]
);

const priceHook = stock.slice(stock.indexOf("def auto_create_item_price"));
assert(priceHook.includes('price_list = "Wholesale Selling"'));
assert(!priceHook.includes('"price_list": "Standard Selling"'));
console.log("item quick entry and wholesale price checks passed");
