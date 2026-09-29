import json, logging

logging.disable(logging.WARNING)
logging.getLogger("pdfminer").setLevel(logging.ERROR)

from pdfminer.high_level import extract_pages
from pdfminer.layout import LAParams, LTImage, LTLine, LTRect, LTTextContainer

PT2MM = 25.4 / 72.0
path = "/tmp/sales_doc_sample.pdf"
items = []
for page in extract_pages(path, laparams=LAParams(), maxpages=1):
    page_height = round(page.height, 1)

    def walk(obj):
        if isinstance(obj, LTImage):
            items.append(("image", obj.bbox))
            return
        if isinstance(obj, (LTRect, LTLine)):
            items.append((type(obj).__name__, obj.bbox))
            return
        if isinstance(obj, LTTextContainer):
            for line in obj:
                text = " ".join(line.get_text().split())
                if text:
                    items.append(("text", line.bbox, text))
            return
        for child in getattr(obj, "_objs", []):
            walk(child)

    walk(page)

header = [i for i in items if i[1][1] > 555]
header.sort(key=lambda i: (-i[1][3], i[1][0]))
out = {"page_height_pt": page_height, "header_items": []}
for entry in header:
    kind, bbox = entry[0], entry[1]
    x0, y0, x1, y1 = bbox
    rec = {
        "kind": kind,
        "x_mm": [round(x0 * PT2MM, 1), round(x1 * PT2MM, 1)],
        "from_top_mm": [round((page_height - y1) * PT2MM, 1), round((page_height - y0) * PT2MM, 1)],
        "w_mm": round((x1 - x0) * PT2MM, 1), "h_mm": round((y1 - y0) * PT2MM, 1),
    }
    if kind == "text":
        rec["text"] = entry[2]
    out["header_items"].append(rec)

print(json.dumps(out, ensure_ascii=True, indent=1))
