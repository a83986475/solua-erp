import os, logging, io, json

os.chdir("/home/frappe/frappe-bench/sites")
import frappe
import frappe.utils.logger as _flog
_flog.create_handler = lambda *a, **k: [logging.StreamHandler()]
frappe.init(site="erp.solua.one", sites_path="/home/frappe/frappe-bench/sites")
frappe.connect()
frappe.set_user("Administrator")

from frappe.utils.pdf import get_pdf
import pdfplumber, pypdfium2

pt2mm = 25.4 / 72.0

htmls = {
    "plain": "<html><body style='margin:0'><div style='width:100mm;height:20mm;background:#333'></div>"
             "<div style='font-size:18pt'>AAAAAAAA</div></body></html>",
    "printformat": "<html><body style='margin:0'><div class='print-format' style='max-width:8.3in;padding:0.2in'>"
                   "<div style='width:100mm;height:20mm;background:#333'></div>"
                   "<div style='font-size:18pt'>AAAAAAAA</div></div></body></html>",
    "atpage12": "<html><head><style>@page{size:A4;margin:12mm}</style></head><body style='margin:0'>"
                "<div style='width:100mm;height:20mm;background:#333'></div></body></html>",
}

out = {}
for label, html in htmls.items():
    pdf = get_pdf(html)
    with pdfplumber.open(io.BytesIO(pdf)) as doc:
        page = doc.pages[0]
        rects = [r for r in page.rects]
        boxes = [(round(r["width"] * pt2mm, 1), round(r["height"] * pt2mm, 1),
                  round(r["x0"] * pt2mm, 1), round(r["top"] * pt2mm, 1)) for r in rects]
        words = [(w["text"], round(w["height"] * pt2mm, 2)) for w in page.extract_words()]
        out[label] = {"page_mm": [round(page.width * pt2mm, 1), round(page.height * pt2mm, 1)],
                      "rects(w,h,x,top)": boxes[:3], "words": words[:2]}

print(json.dumps(out, ensure_ascii=True, indent=1))
frappe.db.rollback()
