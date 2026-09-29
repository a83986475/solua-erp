import os, re, json, logging

os.chdir("/home/frappe/frappe-bench/sites")
import frappe
import frappe.utils.logger as _flog
_flog.create_handler = lambda *a, **k: [logging.StreamHandler()]
frappe.init(site="erp.solua.one", sites_path="/home/frappe/frappe-bench/sites")
frappe.connect()
frappe.set_user("Administrator")

out = {}

for name in ["客户订单确认单（A4新版）", "客户订单确认单（颜色版）-紧凑版", "客户订单确认单（颜色版）-紧凑无边框版"]:
    pf = frappe.get_doc("Print Format", name)
    h = pf.html or ""
    out[name] = {
        "html_len": len(h), "css_len": len(pf.css or ""), "type": pf.print_format_type,
        "custom_format": pf.custom_format,
        "precision_calls": re.findall(r"format_print_money\([^)]*precision[^)]*\)", h)[:6],
        "fmt_money_calls": re.findall(r"fmt_money\([^)]*\)", h)[:6],
        "has_company_header": "company-header" in h,
        "h2": re.findall(r"<h2[^>]*>(.*?)</h2>", h, re.S)[:1],
        "line6": "\n".join(h.split("\n")[5:7])[:400],
    }

# PRINT DESIGN format
pf = frappe.get_doc("Print Format", "PRINT DESIGN 销售订单")
out["PRINT DESIGN 销售订单"] = {
    "type": pf.print_format_type, "custom_format": pf.custom_format, "standard": pf.standard,
    "html_len": len(pf.html or ""), "css_len": len(pf.css or ""),
    "html_none": pf.html is None, "css_none": pf.css is None,
    "raw_printing": pf.get("raw_printing"), "print_format_builder": pf.get("print_format_builder"),
    "html_head": (pf.html or "")[:400],
    "fields": sorted([f for f in pf.as_dict().keys() if "print" in f or "raw" in f or "json" in f]),
}

print(json.dumps(out, ensure_ascii=True, indent=1, default=str))
frappe.db.rollback()
