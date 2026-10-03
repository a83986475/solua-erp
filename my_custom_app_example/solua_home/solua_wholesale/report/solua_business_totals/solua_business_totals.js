(() => {
 const metrics = {orders: "总订单金额", invoices: "总开票金额", receivable: "总应收款", paid: "总已付金额", unbilled: "未开票金额"};
 const periods = {"本周": "week", "本月": "month", "本季度": "quarter", "本年": "year", "今天": "today", "自定义": "custom"};
 let restoring = false;
 const storageKey = metric => `solua-business-period:${frappe.session.user}:${metric}`;
 function changed(report, restore = false) {
  if (restoring || (!restore && (report._no_refresh || !report.solua_initialized))) return;
  const metric = report.get_filter_value("metric");
  report.page.set_title(__(metrics[metric]));
  if (restore) {
   let saved = {};
   try { saved = JSON.parse(localStorage.getItem(storageKey(metric)) || "{}"); } catch (_) {}
   restoring = true;
   return Promise.resolve(report.set_filter_value({period: saved.period || (metric === "unbilled" ? "本年" : "本月"), from_date: saved.from_date || "", to_date: saved.to_date || ""}))
    .finally(() => { restoring = false; if (!report._no_refresh) report.refresh(); });
   return;
  }
  const settings = {period: report.get_filter_value("period"), from_date: report.get_filter_value("from_date"), to_date: report.get_filter_value("to_date")};
  try { localStorage.setItem(storageKey(metric), JSON.stringify(settings)); } catch (_) {}
  if (settings.period !== "自定义" || (settings.from_date && settings.to_date)) report.refresh();
 }
 frappe.query_reports["Solua Business Totals"] = {
  onload: report => {
   report.solua_initialized = true;
   report.page.main.off("click.solua-billing").on("click.solua-billing", "[data-bill-delivery]", function () {
    const button = this;
    button.disabled = true;
    frappe.call({method: "solua_home.api.unbilled.prepare_invoice", args: {delivery_note: button.dataset.billDelivery}, freeze: true, freeze_message: __("正在核对未开票数量…")})
     .then(response => {
      const result = response.message || {};
      if (result.draft_invoices?.length === 1) return frappe.set_route("Form", "Sales Invoice", result.draft_invoices[0]);
      if (result.draft_invoices?.length) { frappe.route_options = {name: ["in", result.draft_invoices]}; return frappe.set_route("List", "Sales Invoice"); }
      if (result.invoice) { frappe.model.sync(result.invoice); frappe.set_route("Form", "Sales Invoice", result.invoice.name); }
     }).finally(() => { button.disabled = false; });
   });
   return changed(report, true);
  },
  formatter: (value, row, column, data, default_formatter) => {
   if (column.fieldname === "action" && data?.name && data.doctype === "Delivery Note" && (data.can_invoice || data.draft_invoices?.length)) {
    return `<button type="button" class="btn btn-xs btn-primary" data-bill-delivery="${frappe.utils.escape_html(data.name)}">${frappe.utils.escape_html(data.action)}</button>`;
   }
   return default_formatter(value, row, column, data);
  },
  filters: [
   {fieldname: "company", label: __("公司"), fieldtype: "Link", options: "Company", reqd: 1, default: frappe.defaults.get_user_default("Company"), on_change: report => changed(report)},
   {fieldname: "metric", label: __("指标"), fieldtype: "Select", options: Object.entries(metrics).map(([value, label]) => ({value, label: __(label)})), default: "orders", reqd: 1, on_change: report => changed(report)},
   {fieldname: "period", label: __("时间范围"), fieldtype: "Select", options: Object.keys(periods).join("\n"), default: "本月", reqd: 1, on_change: report => changed(report)},
   {fieldname: "from_date", label: __("开始日期"), fieldtype: "Date", depends_on: "eval:doc.period=='自定义'", on_change: report => changed(report)},
   {fieldname: "to_date", label: __("结束日期"), fieldtype: "Date", depends_on: "eval:doc.period=='自定义'", on_change: report => changed(report)},
  {fieldname: "customer", label: __("客户"), fieldtype: "Link", options: "Customer", on_change: report => changed(report)},
  ],
 };
})();
