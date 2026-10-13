// Lifecycle is distinct from delivery, invoice quantity and invoice settlement.
(() => {
    const esc = value => frappe.utils.escape_html(String(value ?? ""));
    const num = value => Number(Number(value || 0).toFixed(3));
    function status_label(doc) {
        if (doc.docstatus === 2) return "已取消";
        if (doc.docstatus === 0) return "草稿";
        return {Closed: "已结束", Completed: "已完成", "On Hold": "暂停中"}[doc.status] || "进行中";
    }
    function details(row) {
        const quantities = (row.quantities || []).map(q => `${__("已送")} ${num(q.delivered)} / ${__("退回")} ${num(q.returned)} / ${__("净交付")} ${num(q.net)} / ${__(row.ended ? "不再交付" : "待交付")} ${num(q.remaining)} ${esc(q.uom)}`).join("；");
        return `<div class="text-muted" style="white-space:normal;line-height:1.8">${[row.delivery_label, row.billing_label, row.payment_label].map(value => esc(__(value))).join(" ｜ ")}${quantities ? `<br>${quantities}` : ""}${row.ended ? `<br>${__("结束原因")}：${esc(row.end_reason)}` : ""}</div>`;
    }
    function end_orders(names, done) {
        if (!names.length) return frappe.msgprint(__("请先选择销售订单"));
        if (names.length > 50) return frappe.msgprint(__("每次最多结束 50 张订单"));
        frappe.prompt([{fieldname: "reason", label: __("结束原因"), fieldtype: "Small Text", reqd: 1,
            description: __("例如：客户取消剩余、缺货不补送、退货后不再补送。结束订单不会清除已发生的交货、发票和欠款。") }], values => {
            return frappe.call({method: "solua_home.api.order_status.close_or_unclose_sales_orders",
                args: {names: JSON.stringify(names), status: "Closed", reason: values.reason}, freeze: true,
                freeze_message: __("正在结束订单…")}).then(() => {frappe.show_alert({message: __("订单已结束，剩余不再交付"), indicator: "blue"}); done();});
        }, __("结束订单（不再交付剩余）"), __("结束订单"));
    }
    const previous = frappe.listview_settings["Sales Order"] || {};
    if (!previous.solua_order_status) {
        const onload = previous.onload, after_render = previous.after_render;
        frappe.listview_settings["Sales Order"] = {...previous, solua_order_status: true,
            get_indicator: doc => [__(status_label(doc)), doc.status === "Completed" ? "green" : (doc.status === "Closed" ? "gray" : "orange"), `status,=,${doc.status}`],
            onload(listview) {
                if (onload) onload.call(this, listview);
                listview.page.actions.find("li").filter(function () {return $(this).text().trim() === __("Close");}).remove();
                listview.page.add_action_item(__("结束订单（不再交付剩余）"), () => end_orders(listview.get_checked_items(true) || [], () => listview.refresh()));
                const setup_columns = listview.setup_columns.bind(listview);
                listview.setup_columns = () => {setup_columns(); listview.columns = listview.columns.filter(col => !["per_delivered", "per_billed"].includes(col.df?.fieldname));};
                listview.setup_columns(); listview.render_header();
                const native_refresh = listview.refresh.bind(listview);
                listview.refresh = (...args) => {
                    if (listview.start === 0) {
                        listview.solua_status_cache = Object.create(null);
                        listview.solua_status_generation = (listview.solua_status_generation || 0) + 1;
                    }
                    return native_refresh(...args);
                };
                const native_after_render = listview.after_render.bind(listview);
                listview.after_render = () => {native_after_render(); this.after_render(listview);};
            },
            after_render(listview) {
                if (after_render) after_render.call(this, listview);
                const names = (listview.data || []).map(row => row.name).filter(Boolean);
                if (!names.length) return;
                const cache = listview.solua_status_cache || (listview.solua_status_cache = Object.create(null));
                const generation = listview.solua_status_generation = (listview.solua_status_generation || 0) + 1;
                const missing = names.filter(name => !cache[name]);
                const render_cached = () => listview.$result.find(".list-row-container").each(function () {
                    const name = decodeURIComponent($(this).find(".list-row-checkbox").attr("data-name") || "");
                    const row = cache[name];
                    if (row && !$(this).find("[data-solua-order-status]").length) $(this).append(`<div data-solua-order-status style="padding:0 12px 8px 38px">${details(row)}</div>`);
                });
                if (!missing.length) return render_cached();
                const batches = [];
                for (let i = 0; i < missing.length; i += 50) batches.push(frappe.call({method: "solua_home.api.order_status.get_order_statuses", args: {names: JSON.stringify(missing.slice(i, i + 50))}}));
                Promise.all(batches).then(responses => {
                    if (generation !== listview.solua_status_generation) return;
                    responses.forEach(response => Object.assign(cache, response.message || {}));
                    render_cached();
                }).catch(() => {if (generation !== listview.solua_status_generation) return; render_cached();});
            },
        };
    }
    frappe.provide("solua_home");
    if (!solua_home.order_status_form_registered) {
        solua_home.order_status_form_registered = true;
        frappe.ui.form.on("Sales Order", {refresh(frm) {
            frm.page.set_indicator(__(status_label(frm.doc)), frm.doc.status === "Completed" ? "green" : (frm.doc.status === "Closed" ? "gray" : "orange"));
            frm.toggle_display(["status", "delivery_status", "billing_status"], false);
            frm.remove_custom_button(__("Close"), __("Status"));
            frm.remove_custom_button(__("Close"));
            if (frm.doc.docstatus === 1 && !["Closed", "Completed", "Cancelled"].includes(frm.doc.status) && frappe.model.can_submit("Sales Order")) {
                frm.add_custom_button(__("结束订单（不再交付剩余）"), () => end_orders([frm.doc.name], () => frm.reload_doc()), __("Status"));
            }
            const name = frm.doc.name, modified = frm.doc.modified;
            frm.solua_status_section?.closest(".form-dashboard-section").remove();
            if (frm.is_new()) return;
            frappe.call({method: "solua_home.api.order_status.get_order_statuses", args: {names: JSON.stringify([name])}}).then(response => {
                if (frm.doc.name !== name || frm.doc.modified !== modified) return;
                frm.solua_status_section?.closest(".form-dashboard-section").remove();
                const row = response.message?.[name];
                if (row) {frm.solua_status_section = frm.dashboard.add_section(`<div><strong>${esc(__(row.status_label))}</strong>${details(row)}</div>`, __("订单履约与结算")); frm.dashboard.show();}
            });
        }});
    }
})();
