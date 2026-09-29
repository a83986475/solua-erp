import os, logging, json, re

os.chdir("/home/frappe/frappe-bench/sites")
import frappe
import frappe.utils.logger as _flog
_flog.create_handler = lambda *a, **k: [logging.StreamHandler()]
frappe.init(site="erp.solua.one", sites_path="/home/frappe/frappe-bench/sites")
frappe.connect()
frappe.set_user("Administrator")

BASE = "/home/frappe/frappe-bench/apps/solua_home/solua_home/print_format"
SIMPLE = "\u62e3\u8d27\u5355\uff08\u7b80\u7248\uff09"
COLOR = "\u62e3\u8d27\u5355\uff08\u989c\u8272\u7248\uff09"
out = {}

from frappe.modules.import_file import import_file_by_path

for folder in ("pick_list_simple", "pick_list_color"):
    import_file_by_path(f"{BASE}/{folder}/{folder}.json", force=True, ignore_version=True)
frappe.db.commit()

out["formats"] = frappe.get_all(
    "Print Format", filters={"doc_type": "Pick List"},
    fields=["name", "module", "custom_format", "standard", "disabled"], order_by="name")
out["module"] = {f: frappe.get_doc("Print Format", f).module for f in (SIMPLE, COLOR)}
out["has_datetime_slice"] = {
    f: ("doc.get('creation')[:10]" in (frappe.get_doc("Print Format", f).html or ""))
    for f in (SIMPLE, COLOR)}
out["uom_slice"] = {
    f: re.findall(r"Data / \u65e5\u671f: [^<]*", frappe.get_doc("Print Format", f).html or "")
    for f in (SIMPLE, COLOR)}

out["print_property_setters"] = frappe.get_all(
    "Property Setter", filters={"property": ["like", "%print%"], "doc_type": "Pick List"},
    fields=["name", "doc_type", "field_name", "property", "value"])

pl = frappe.get_all("Pick List", filters={"docstatus": 1}, fields=["name"], order_by="creation desc", limit=1)
out["renders"] = {}
if pl:
    doc = frappe.get_doc("Pick List", pl[0].name)
    for fmt_name in (SIMPLE, COLOR):
        try:
            html = frappe.get_print("Pick List", doc.name, print_format=fmt_name, as_pdf=False)
            out["renders"][fmt_name] = {
                "ok": True,
                "title": fmt_name.split("\uff08")[0] in html,
                "spu": "SPU" in html,
                "sku": "SKU / \u8d27\u53f7" in html,
                "qty": "Quantidade / \u6570\u91cf" in html,
                "confirm": "Separado por / \u62e3\u8d27\u4eba" in html and "Motorista / \u53f8\u673a" in html,
                "no_jinja": "{%" not in html,
                "date": re.findall(r"\d{4}-\d{2}-\d{2}", html)[:2],
                "qty_cells": re.findall(r'class="col-qty num">([^<]*)<', html)[:4],
            }
        except Exception as exc:
            out["renders"][fmt_name] = {"ok": False, "error": str(exc)[:160]}
    try:
        with open("/tmp/pick_list_simple_preview.html", "w", encoding="utf-8") as fh:
            fh.write(frappe.get_print("Pick List", doc.name, print_format=SIMPLE, as_pdf=False))
        out["preview_written"] = "/tmp/pick_list_simple_preview.html"
    except Exception as exc:
        out["preview_written"] = "error: " + str(exc)[:120]
    out["sample"] = {"name": doc.name, "customer": doc.get("customer_name") or doc.get("customer"),
                     "rows": len(doc.get("locations") or []),
                     "first_uom": [r.get("uom") for r in (doc.get("locations") or [])[:3]]}

out["box_uom_items"] = frappe.db.count("UOM Conversion Detail", {"uom": "\u7bb1/Caixa"})

print(json.dumps(out, ensure_ascii=True, indent=1, default=str))
frappe.db.rollback()
