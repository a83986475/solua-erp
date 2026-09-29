import os, logging, json, re, base64

os.chdir("/home/frappe/frappe-bench/sites")
import frappe
import frappe.utils.logger as _flog
_flog.create_handler = lambda *a, **k: [logging.StreamHandler()]
frappe.init(site="erp.solua.one", sites_path="/home/frappe/frappe-bench/sites")
frappe.connect()
frappe.set_user("Administrator")

from solua_home.api import a4_designer as api

fmt = frappe.get_doc("Print Format", "A4-Designer-Deploy-20260926-v8")
marker = re.search(r"<!--SOLUA_A4_DESIGNER:v1:([^>]+)-->", fmt.html)
config = json.loads(base64.urlsafe_b64decode(marker.group(1).encode()).decode())
doc = frappe.get_doc("Sales Order", "SAL-ORD-2026-00015")
html = frappe.render_template(api._template(api._validate_config(config)), {"doc": doc})
with open("/tmp/a4_fixed_render.html", "w", encoding="utf-8") as fh:
    fh.write(html)
print("written", len(html), "| company-logo:", 'class="company-logo"' in html)
