import logging, os, json, re

logging.disable(logging.WARNING)
logging.getLogger("pdfminer").setLevel(logging.ERROR)

os.chdir("/home/frappe/frappe-bench/sites")
import frappe
import frappe.utils.logger as _flog
_flog.create_handler = lambda *a, **k: [logging.StreamHandler()]
frappe.init(site="erp.solua.one", sites_path="/home/frappe/frappe-bench/sites")
frappe.connect()
frappe.set_user("Administrator")

from pdfminer.high_level import extract_pages
from pdfminer.layout import LAParams, LTImage, LTTextContainer

REF = "/tmp/sales_doc_sample.pdf"
DOC = "SAL-ORD-2026-00015"


def layout(path, maxpages=1):
    items = []
    for page in extract_pages(path, laparams=LAParams(), maxpages=maxpages):
        def walk(obj):
            if isinstance(obj, LTImage):
                items.append({"kind": "image", "bbox": [round(v, 1) for v in obj.bbox],
                              "size": [round(obj.width, 1), round(obj.height, 1)]})
                return
            if isinstance(obj, LTTextContainer):
                for line in obj:
                    text = " ".join(line.get_text().split())
                    if text:
                        items.append({"kind": "text", "bbox": [round(v, 1) for v in line.bbox], "text": text})
                return
            for child in getattr(obj, "_objs", []):
                walk(child)
        walk(page)
    return items


def key(item):
    x0, y0, x1, y1 = item["bbox"]
    return (item["text"], round(x0, 0), round(y1, 0))


ref = layout(REF)
ref_keys = {key(i) for i in ref if i["kind"] == "text"}
ref_images = [i for i in ref if i["kind"] == "image"]
out = {"reference": {"texts": len(ref_keys), "images": ref_images[:2],
                     "first_lines": [[i["bbox"], i["text"]] for i in ref[:3] if i["kind"] == "text"]}}

candidates = [r.name for r in frappe.get_all("Print Format", filters={"doc_type": "Sales Order"},
                                             fields=["name"], order_by="modified desc")]
out["matched"] = {}
for name in candidates:
    try:
        pdf = frappe.get_print("Sales Order", DOC, print_format=name, as_pdf=True)
    except Exception as exc:
        out["matched"][name] = {"error": str(exc)[:120]}
        continue
    if isinstance(pdf, str):
        out["matched"][name] = {"error": "get_print returned html"}
        continue
    path = "/tmp/cand_%s.pdf" % re.sub(r"[^A-Za-z0-9_.-]", "_", name)
    with open(path, "wb") as fh:
        fh.write(pdf)
    items = layout(path)
    cand_keys = {key(i) for i in items if i["kind"] == "text"}
    hit = len(ref_keys & cand_keys)
    out["matched"][name] = {
        "pdf": path,
        "texts": len(cand_keys),
        "exact_hits": hit,
        "ratio": round(hit / max(len(ref_keys), 1), 3),
        "images": [i for i in items if i["kind"] == "image"][:1],
    }

best = sorted(((v.get("ratio", -1), k) for k, v in out["matched"].items() if "ratio" in v), reverse=True)[:3]
out["ranking"] = [[k, r] for r, k in best]
if best:
    best_name = best[0][1]
    best_pdf = out["matched"][best_name]["pdf"]
    out["best_layout_head"] = [[i["bbox"], i["kind"], i.get("text") or i.get("size")]
                               for i in layout(best_pdf)[:14]]
out["ref_head"] = [[i["bbox"], i["kind"], i.get("text") or i.get("size")] for i in ref[:14]]

print(json.dumps(out, ensure_ascii=True, indent=1, default=str))
