import html as html_mod, json, logging, os, re
from collections import Counter

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
from pdfminer.high_level import extract_pages
from pdfminer.layout import LAParams, LTTextContainer

DOC = "SAL-ORD-2026-00015"


def pdf_lines(path, maxpages=1):
    out = []
    for page in extract_pages(path, laparams=LAParams(), maxpages=maxpages):
        def walk(obj):
            if isinstance(obj, LTTextContainer):
                for line in obj:
                    text = " ".join(line.get_text().split())
                    if text:
                        out.append(text)
                return
            for child in getattr(obj, "_objs", []):
                walk(child)
        walk(page)
    return out


def html_lines(markup):
    soup = BeautifulSoup(markup, "html.parser")
    for tag in soup(["style", "script"]):
        tag.decompose()
    text = soup.get_text("\n")
    return [" ".join(x.split()) for x in text.split("\n") if x.strip()]


ref_page1 = pdf_lines("/tmp/sales_doc_sample.pdf")
ref_all = pdf_lines("/tmp/sales_doc_sample.pdf", maxpages=4)

rows = []
for fmt in frappe.get_all("Print Format", filters={"doc_type": "Sales Order"}, pluck="name"):
    try:
        markup = frappe.get_print("Sales Order", DOC, print_format=fmt, as_pdf=False)
    except Exception as exc:
        rows.append({"format": fmt, "error": str(exc)[:110]})
        continue
    lines = html_lines(markup)
    open("/tmp/html_%s.html" % re.sub(r"[^A-Za-z0-9_.-]", "_", fmt), "w", encoding="utf-8").write(markup)
    rows.append({
        "format": fmt,
        "html_lines": len(lines),
        "hit_page1": sum((Counter(ref_page1) & Counter(lines)).values()),
        "hit_all": sum((Counter(ref_all) & Counter(lines)).values()),
        "ratio_page1": round(sum((Counter(ref_page1) & Counter(lines)).values()) / max(len(ref_page1), 1), 3),
        "missing_page1": [x for x in ref_page1 if x not in lines][:5],
    })

rows.sort(key=lambda r: -r.get("ratio_page1", -1))
out = {"ref_page1_lines": len(ref_page1), "rows": rows}
print(json.dumps(out, ensure_ascii=True, indent=1))
