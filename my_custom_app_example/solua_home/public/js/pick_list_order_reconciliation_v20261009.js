// Pick List business status and Sales Order reconciliation.
(() => {
    const comparison_api = "solua_home.api.stock.get_pick_list_sales_order_comparison";
    const tolerance = 0.000001;

    const esc = (value) => frappe.utils.escape_html(String(value == null ? "" : value));
    const qty = (value) => {
        const number = Number(value || 0);
        return Number.isFinite(number) ? number.toLocaleString(undefined, { maximumFractionDigits: 3 }) : "0";
    };
    const status_info = (frm) => {
        if (Number(frm.doc.docstatus) === 2) return [__("已取消"), "red"];
        const result = frm.doc.custom_pick_result || "待拣货";
        if (result === "已拣齐") return [__("已拣齐"), "green"];
        if (result === "部分拣货") return [__("部分拣货"), "orange"];
        if (result === "缺货待补") return [__("缺货待补"), "red"];
        return [__("待拣货"), "orange"];
    };

    const render_business_status = (frm) => {
        const [label, color] = status_info(frm);
        frm.page?.set_indicator?.(label, color);
        frm.set_df_property?.("status", "hidden", 1);
    };

    const render_comparison = (frm, data) => {
        const wrapper = frm.fields_dict?.custom_sales_order_comparison?.$wrapper;
        if (!wrapper) return;
        const summary = data?.summary || {};
        const orders = (data?.sales_orders || []).map((name) =>
            `<a href="/app/sales-order/${encodeURIComponent(name)}">${esc(name)}</a>`
        ).join("、") || __("未找到销售订单来源");
        const rows = data?.rows || [];
        const body = rows.length ? rows.map((row) => {
            const shortage = Number(row.shortage_qty || 0);
            const extra = row.extra;
            const row_class = extra || shortage > tolerance ? "solua-pick-compare-shortage" : "solua-pick-compare-ok";
            const status = extra ? __("拣货单多出") : __(row.status || "待确认");
            return `<tr class="${row_class}"><td>${esc(row.item_code)}</td><td>${esc(row.item_name)}</td><td class="text-right">${qty(row.order_qty)}</td><td class="text-right">${qty(row.planned_qty)}</td><td class="text-right">${qty(row.picked_qty)}</td><td class="text-right">${qty(row.shortage_qty)}</td><td>${esc(row.stock_uom || "")}</td><td>${esc(status)}</td></tr>`;
        }).join("") : `<tr><td colspan="8" class="text-muted">${__("保存后才能读取销售订单对比")}</td></tr>`;
        const complete = Boolean(summary.complete);
        wrapper.html(`<style>.solua-pick-compare-shortage{background:#fff1f0;color:#a8071a}.solua-pick-compare-ok{background:#f6ffed;color:#237804}.solua-pick-compare-summary{padding:8px;margin-bottom:8px;border-radius:4px}</style><div class="solua-pick-compare"><div class="solua-pick-compare-summary ${complete ? "solua-pick-compare-ok" : "solua-pick-compare-shortage"}"><b>${__("销售订单")}</b>：${orders}<br><b>${__("订单待拣")}</b> ${qty(summary.order_qty)}　<b>${__("计划拣货")}</b> ${qty(summary.planned_qty)}　<b>${__("实际已拣")}</b> ${qty(summary.picked_qty)}　<b>${__("缺货")}</b> ${qty(summary.shortage_qty)}　<span>${complete ? __("对比通过") : __("存在差异，请处理")}</span></div><div class="table-responsive"><table class="table table-bordered table-sm"><thead><tr><th>${__("物料")}</th><th>${__("名称")}</th><th class="text-right">${__("订单待拣")}</th><th class="text-right">${__("计划拣货")}</th><th class="text-right">${__("实际已拣")}</th><th class="text-right">${__("缺货")}</th><th>${__("库存单位")}</th><th>${__("状态")}</th></tr></thead><tbody>${body}</tbody></table></div></div>`);
    };

    const load_comparison = (frm) => {
        const wrapper = frm.fields_dict?.custom_sales_order_comparison?.$wrapper;
        if (!wrapper) return;
        if (frm.is_new()) {
            wrapper.html(`<div class="text-muted">${__("保存拣货单后显示销售订单完整对比")}</div>`);
            return;
        }
        const request_id = (frm.__solua_pick_compare_request || 0) + 1;
        frm.__solua_pick_compare_request = request_id;
        wrapper.html(`<div class="text-muted">${__("正在读取销售订单对比…")}</div>`);
        frappe.call({ method: comparison_api, args: { pick_list: frm.doc.name } }).then((response) => {
            if (frm.__solua_pick_compare_request !== request_id) return;
            render_comparison(frm, response?.message || {});
        }).catch(() => {
            if (frm.__solua_pick_compare_request === request_id) wrapper.html(`<div class="text-danger">${__("销售订单对比读取失败，请刷新后重试")}</div>`);
        });
    };

    const refresh_pick_list = (frm) => {
        render_business_status(frm);
        load_comparison(frm);
        if (!frm.is_new()) {
            frm.remove_custom_button?.(__("销售订单对比"), __("工具"));
            frm.add_custom_button(__("销售订单对比"), () => load_comparison(frm), __("工具"));
        }
    };

    frappe.ui.form.on("Pick List", {
        refresh: refresh_pick_list,
        custom_pick_result: refresh_pick_list,
        locations_add: refresh_pick_list,
        locations_remove: refresh_pick_list,
    });
})();
