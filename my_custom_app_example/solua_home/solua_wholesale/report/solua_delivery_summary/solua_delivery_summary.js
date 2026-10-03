frappe.query_reports["Solua Delivery Summary"] = {
 onload: report => report.page.set_title(__("交货金额明细")),
 filters: [
  {fieldname: "company", label: __("公司"), fieldtype: "Link", options: "Company", reqd: 1, default: frappe.defaults.get_user_default("Company")},
  {fieldname: "from_date", label: __("开始日期"), fieldtype: "Date", reqd: 1, default: frappe.datetime.get_today()},
  {fieldname: "to_date", label: __("结束日期"), fieldtype: "Date", reqd: 1, default: frappe.datetime.get_today()},
 ]
};
