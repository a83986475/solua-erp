// Keep Sales Order delivery actions tied to an active Pick List.
(() => {
    const method = "solua_home.api.stock.get_active_pick_lists_for_sales_order";
    const action_label = __("继续处理拣货单");

    function pick_list_label(pick_list) {
        const items = (pick_list.items || []).map(row => `${row.item_code} × ${row.remaining_qty}`).join(", ");
        return `${pick_list.name} · ${pick_list.status || __("Draft")} · ${items}`;
    }

    function open_or_create_delivery(frm, pick_list) {
        if (Number(pick_list.docstatus) === 0) {
            frappe.set_route("Form", "Pick List", pick_list.name);
            return;
        }

        frappe.call({
            method: "erpnext.stock.doctype.pick_list.pick_list.create_dn_for_pick_lists",
            args: {
                source_name: pick_list.name,
                kwargs: JSON.stringify({sales_order: frm.doc.name}),
            },
            freeze: true,
            freeze_message: __("正在从拣货单生成交货单…"),
        }).then(response => {
            const delivery_note = response.message;
            if (!delivery_note) return;
            frappe.model.sync(delivery_note);
            frappe.set_route("Form", "Delivery Note", delivery_note.name);
        });
    }

    function choose_pick_list(frm, pick_lists) {
        if (pick_lists.length === 1) {
            open_or_create_delivery(frm, pick_lists[0]);
            return;
        }

        const dialog = new frappe.ui.Dialog({
            title: __("选择有效拣货单"),
            fields: [{
                fieldname: "pick_list",
                label: __("拣货单"),
                fieldtype: "Select",
                options: pick_lists.map(pick_list_label).join("\n"),
                reqd: 1,
            }],
            primary_action_label: __("继续"),
            primary_action(values) {
                const index = pick_lists.map(pick_list_label).indexOf(values.pick_list);
                if (index < 0) return;
                dialog.hide();
                open_or_create_delivery(frm, pick_lists[index]);
            },
        });
        dialog.show();
    }

    frappe.ui.form.on("Sales Order", {
        refresh(frm) {
            frm.remove_custom_button(action_label, __("Create"));
            if (frm.is_new() || frm.doc.docstatus !== 1 || ["Closed", "Completed", "Cancelled"].includes(frm.doc.status)) {
                return;
            }

            frappe.call({
                method,
                args: {sales_order: frm.doc.name},
            }).then(response => {
                const pick_lists = response.message || [];
                if (!pick_lists.length) return;

                // The standard Sales Order -> Delivery Note mapper is unsafe here.
                frm.remove_custom_button(__("Delivery Note"), __("Create"));
                frm.remove_custom_button(__("Delivery Note"));
                frm.add_custom_button(action_label, () => choose_pick_list(frm, pick_lists), __("Create"));
            });
        },
    });
})();
