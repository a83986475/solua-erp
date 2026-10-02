frappe.query_reports["Template Stock Tree"] = {
 tree: true,
 name_field: "node_id",
 parent_field: "parent_id",
 initial_depth: 0,
 filters: [
  {fieldname: "company", label: __("Company"), fieldtype: "Link", options: "Company", reqd: 1, default: frappe.defaults.get_user_default("Company")},
  {fieldname: "warehouse", label: __("Warehouse"), fieldtype: "Link", options: "Warehouse", get_query: () => ({filters: {is_group: 0, company: frappe.query_report.get_filter_value("company")}})},
  {fieldname: "template", label: __("模板货号"), fieldtype: "Link", options: "Item", get_query: () => ({filters: {has_variants: 1}})}
 ]
};
