frappe.query_reports["Item-wise Sales History"] = {
	onload: (report) => {
		report.page.add_inner_button(__("发送表格到微信"), () => {
			frappe.confirm(__("将当前报表发送到企业微信群，继续吗？"), () => {
				frappe.call({
					method: "solua_home.api.wecom.send_query_report_xlsx_to_wechat",
					args: { report_name: "Item-wise Sales History", filters: report.get_values() },
					freeze: true,
					freeze_message: __("正在生成并发送报表…"),
				}).then((response) => frappe.show_alert({ message: __("已发送：{0}", [response.message?.filename]), indicator: "green" }));
			});
		});
	},
	filters: [
		{fieldname: "company", label: __("Company"), fieldtype: "Link", options: "Company", default: frappe.defaults.get_user_default("Company"), reqd: 1},
		{fieldname: "from_date", label: __("From Date"), fieldtype: "Date", default: frappe.datetime.add_months(frappe.datetime.get_today(), -1), reqd: 1},
		{fieldname: "to_date", label: __("To Date"), fieldtype: "Date", default: frappe.datetime.get_today(), reqd: 1},
		{fieldname: "item_group", label: __("Item Group"), fieldtype: "Link", options: "Item Group"},
		{fieldname: "item_code", label: __("Item"), fieldtype: "Link", options: "Item"},
		{fieldname: "customer", label: __("Customer"), fieldtype: "Link", options: "Customer"},
	],
};
