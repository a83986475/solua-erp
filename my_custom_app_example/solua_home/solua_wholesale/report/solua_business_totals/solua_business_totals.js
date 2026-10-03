(() => {
 const metrics = {orders: "总订单金额", invoices: "总开票金额", receivable: "总应收款", paid: "总已付金额"};
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
   return Promise.resolve(report.set_filter_value({period: saved.period || "本月", from_date: saved.from_date || "", to_date: saved.to_date || ""}))
    .finally(() => { restoring = false; if (!report._no_refresh) report.refresh(); });
   return;
  }
  const settings = {period: report.get_filter_value("period"), from_date: report.get_filter_value("from_date"), to_date: report.get_filter_value("to_date")};
  try { localStorage.setItem(storageKey(metric), JSON.stringify(settings)); } catch (_) {}
  if (settings.period !== "自定义" || (settings.from_date && settings.to_date)) report.refresh();
 }
 frappe.query_reports["Solua Business Totals"] = {
  onload: report => { report.solua_initialized = true; return changed(report, true); },
  filters: [
   {fieldname: "company", label: __("公司"), fieldtype: "Link", options: "Company", reqd: 1, default: frappe.defaults.get_user_default("Company"), on_change: report => changed(report)},
   {fieldname: "metric", label: __("指标"), fieldtype: "Select", options: Object.entries(metrics).map(([value, label]) => ({value, label: __(label)})), default: "orders", reqd: 1, on_change: report => changed(report, true)},
   {fieldname: "period", label: __("时间范围"), fieldtype: "Select", options: Object.keys(periods).join("\n"), default: "本月", reqd: 1, on_change: report => changed(report)},
   {fieldname: "from_date", label: __("开始日期"), fieldtype: "Date", depends_on: "eval:doc.period=='自定义'", on_change: report => changed(report)},
   {fieldname: "to_date", label: __("结束日期"), fieldtype: "Date", depends_on: "eval:doc.period=='自定义'", on_change: report => changed(report)},
  ],
 };
})();
