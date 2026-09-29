import json, logging, sys

logging.disable(logging.WARNING)
logging.getLogger("pdfminer").setLevel(logging.ERROR)

from pdfminer.high_level import extract_pages
from pdfminer.layout import LAParams, LTImage, LTTextContainer

PT2MM = 25.4 / 72.0


def geom(path):
    page = next(iter(extract_pages(path, laparams=LAParams(), maxpages=1)))
    height = page.height
    items = []

    def walk(obj):
        if isinstance(obj, LTImage):
            items.append(("image", obj.bbox, f"{obj.width:.1f}x{obj.height:.1f}pt"))
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
    rows = []
    for kind, bbox, text in items:
        x0, y0, x1, y1 = bbox
        rows.append({
            "kind": kind, "text": text[:60],
            "top_mm": round((height - y1) * PT2MM, 1),
            "x_mm": round(x0 * PT2MM, 1),
            "w_mm": round((x1 - x0) * PT2MM, 1),
            "h_mm": round((y1 - y0) * PT2MM, 1),
        })
    return rows


def summary(path):
    rows = geom(path)
    top = [r for r in rows if r["top_mm"] < 90]
    logo = [r for r in top if r["kind"] == "image"]
    title = [r for r in top if "Confirma" in r["text"] or "订单确认单" in r["text"]]
    parties = [r for r in top if r["text"].startswith(("Solua Home", "Cliente", "NUIT"))]
    columns = [r for r in top if r["text"] in ("Solua Home, Lda", "Cliente", "NUIT")]
    return {
        "page_pt": None,
        "logo": [(r["top_mm"], r["x_mm"], r["w_mm"], r["h_mm"]) for r in logo],
        "title": [(r["top_mm"], r["x_mm"], r["w_mm"], r["h_mm"], r["text"]) for r in title],
        "left_col_x": sorted({r["x_mm"] for r in top if r["x_mm"] < 60 and r["kind"] == "text"})[:4],
        "right_col_x": sorted({r["x_mm"] for r in top if 60 < r["x_mm"] < 160 and r["kind"] == "text"})[:4],
        "lines": [(r["top_mm"], r["x_mm"], r["text"]) for r in top][:16],
    }


out = {}
for path in sys.argv[1:]:
    try:
        out[path] = summary(path)
    except Exception as exc:
        out[path] = {"error": str(exc)[:120]}
print(json.dumps(out, ensure_ascii=True, indent=1))
