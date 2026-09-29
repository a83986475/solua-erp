import os, re, json, logging

os.chdir("/home/frappe/frappe-bench/sites")
import frappe
import frappe.utils.logger as _flog
_flog.create_handler = lambda *a, **k: [logging.StreamHandler()]
frappe.init(site="erp.solua.one", sites_path="/home/frappe/frappe-bench/sites")
frappe.connect()
frappe.set_user("Administrator")

from frappe.utils.pdf import inline_private_images

SO = "SAL-ORD-2026-00015"
FORMATS = ["客户订单确认单（颜色版）", "客户订单确认单（公司抬头-新）"]

out = {}
for name in FORMATS:
    h = frappe.get_print("Sales Order", SO, print_format=name, as_pdf=False)
    h = inline_private_images(h)
    styles = re.findall(r"<style[^>]*>(.*?)</style>", h, re.S)
    start = h.find('<div class="print-format">')
    end = h.rfind("</div>", 0, h.find('<div class="action-banner') if '<div class="action-banner' in h else None)
    out[name] = {"styles": styles, "body": h[start:end if end > start else len(h)]}

lh = frappe.get_doc("Letter Head", "Company Letterhead - Grey")
out["__letterhead__"] = {"html": lh.get("content") or lh.get("letter_head") or "", "fields": list(lh.as_dict().keys())}

with open("/tmp/format_probe.json", "w", encoding="utf-8") as fh:
    json.dump(out, fh)

for k, v in out.items():
    if k == "__letterhead__":
        print("letterhead len", len(v["html"]), "has_logo", "img" in v["html"])
    else:
        print(k, "styles", len(v["styles"]), "body", len(v["body"]))
