// Delivery Notes already record stock; invoices only record the receivable.
(() => {
    async function protect_stock(frm) {
        const items = (frm.doc.items || []).map(({ delivery_note, sales_order, so_detail, item_code }) =>
            ({ delivery_note, sales_order, so_detail, item_code }));
        const key = JSON.stringify(items);
        frm.__stock_guard_key = key;
        const { message } = await frappe.call({
            method: "solua_home.invoice_stock_guard.delivery_backed", args: { items: key },
        });
        if (frm.__stock_guard_key !== key) return;
        frm.toggle_display("update_stock", !message);
        if (message && frm.doc.docstatus === 0 && frm.doc.update_stock) {
            await frm.set_value("update_stock", 0);
        }
    }
    frappe.ui.form.on("Sales Invoice", {
        refresh: protect_stock,
        update_stock: protect_stock,
    });
    frappe.ui.form.on("Sales Invoice Item", {
        delivery_note: protect_stock, sales_order: protect_stock,
        so_detail: protect_stock, item_code: protect_stock, items_remove: protect_stock,
    });
})();
