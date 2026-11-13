frappe.query_reports["Sales Order Reservations"] = {
 onload: report => report.page.set_title(__("销售订单预留明细")),
 filters: [
  {fieldname: "company", label: __("Company"), fieldtype: "Link", options: "Company", default: frappe.defaults.get_user_default("Company"), reqd: 1},
  {fieldname: "item_code", label: __("物料"), fieldtype: "Link", options: "Item"},
  {fieldname: "warehouse", label: __("仓库"), fieldtype: "Link", options: "Warehouse"},
  {fieldname: "sales_order", label: __("销售订单"), fieldtype: "Link", options: "Sales Order"},
 ],
};
