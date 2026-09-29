import os, json, logging

os.chdir("/home/frappe/frappe-bench/sites")
import frappe
import frappe.utils.logger as _flog
_flog.create_handler = lambda *a, **k: [logging.StreamHandler()]
frappe.init(site="erp.solua.one", sites_path="/home/frappe/frappe-bench/sites")
frappe.connect()
frappe.set_user("Administrator")

out = {}
for name in ["PRINT DESIGN 销售订单", "Sales Order DIY", "Sales Order PD v2"]:
    pf = frappe.get_doc("Print Format", name)
    out[name] = {"creation": str(pf.creation), "modified": str(pf.modified),
                 "owner": pf.owner, "modified_by": pf.modified_by, "disabled": pf.disabled}

out["property_setters"] = frappe.get_all("Property Setter",
                                         filters={"property": "default_print_format"},
                                         fields=["name", "doc_type", "value", "creation", "owner"])
out["doctype_default"] = frappe.db.sql(
    "select name, default_print_format from `tabDocType` where default_print_format is not null and default_print_format != ''",
    as_dict=True)
out["default_letterhead"] = frappe.db.get_default("letter_head")
out["company_letterhead"] = frappe.get_all("Company", fields=["name", "default_letter_head"])
out["doc_letterhead_so"] = frappe.get_all("Sales Order", filters={"docstatus": 1},
                                          fields=["name", "letter_head"], limit=3)
print(json.dumps(out, ensure_ascii=True, indent=1, default=str))
frappe.db.rollback()
