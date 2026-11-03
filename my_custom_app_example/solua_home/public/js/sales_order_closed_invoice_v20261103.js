// Closed-order billing: map only submitted delivery quantities that remain unbilled.
(() => {
    frappe.provide("solua_home");
    if (solua_home.closed_invoice_form_registered) return;
    solua_home.closed_invoice_form_registered = true;
    frappe.ui.form.on("Sales Order", {
        refresh(frm) {
            const label = __("为已交付未开票部分开票");
            frm.remove_custom_button(label, __("Create"));
            if (frm.doc.docstatus !== 1 || frm.doc.status !== "Closed" || !frappe.model.can_create("Sales Invoice")) return;
            frm.remove_custom_button(__("Sales Invoice"), __("Create"));
            frm.add_custom_button(label, () => {
                frappe.model.open_mapped_doc({
                    method: "solua_home.api.unbilled.make_sales_invoice_from_closed_sales_order",
                    frm,
                    freeze: true,
                    freeze_message: __("正在生成已交付未开票发票草稿…"),
                });
            }, __("Create"));
        },
    });
})();
