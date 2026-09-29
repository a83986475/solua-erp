import json, os, re

os.chdir("/home/frappe/frappe-bench/sites")
import frappe
import frappe.utils.logger as _flog
_flog.create_handler = lambda *a, **k: [logging.StreamHandler()] if False else [__import__("logging").StreamHandler()]
from frappe.utils import cstr

frappe.init(site="erp.solua.one", sites_path="/home/frappe/frappe-bench/sites")
frappe.connect()
frappe.set_user("Administrator")

out = []
for row in frappe.get_all("Print Format", fields=["name", "doc_type", "css", "html", "modified", "disabled"]):
    blob = cstr(row.html) + "\n" + cstr(row.css)
    if "company-header" not in blob and "company-logo" not in blob:
        continue
    rules = []
    for part in re.split(r"(?<=\})", cstr(row.css) + "".join(re.findall(r"<style[^>]*>(.*?)</style>", cstr(row.html), re.S))):
        if "company-header" in part or "company-logo" in part or ".meta" in part:
            rules.append(" ".join(part.split())[:220])
    out.append({
        "name": row.name, "doc_type": row.doc_type, "modified": str(row.modified), "disabled": row.disabled,
        "html_base64": row.html[:0] if False else len(cstr(row.html)),
        "has_company_img_in_html": 'class="company-logo"' in cstr(row.html),
        "h2_center_in_css": "text-align:center" in blob or "text-align: center" in blob,
        "rules": rules,
    })

print(json.dumps(out, ensure_ascii=True, indent=1))
