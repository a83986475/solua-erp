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

out = {}

from frappe.modules.import_file import import_file_by_path

import_file_by_path(f"{BASE}/{FOLDER}/{FOLDER}.json", force=True, ignore_version=True)
frappe.db.commit()

out["exists"] = frappe.db.exists("Print Format", NAME)
pf = frappe.get_doc("Print Format", NAME)
out["pf"] = {"name": pf.name, "doc_type": pf.doc_type, "module": pf.module,
             "standard": pf.standard, "custom_format": pf.custom_format,
             "disabled": pf.disabled}
html = pf.html or ""
out["html_tokens"] = {t: (t in html) for t in
                      ["company-header", "company-logo", "print-format table.items", "solua-global-logo"]}
out["html_len"] = len(html)

out["all_so_formats"] = frappe.get_all(
    "Print Format", filters={"doc_type": "Sales Order"},
    fields=["name", "module", "disabled"], order_by="name")

# render on a real submitted Sales Order
so = frappe.get_all("Sales Order", filters={"docstatus": 1}, fields=["name"], order_by="creation desc", limit=1)
out["renders"] = {}
if so:
    doc = frappe.get_doc("Sales Order", so[0].name)
    out["so"] = {"name": doc.name, "customer": doc.get("customer_name") or doc.get("customer"),
                 "rows": len(doc.get("items") or []), "docstatus": doc.docstatus}

    # company logo presence in print data
    try:
        from solua_home.printing.a4_designer import get_a4_print_data
        data = get_a4_print_data(doc)
        out["company_keys"] = sorted((data.get("company") or {}).keys())
        out["company_logo"] = (data.get("company") or {}).get("logo")
    except Exception as exc:
        out["company_keys"] = "error: " + str(exc)[:160]

    for fmt_name in (NAME,):
        try:
            h = frappe.get_print("Sales Order", doc.name, print_format=fmt_name, as_pdf=False)
            out["renders"][fmt_name] = {
                "ok": True,
                "has_header": "company-header" in h,
                "has_logo_img": "company-logo" in h,
                "logo_src": re.findall(r'class="company-logo"[^>]*src="([^"]+)"', h)[:1],
                "title_center": re.findall(r"<h2[^>]*>([^<]*)</h2>", h)[:2],
                "no_jinja": "{%" not in h,
                "items": h.count("wholesale-items") + h.count("table.items"),
            }
            if fmt_name == NAME:
                with open("/tmp/so_new_header_render.html", "w", encoding="utf-8") as fh:
                    fh.write(h)
        except Exception as exc:
            out["renders"][fmt_name] = {"ok": False, "error": str(exc)[:200]}

# regression: every SO format still renders
out["regression"] = {}
for f in frappe.get_all("Print Format", filters={"doc_type": "Sales Order"}, fields=["name"]):
    try:
        h = frappe.get_print("Sales Order", so[0].name, print_format=f.name, as_pdf=False)
        out["regression"][f.name] = {"ok": True, "no_jinja": "{%" not in h}
    except Exception as exc:
        out["regression"][f.name] = {"ok": False, "error": str(exc)[:160]}

print(json.dumps(out, ensure_ascii=True, indent=1, default=str))
frappe.db.rollback()
