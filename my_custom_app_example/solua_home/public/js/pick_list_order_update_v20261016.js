// Preview first; the server rechecks the draft and source before saving.
(() => {
    const api = "solua_home.api.pick_list_update.";
    const esc = (value) => frappe.utils.escape_html(String(value ?? ""));
    const qty = (value) => Number(value || 0).toLocaleString(undefined, { maximumFractionDigits: 6 });
    const label = "按最新订单更新";

    const update = async (frm) => {
        if (frm.is_dirty()) {
            frappe.msgprint(__("请先保存当前单据，再按最新订单更新。"));
            return;
        }
        if (frm.__solua_order_update_busy) return;
        frm.__solua_order_update_busy = true;
        try {
            const { message: data } = await frappe.call({
                method: api + "preview", args: { pick_list: frm.doc.name },
                freeze: true, freeze_message: __("正在读取最新订单…"),
            });
            const body = data.changes.map((row) => `<tr><td>${esc(__(row.action))}</td><td>${esc(row.item_code)}<br>${esc(row.item_name)}</td><td>${esc(row.warehouse)}</td><td>${qty(row.before_qty)} → ${qty(row.after_qty)} ${esc(row.uom)}<br>${qty(row.before_stock_qty)} → ${qty(row.after_stock_qty)} ${esc(row.stock_uom)}</td></tr>`).join("");
            const missing = data.unplanned.length ? `<p class="text-danger">${__("以下物料当前可拣计划不足，请核对库存：")}</p><ul>${data.unplanned.map((row) => `<li>${esc(row.item_code)} ${esc(row.item_name)}：${qty(row.planned_qty)} / ${qty(row.order_qty)} ${esc(row.stock_uom)}</li>`).join("")}</ul>` : "";
            if (!data.changed) {
                frappe.msgprint({ title: __(label), message: __("拣货明细已与最新订单及当前可拣库存一致，无需保存。") + missing });
                return;
            }
            const dialog = new frappe.ui.Dialog({
                title: __(label), size: "large",
                fields: [{ fieldtype: "HTML", fieldname: "comparison", options:
                    `<p>${__("销售订单")}：${esc(data.sales_order)}；${__("明细行数")}：${data.before_rows} → ${data.after_rows}</p><div class="table-responsive"><table class="table table-bordered"><thead><tr><th>${__("变更")}</th><th>${__("物料")}</th><th>${__("仓库")}</th><th>${__("更新前 → 更新后")}</th></tr></thead><tbody>${body}</tbody></table></div>${missing}<p>${__("确认后保存原拣货单草稿；请确认仓库尚未按旧单拣货，并重新下发更新后的单据。")}</p>`,
                }],
                primary_action_label: __("确认差异并保存草稿"),
                primary_action: async () => {
                    if (frm.is_dirty()) {
                        frappe.msgprint(__("页面有未保存修改，请关闭弹窗、保存后重新读取。"));
                        return;
                    }
                    const button = dialog.get_primary_btn();
                    button.prop("disabled", true);
                    try {
                        await frappe.call({
                            method: api + "apply", args: { pick_list: data.pick_list, token: data.token },
                            freeze: true, freeze_message: __("正在更新拣货单草稿…"),
                        });
                        dialog.hide();
                        await frm.reload_doc();
                        frappe.show_alert({ message: __("已按最新订单更新并保存草稿。"), indicator: "green" });
                    } finally {
                        button.prop("disabled", false);
                    }
                },
            });
            dialog.show();
        } finally {
            frm.__solua_order_update_busy = false;
        }
    };

    frappe.ui.form.on("Pick List", {
        refresh(frm) {
            frm.remove_custom_button?.(__(label), __("工具"));
            if (!frm.is_new() && Number(frm.doc.docstatus) === 0 && frm.doc.purpose === "Delivery") {
                frm.add_custom_button(__(label), () => update(frm), __("工具"));
            }
        },
    });
})();
