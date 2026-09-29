import os, logging, json

os.chdir("/home/frappe/frappe-bench/sites")
import frappe
import frappe.utils.logger as _flog
_flog.create_handler = lambda *a, **k: [logging.StreamHandler()]
frappe.init(site="erp.solua.one", sites_path="/home/frappe/frappe-bench/sites")
frappe.connect()
frappe.set_user("Administrator")

SIMPLE = "\u62e3\u8d27\u5355\uff08\u7b80\u7248\uff09"
COLOR = "\u62e3\u8d27\u5355\uff08\u989c\u8272\u7248\uff09"
out = {"before": {
    "doctype_field": frappe.db.get_value("DocType", "Pick List", "default_print_format"),
    "meta": frappe.get_meta("Pick List").default_print_format,
}}

# 标准 DocType 的默认打印格式应走 Property Setter（和 Sales Order / Delivery Note 一致）；
# 直接写在 DocType 记录上是绕过校验的老做法，这里改回标准并保留规范值。
frappe.make_property_setter({
    "doctype_or_field": "DocType",
    "doctype": "Pick List",
    "property": "default_print_format",
    "value": SIMPLE,
    "property_type": "Link",
}, validate_fields_for_doctype=False)
frappe.db.set_value("DocType", "Pick List", "default_print_format", "")
frappe.db.commit()
frappe.clear_cache(doctype="Pick List")

out["after"] = {
    "doctype_field": frappe.db.get_value("DocType", "Pick List", "default_print_format"),
    "meta": frappe.get_meta("Pick List").default_print_format,
    "setters": frappe.get_all("Property Setter",
                            filters={"doc_type": "Pick List", "property": "default_print_format"},
                            fields=["name", "value", "property_type"]),
}

# 不指定格式渲染：验证默认格式真的生效（走 printview 的 meta.default_print_format）
pick = frappe.get_all("Pick List", filters={"docstatus": 1}, fields=["name"], order_by="creation desc", limit=1)
if pick:
    html = frappe.get_print("Pick List", pick[0].name, as_pdf=False)
    out["default_render"] = {
        "doc": pick[0].name,
        "is_simple": "\u62e3\u8d27\u5355\uff08\u7b80\u7248\uff09" in html,
        "has_spu": "SPU" in html and "SKU / \u8d27\u53f7" in html,
        "has_box": "\u7bb1/Caixa" in html,
        "is_standard_erpnext": "Item Code" in html and "Stock UOM" in html,
        "no_jinja": "{%" not in html,
    }

print(json.dumps(out, ensure_ascii=True, indent=1, default=str))
