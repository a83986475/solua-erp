frappe.query_reports["Solua Delivery Summary"] = {
 onload: report => {
  report.page.set_title(__("交货金额明细"));
  report.page.add_inner_button(__("发送表格到微信"), () => {
   frappe.confirm(__("将当前报表发送到企业微信群，继续吗？"), () => {
    frappe.call({
     method: "solua_home.api.wecom.send_query_report_xlsx_to_wechat",
     args: {report_name: "Solua Delivery Summary", filters: report.get_values()},
     freeze: true,
     freeze_message: __("正在生成并发送报表…"),
    }).then(response => frappe.show_alert({message: __("已发送：{0}", [response.message?.filename]), indicator: "green"}));
   });
  });
 },
 filters: [
  {fieldname: "company", label: __("公司"), fieldtype: "Link", options: "Company", reqd: 1, default: frappe.defaults.get_user_default("Company")},
  {fieldname: "from_date", label: __("开始日期"), fieldtype: "Date", reqd: 1, default: frappe.datetime.get_today()},
  {fieldname: "to_date", label: __("结束日期"), fieldtype: "Date", reqd: 1, default: frappe.datetime.get_today()},
 ]
};
