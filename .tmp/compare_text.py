import glob, json, logging
from collections import Counter

logging.disable(logging.WARNING)
logging.getLogger("pdfminer").setLevel(logging.ERROR)

from pdfminer.high_level import extract_pages
from pdfminer.layout import LAParams, LTTextContainer


def lines(path, maxpages=1):
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


ref = lines("/tmp/sales_doc_sample.pdf")
rows = []
for path in sorted(glob.glob("/tmp/cand_*.pdf")):
    cand = lines(path)
    common = sum((Counter(ref) & Counter(cand)).values())
    rows.append({
        "pdf": path,
        "lines": len(cand),
        "common": common,
        "ratio": round(common / max(len(ref), 1), 3),
        "only_ref": [x for x in ref if x not in cand][:6],
        "only_cand": [x for x in cand if x not in ref][:6],
    })
rows.sort(key=lambda r: (-r["ratio"], -r["common"]))
print(json.dumps({"ref_lines": len(ref), "candidates": rows}, ensure_ascii=True, indent=1))
