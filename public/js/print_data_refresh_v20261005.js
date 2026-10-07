(function () {
    "use strict";

    if (window.__solua_print_data_refresh_loaded) return;
    window.__solua_print_data_refresh_loaded = true;

    const method = "solua_home.api.print_data.refresh_latest";
    const doctypes = ["Sales Order", "Delivery Note", "Sales Invoice", "Pick List"];

    function add_button(frm) {
        if (!frm.doc.name || frm.is_new?.()) return;
        frm.add_custom_button(__("读取最新数据"), async function () {
            if (frm.is_dirty?.()) {
                frappe.msgprint(__("请先保存当前单据，再读取最新数据。"));
                return;
            }
            try {
                const response = await frappe.call({
                    method,
                    args: { doctype: frm.doctype, name: frm.doc.name },
                });
                const result = response.message || {};
                if (result.persisted) await frm.reload_doc();
                frappe.show_alert({
                    message: result.persisted
                        ? __("最新客户、物料和单据资料已写入打印快照。")
                        : __("已读取最新数据；本单据打印将直接使用当前资料。"),
                    indicator: "green",
                });
            } catch (error) {
                frappe.msgprint({
                    title: __("读取最新数据失败"),
                    message: error?.message || __("请检查权限或单据状态。"),
                    indicator: "red",
                });
            }
        });
    }

    doctypes.forEach((doctype) => frappe.ui.form.on(doctype, { refresh: add_button }));
}());
