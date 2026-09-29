import json
import pdfplumber

p = "/tmp/sales_doc_sample.pdf"
pt2mm = 25.4 / 72.0
out = {}
with pdfplumber.open(p) as pdf:
    page = pdf.pages[0]
    W, H = page.width, page.height
    out["page_mm"] = [round(W * pt2mm, 1), round(H * pt2mm, 1)]
    out["images"] = []
    for im in page.images:
        out["images"].append({
            "x0": round(im["x0"] * pt2mm, 1), "top": round(im["top"] * pt2mm, 1),
            "w": round((im["x1"] - im["x0"]) * pt2mm, 1), "h": round((im["bottom"] - im["top"]) * pt2mm, 1),
        })
    words = page.extract_words(use_text_flow=False, keep_blank_chars=False)
    out["header_lines"] = []
    seen = set()
    for w in words:
        y = round(w["top"] * pt2mm, 1)
        if y > 55:
            continue
        key = (round(y), w["text"])
        if key in seen:
            continue
        seen.add(key)
        out["header_lines"].append({
            "t": w["text"], "x0": round(w["x0"] * pt2mm, 1), "x1": round(w["x1"] * pt2mm, 1),
            "y": y, "size": round(w.get("height", 0) * pt2mm, 1),
        })
    # group into rows for readable output
    rows = {}
    for w in out["header_lines"]:
        rows.setdefault(w["y"], []).append(w)
    out["rows"] = {str(y): " | ".join(f"{x['t']}({x['x0']}-{x['x1']})" for x in sorted(v, key=lambda z: z["x0"]))
                   for y, v in sorted(rows.items())}
    out["page_center_mm"] = round(W / 2 * pt2mm, 1)
    out["page_width_mm"] = round(W * pt2mm, 1)
print(json.dumps(out, ensure_ascii=False, indent=1))
