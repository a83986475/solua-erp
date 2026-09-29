import logging
import sys

logging.disable(logging.WARNING)
logging.getLogger("pdfminer").setLevel(logging.ERROR)

from pdfminer.high_level import extract_pages
from pdfminer.layout import LAParams, LTImage, LTTextContainer
from pdfminer.pdfdocument import PDFDocument
from pdfminer.pdfpage import PDFPage
from pdfminer.pdfparser import PDFParser

path = "/tmp/sales_doc_sample.pdf"
with open(path, "rb") as fh:
    doc = PDFDocument(PDFParser(fh))
    pages = list(PDFPage.create_pages(doc))
print("pages:", len(pages), "mediabox:", [round(float(v), 1) for v in pages[0].mediabox])

for index, layout in enumerate(extract_pages(path, laparams=LAParams(), maxpages=2)):
    items = []

    def walk(obj):
        if isinstance(obj, LTImage):
            items.append(("image", obj.bbox, f"IMAGE {round(obj.width,1)}x{round(obj.height,1)}pt"))
            return
        if isinstance(obj, LTTextContainer):
            for line in obj:
                text = " ".join(line.get_text().split())
                if text:
                    items.append(("text", line.bbox, text))
            return
        for child in getattr(obj, "_objs", []):
            walk(child)

    walk(layout)
    items.sort(key=lambda row: (-row[1][3], row[1][0]))
    print(f"\n===== PAGE {index + 1}  ({len(items)} items)")
    for kind, bbox, text in items:
        x0, y0, x1, y1 = (round(v, 1) for v in bbox)
        print(f"{kind:5s} y={y1:6.1f} x={x0:6.1f}-{x1:6.1f} | {text[:110]}")
