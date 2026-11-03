frappe.query_reports["Template Stock Tree"] = {
 onload: (report) => {
  report.page.set_title(__("库存树报表"));
  report.page.add_inner_button(__("发送表格到微信"), () => {
   frappe.call({
    method: "solua_home.api.wecom.send_template_stock_tree_xlsx_to_wechat",
    args: {filters: frappe.query_report.get_filter_values()},
    freeze: true,
    freeze_message: __("正在生成并发送表格..."),
   }).then((response) => {
    const filename = response.message && response.message.filename;
    frappe.show_alert({
     message: filename ? __("已发送：{0}", [filename]) : __("表格已发送到微信"),
     indicator: "green",
    });
   });
  });
 },
 tree: true,
 name_field: "node_id",
 parent_field: "parent_id",
 initial_depth: 0,
 filters: [
  {fieldname: "company", label: __("Company"), fieldtype: "Link", options: "Company", reqd: 1, default: frappe.defaults.get_user_default("Company")},
  {fieldname: "warehouse", label: __("Warehouse"), fieldtype: "Link", options: "Warehouse", get_query: () => ({filters: {is_group: 0, company: frappe.query_report.get_filter_value("company")}})},
  {fieldname: "template", label: __("模板货号"), fieldtype: "Link", options: "Item", get_query: () => ({filters: {has_variants: 1}})},
  {fieldname: "exclude_legacy", label: __("忽略 LEGACY"), fieldtype: "Check", default: 1}
 ]
};
