(function () {
	function register() {
		if (!frappe.ui || !frappe.ui.form || !frappe.ui.form.QuickEntryForm) {
			return false;
		}
		if (frappe.ui.form.ItemQuickEntryForm) {
			return true;
		}

		frappe.ui.form.ItemQuickEntryForm = class ItemQuickEntryForm extends frappe.ui.form.QuickEntryForm {
			set_meta_and_mandatory_fields() {
				super.set_meta_and_mandatory_fields();
				const fields = this.meta.fields || [];

				[
					["valuation_rate", "成本价", "库存物料成本必须大于 0"],
					["standard_rate", "一级批发售价", "保存后写入 Wholesale Selling"],
				].forEach(([fieldname, label, description]) => {
					const index = this.docfields.findIndex((field) => field.fieldname === fieldname);
					if (index >= 0) {
						this.docfields[index] = { ...this.docfields[index], label, description };
						return;
					}
					const source = fields.find((field) => field.fieldname === fieldname);
					if (!source) {
						return;
					}
					this.docfields.push({ ...source, label, description });
				});
			}

			render_dialog() {
				super.render_dialog();
				[
					["valuation_rate", "成本价", "库存物料成本必须大于 0"],
					["standard_rate", "一级批发售价", "保存后写入 Wholesale Selling"],
				].forEach(([fieldname, label, description]) => {
					const field = this.get_field(fieldname);
					if (field) {
						field.set_label(label);
						field.set_description(description);
					}
				});
			}
		};
		return true;
	}

	if (!register()) {
		let attempts = 0;
		const retry = () => {
			if (!register() && attempts++ < 20) {
				setTimeout(retry, 250);
			}
		};
		retry();
	}
})();
