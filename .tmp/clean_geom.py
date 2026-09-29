import json, logging, os, re, base64

logging.disable(logging.WARNING)
logging.getLogger("pdfminer").setLevel(logging.ERROR)

os.chdir("/home/frappe/frappe-bench/sites")
import frappe
import frappe.utils.logger as _flog
_flog.create_handler = lambda *a, **k: [logging.StreamHandler()]
frappe.init(site="erp.solua.one", sites_path="/home/frappe/frappe-bench/sites")
frappe.connect()
frappe.set_user("Administrator")

from bs4 import BeautifulSoup
from frappe.utils.pdf import get_pdf
from pdfminer.high_level import extract_pages
from pdfminer.layout import LAParams, LTImage, LTTextContainer
from solua_home.api import a4_designer as api

PT2MM = 25.4 / 72.0
DOC = "SAL-ORD-2026-00015"


def standalone(fragment_html):
    """把片段里的 <style> 提到 head，其余放 body —— wkhtmltopdf 才能正确应用样式。"""
    soup = BeautifulSoup(fragment_html, "html.parser")
    styles = [s.extract() for s in soup.find_all("style")]
    head = "".join(str(s) for s in styles)
    return ('<!doctype html><html><head><meta charset="utf-8">' + head
            + "</head><body>" + str(soup) + "</body></html>")


def geom(path):
    page = next(iter(extract_pages(path, laparams=LAParams(), maxpages=1)))
    height = page.height
    rows = []

    def walk(obj):
        if isinstance(obj, LTImage):
            rows.append(("image", obj.bbox, ""))
            return
        if isinstance(obj, LTTextContainer):
            for line in obj:
                text = " ".join(line.get_text().split())
                if text:
                    rows.append(("text", line.bbox, text[:46]))
            return
        for child in getattr(obj, "_objs", []):
            walk(child)

    walk(page)
    out = []
    for kind, bbox, text in rows:
        x0, y0, x1, y1 = bbox
        out.append({"kind": kind, "text": text, "top": round((height - y1) * PT2MM, 1),
                    "x": round(x0 * PT2MM, 1), "w": round((x1 - x0) * PT2MM, 1),
                    "h": round((y1 - y0) * PT2MM, 1)})
    return [r for r in out if r["top"] < 100]


def brief(rows):
    logo = [r for r in rows if r["kind"] == "image"]
    title = [r for r in rows if "Confirma" in r["text"]]
    return {
        "logo": [[r["top"], r["x"], r["w"], r["h"]] for r in logo],
        "title": [[r["top"], r["x"], r["w"], r["h"]] for r in title],
        "title_center_mm": [round(r["x"] + r["w"] / 2, 1) for r in title],
        "party_left_x": sorted({r["x"] for r in rows if r["x"] < 60 and r["top"] > 25})[:2],
        "party_right_x": sorted({r["x"] for r in rows if 60 <= r["x"] < 150 and r["top"] > 25})[:2],
        "first_party_top": min([r["top"] for r in rows if r["x"] < 60 and r["top"] > 25], default=None),
        "head": [[r["top"], r["x"], r["text"]] for r in rows[:6]],
    }


out = {}
doc = frappe.get_doc("Sales Order", DOC)

fmt = frappe.get_doc("Print Format", "A4-Designer-Deploy-20260926-v8")
config = json.loads(base64.urlsafe_b64decode(
    re.search(r"<!--SOLUA_A4_DESIGNER:v1:([^>]+)-->", fmt.html).group(1).encode()).decode())
fragment = frappe.render_template(api._template(api._validate_config(config)), {"doc": doc})
open("/tmp/designer_new.pdf", "wb").write(get_pdf(standalone(fragment)))
out["designer_current_template"] = brief(geom("/tmp/designer_new.pdf"))

color_html = frappe.get_print("Sales Order", DOC, print_format="\u5ba2\u6237\u8ba2\u5355\u786e\u8ba4\u5355\uff08\u989c\u8272\u7248\uff09", as_pdf=False)
open("/tmp/color_format.pdf", "wb").write(get_pdf(standalone(color_html)))
out["sales_order_color_format"] = brief(geom("/tmp/color_format.pdf"))

out["reference_sample"] = brief(geom("/tmp/sales_doc_sample.pdf"))

print(json.dumps(out, ensure_ascii=True, indent=1, default=str))
