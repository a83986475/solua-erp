import os, json, logging, re

os.chdir("/home/frappe/frappe-bench/sites")
import frappe
import frappe.utils.logger as _flog
_flog.create_handler = lambda *a, **k: [logging.StreamHandler()]
frappe.init(site="erp.solua.one", sites_path="/home/frappe/frappe-bench/sites")
frappe.connect()
frappe.set_user("Administrator")

out = {}
for name in ["批发销售单（颜色版）", "批发销售单（颜色版）新版"]:
    pf = frappe.get_doc("Print Format", name)
    h = pf.html or ""
    c = pf.css or ""
    out[name] = {
        "html_len": len(h), "css_len": len(c), "type": pf.print_format_type,
        "uses_shared_css": "get_solua_print_css" in h,
        "own_at_page": bool(re.search(r"@page", c)),
        "own_h2_rule": bool(re.search(r"h2\s*\{", c)),
        "html_h2": re.findall(r"<h2[^>]*>(.*?)</h2>", h, re.S)[:1],
        "has_company_header": "company-header" in h,
        "undefined_keys": re.findall(r"item\.(\w+)", h)[:0],
        "sku_expr": re.findall(r"\{\{[^}]*item\.sku[^}]*\}\}", h)[:2],
    }
print(json.dumps(out, ensure_ascii=True, indent=1, default=str))
frappe.db.rollback()
