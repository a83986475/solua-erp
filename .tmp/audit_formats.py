import os, re, json, logging

os.chdir("/home/frappe/frappe-bench/sites")
import frappe
import frappe.utils.logger as _flog
_flog.create_handler = lambda *a, **k: [logging.StreamHandler()]
frappe.init(site="erp.solua.one", sites_path="/home/frappe/frappe-bench/sites")
frappe.connect()
frappe.set_user("Administrator")

REPO = "/home/frappe/frappe-bench/apps/solua_home/solua_home/print_format"
disk_names = {}
if os.path.isdir(REPO):
    for d in os.listdir(REPO):
        f = os.path.join(REPO, d, d + ".json")
        if os.path.isfile(f):
            try:
                with open(f, encoding="utf-8") as fh:
                    disk_names[json.load(fh).get("name")] = d
            except Exception as exc:
                disk_names[d] = "ERR:" + str(exc)[:40]

rows = frappe.get_all("Print Format", fields=["name", "doc_type", "module", "disabled",
                                              "custom_format", "print_format_type", "standard"],
                      order_by="doc_type, name")

sample_doc = {}
for dt in ("Sales Order", "Sales Invoice", "Delivery Note", "Pick List"):
    docs = frappe.get_all(dt, filters={"docstatus": 1}, fields=["name"], order_by="creation desc", limit=1)
    if not docs:
        docs = frappe.get_all(dt, fields=["name"], order_by="creation desc", limit=1)
    sample_doc[dt] = docs[0].name if docs else None

out = {"total": len(rows), "sample_docs": sample_doc, "formats": []}
for r in rows:
    rec = dict(r)
    rec["disk_folder"] = disk_names.get(r.name)
    doc = sample_doc.get(r.doc_type)
    if not doc:
        rec["render"] = "no sample doc"
        out["formats"].append(rec)
        continue
    try:
        h = frappe.get_print(r.doc_type, doc, print_format=r.name, as_pdf=False)
        rec["render"] = "ok"
        rec["markers"] = {
            "global_logo": h.count('class="solua-global-logo"'),
            "company_logo": h.count('class="company-logo"'),
            "brand_table": h.count('class="brand"'),
            "company_header": h.count("company-header"),
            "default_layout": h.count("data-fieldname=") + h.count('id="print-heading"'),
            "h2_text": re.findall(r"<h2[^>]*>(.*?)</h2>", h, re.S)[:1],
            "at_page": re.findall(r"@page\s*\{[^}]*\}", h)[:1],
            "undefined": h.count("no such element"),
            "jinja_left": h.count("{%"),
            "letterhead_block": h.count("letterhead-container"),
        }
        # does the format own css define the global logo size?
        pf = frappe.get_doc("Print Format", r.name)
        rec["own_css_at_page"] = "@page" in (pf.css or "")
        rec["own_html_len"] = len(pf.html or "")
        rec["html_has_company_header"] = "company-header" in (pf.html or "")
    except Exception as exc:
        rec["render"] = "FAIL"
        rec["error"] = str(exc)[:150]
    out["formats"].append(rec)

out["letterheads"] = frappe.get_all("Letter Head", fields=["name", "is_default", "disabled", "source"])
print(json.dumps(out, ensure_ascii=True, indent=1, default=str))
frappe.db.rollback()
