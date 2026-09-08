// solua_home / public/js/item_quick_entry.js
// Monkey-patch frappe.ui.form.make_quick_entry，为 Item 添加条码输入字段
// 注册：hooks.py -> app_include_js（全局加载，确保在点击「添加」前 patch 就生效）

frappe.provide("solua_home.item_quick_entry");

(function () {
    if (window.__solua_home_item_quick_entry_patched) return;
    window.__solua_home_item_quick_entry_patched = true;

    const _original_make_quick_entry = frappe.ui.form.make_quick_entry;

    frappe.ui.form.make_quick_entry = function (
        doctype,
        callback,
        on_change,
        default_values
    ) {
        if (doctype !== "Item") {
            return _original_make_quick_entry(
                doctype,
                callback,
                on_change,
                default_values
            );
        }

        // ---- Item 定制 Quick Entry（含条码） ----
        frappe.model.with_doctype(doctype, function () {
            const meta = frappe.get_meta(doctype);
            const required_fields = meta.fields.filter((f) => f.reqd);

            const fields = required_fields.map((f) => ({
                fieldname: f.fieldname,
                label: __(f.label),
                fieldtype: f.fieldtype,
                options: f.options,
                reqd: f.reqd,
                ...(f.fieldtype === "Link" ? { default: f.default } : {}),
            }));

            // 添加条码字段（放在最后）
            fields.push({
                fieldname: "barcode_value",
                label: __("条码"),
                fieldtype: "Data",
                description: __("填入条码值，留空则不创建条码记录"),
            });

            const d = new frappe.ui.Dialog({
                title: __("新建物料"),
                fields: fields,
                primary_action_label: __("保存"),
                secondary_action_label: __("继续编辑"),
                secondary_action() {
                    d.hide();
                    frappe.new_doc(doctype);
                },
                primary_action(values) {
                    const doc = frappe.get_doc({
                        doctype: doctype,
                        ...values,
                    });

                    delete doc.barcode_value;

                    doc.insert().then(() => {
                        if (values.barcode_value) {
                            frappe.call({
                                method: "frappe.client.insert",
                                args: {
                                    doc: {
                                        doctype: "Item Barcode",
                                        parent: doc.name,
                                        parentfield: "barcodes",
                                        parenttype: doctype,
                                        barcode: values.barcode_value,
                                    },
                                },
                                callback(r) {
                                    if (r.message) {
                                        frappe.show_alert({
                                            message: __(
                                                `物料 ${doc.name} 已创建，条码已添加`
                                            ),
                                            indicator: "green",
                                        });
                                    }
                                },
                            });
                        } else {
                            frappe.show_alert({
                                message: __(`物料 ${doc.name} 已创建`),
                                indicator: "green",
                            });
                        }

                        d.hide();
                        frappe.set_route("Form", doctype, doc.name);
                        if (callback) callback(doc);
                    });
                },
            });

            // 应用默认值
            if (default_values) {
                for (const [key, value] of Object.entries(default_values)) {
                    if (key !== "barcode_value") {
                        d.set_value(key, value);
                    }
                }
            }

            d.show();
        });
    };
})();
