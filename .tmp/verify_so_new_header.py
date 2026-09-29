import os, logging, json, re

os.chdir("/home/frappe/frappe-bench/sites")
import frappe
import frappe.utils.logger as _flog
_flog.create_handler = lambda *a, **k: [logging.StreamHandler()]
frappe.init(site="erp.solua.one", sites_path="/home/frappe/frappe-bench/sites")
frappe.connect()
frappe.set_user("Administrator")

BASE = "/home/frappe/frappe-bench/apps/solua_home/solua_home/print_format"
FOLDER = "so_new_header"
NAME = "客户订单确认单（公司抬头-新）"
out = {"steps": []}

from frappe.modules.import_file import import_file_by_path
import_file_by_path(f"{BASE}/{FOLDER}/{FOLDER}.json", force=True, ignore_version=True)
frappe.db.commit()

pf = frappe.get_doc("Print Format", NAME)
out["pf"] = {"custom_format": pf.custom_format, "type": pf.print_format_type,
             "standard": pf.standard, "doc_type": pf.doc_type, "module": pf.module}
out["pf_html_len"] = len(pf.html or "")
out["pf_has_sku_bug"] = "{{ item.sku | e }}" in (pf.html or "")

# shared logo css now?
import solua_home.printing.wholesale as wm
css = wm.get_solua_print_css()
out["shared_logo_css"] = re.findall(r"\.solua-global-logo\{[^}]*\}", css)[:1]

so = frappe.get_all("Sales Order", filters={"docstatus": 1}, fields=["name"], order_by="creation desc", limit=1)[0].name
doc = frappe.get_doc("Sales Order", so)
out["so"] = so

html = frappe.get_print("Sales Order", so, print_format=NAME, as_pdf=False)
out["html_probe"] = {
    "no_jinja": "{%" not in html,
    "no_undefined": "no such element" not in html,
    "sku_cells": re.findall(r'class="col-sku">([^<]*)<', html)[:5],
    "title": re.findall(r"<h2[^>]*>([^<]*)</h2>", html)[:1],
    "global_logo": re.findall(r'<img class="solua-global-logo" src="([^"]+)"', html)[:1],
    "company_logo_img": "company-logo" in html,
}
with open("/tmp/so_new_header_render.html", "w", encoding="utf-8") as fh:
    fh.write(html)

# PDF for geometry
try:
    pdf = frappe.get_print("Sales Order", so, print_format=NAME, as_pdf=True)
    with open("/tmp/so_new_header.pdf", "wb") as fh:
        fh.write(pdf)
    out["pdf_bytes"] = len(pdf)
except Exception as exc:
    out["pdf_error"] = str(exc)[:200]

print(json.dumps(out, ensure_ascii=True, indent=1, default=str))
frappe.db.rollback()
