import base64, json, io

import pypdfium2 as pdfium
import pdfplumber

pt2mm = 25.4 / 72.0


def page_png(path, page_index=0, scale=2.2):
    pdf = pdfium.PdfDocument(path)
    page = pdf[page_index]
    bitmap = page.render(scale=scale)
    pil = bitmap.to_pil()
    buf = io.BytesIO()
    pil.save(buf, format="PNG")
    return base64.b64encode(buf.getvalue()).decode()


def geom(path):
    with pdfplumber.open(path) as pdf:
        page = pdf.pages[0]
        W = page.width
        imgs = [{"x0": round(i["x0"] * pt2mm, 1), "top": round(i["top"] * pt2mm, 1),
                 "w": round((i["x1"] - i["x0"]) * pt2mm, 1), "h": round((i["bottom"] - i["top"]) * pt2mm, 1)}
                for i in page.images]
        rows = {}
        for w in page.extract_words():
            y = round(w["top"] * pt2mm, 1)
            if y > 55:
                continue
            rows.setdefault(y, []).append(w)
        head = {}
        for y, ws in sorted(rows.items()):
            text = " ".join(w["text"] for w in ws)
            xs = [w["x0"] * pt2mm for w in ws] + [w["x1"] * pt2mm for w in ws]
            head[y] = {"t": text[:70], "x0": round(min(xs), 1), "x1": round(max(xs), 1),
                       "mid": round((min(xs) + max(xs)) / 2, 1)}
        return {"page_mm": [round(W * pt2mm, 1), round(page.height * pt2mm, 1)],
                "center_mm": round(W / 2 * pt2mm, 1), "images": imgs, "header": head}


out = {
    "sample": {"geom": geom("/tmp/sales_doc_sample.pdf"), "png": page_png("/tmp/sales_doc_sample.pdf")},
    "new": {"geom": geom("/tmp/so_new_header.pdf"), "png": page_png("/tmp/so_new_header.pdf")},
}
with open("/tmp/render_compare.json", "w", encoding="utf-8") as fh:
    json.dump(out, fh)
print(json.dumps({k: v["geom"] for k, v in out.items()}, ensure_ascii=True, indent=1))
print("PNG bytes:", {k: len(v["png"]) for k, v in out.items()})
