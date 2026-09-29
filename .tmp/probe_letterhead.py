import os, logging, json, base64, io

os.chdir("/home/frappe/frappe-bench/sites")
import frappe
import frappe.utils.logger as _flog
_flog.create_handler = lambda *a, **k: [logging.StreamHandler()]
frappe.init(site="erp.solua.one", sites_path="/home/frappe/frappe-bench/sites")
frappe.connect()
frappe.set_user("Administrator")

import pypdfium2 as pdfium
import pdfplumber
pt2mm = 25.4 / 72.0

NAME = "客户订单确认单（公司抬头-新）"
SO = "SAL-ORD-2026-00015"
out = {}

pf = frappe.get_doc("Print Format", NAME)
out["pf_letterhead"] = pf.get("letterhead")
out["default_letterhead"] = frappe.db.get_value("Print Settings", None, "letter_head") or frappe.db.get_default("letter_head")
out["all_letterheads"] = frappe.get_all("Letter Head", fields=["name", "is_default", "disabled"])


def geom(pdf_bytes):
    with pdfplumber.open(io.BytesIO(pdf_bytes)) as pdf:
        page = pdf.pages[0]
        imgs = [{"x0": round(i["x0"] * pt2mm, 1), "top": round(i["top"] * pt2mm, 1),
                 "w": round((i["x1"] - i["x0"]) * pt2mm, 1), "h": round((i["bottom"] - i["top"]) * pt2mm, 1)}
                for i in page.images]
        words = [w for w in page.extract_words() if w["top"] * pt2mm < 25]
        xs = [w["x0"] * pt2mm for w in words] or [0]
        ys = [w["top"] * pt2mm for w in words] or [0]
        return {"images": imgs, "text_x0_min": round(min(xs), 1), "text_top_min": round(min(ys), 1),
                "pages": len(pdf.pages), "width_mm": round(page.width * pt2mm, 1)}


variants = {
    "default": {},
    "no_letterhead": {"no_letterhead": 1},
}
for label, kw in variants.items():
    try:
        pdf = frappe.get_print("Sales Order", SO, print_format=NAME, as_pdf=True, **kw)
        with open(f"/tmp/new_{label}.pdf", "wb") as fh:
            fh.write(pdf)
        out[label] = geom(pdf)
    except Exception as exc:
        out[label] = {"error": str(exc)[:200]}

print(json.dumps(out, ensure_ascii=True, indent=1, default=str))
frappe.db.rollback()
