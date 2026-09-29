import os, re, json, logging

os.chdir("/home/frappe/frappe-bench/sites")
import frappe
import frappe.utils.logger as _flog
_flog.create_handler = lambda *a, **k: [logging.StreamHandler()]
frappe.init(site="erp.solua.one", sites_path="/home/frappe/frappe-bench/sites")
frappe.connect()
frappe.set_user("Administrator")

NAME = "客户订单确认单（公司抬头-新）"
SO = "SAL-ORD-2026-00015"
REPO = "/home/frappe/frappe-bench/apps/solua_home/solua_home/print_format"
out = {}

pf = frappe.get_doc("Print Format", NAME)
out["new_format"] = {"custom_format": pf.custom_format, "type": pf.print_format_type,
                     "standard": pf.standard, "has_sku_bug": "{{ item.sku | e }}" in (pf.html or ""),
                     "at_page": "@page" in (pf.css or "")}
h = frappe.get_print("Sales Order", SO, print_format=NAME, as_pdf=False)
out["render"] = {"no_jinja": "{%" not in h, "no_undefined": "no such element" not in h,
                 "default_layout": "data-fieldname=" in h or "print-heading" in h,
                 "title": re.findall(r"<h2[^>]*>([^<]*)</h2>", h)[:1],
                 "logo": bool(re.search(r'<img class="solua-global-logo"', h)),
                 "sku_sample": re.findall(r'class="col-sku">([^<]*)<', h)[1:4]}

# audit every Sales Order print format
audit = {}
for f in frappe.get_all("Print Format", filters={"doc_type": "Sales Order"}, fields=["name", "module", "disabled"]):
    rec = {"module": f.module, "disabled": f.disabled}
    # is there a file on disk for it?
    rec["on_disk"] = False
    for d in (os.listdir(REPO) if os.path.isdir(REPO) else []):
        if os.path.isfile(os.path.join(REPO, d, d + ".json")):
            try:
                with open(os.path.join(REPO, d, d + ".json"), encoding="utf-8") as fh:
                    if json.load(fh).get("name") == f.name:
                        rec["on_disk"] = True
            except Exception:
                pass
    try:
        hh = frappe.get_print("Sales Order", SO, print_format=f.name, as_pdf=False)
        rec["ok"] = True
        rec["precision_bug"] = False
    except Exception as exc:
        rec["ok"] = False
        rec["error"] = str(exc)[:110]
        rec["precision_bug"] = "precision" in str(exc)
    audit[f.name] = rec
out["audit"] = audit
out["broken_count"] = sum(1 for v in audit.values() if not v["ok"])

print(json.dumps(out, ensure_ascii=True, indent=1, default=str))
frappe.db.rollback()
