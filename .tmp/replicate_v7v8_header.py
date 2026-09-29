"""Replicate a saved A4 designer format's company-header layout from its raw HTML source
and measure the resulting geometry for comparison with the reference PDF sample."""
import os, json, base64
from pathlib import Path
import pymupdf

ROOT = Path(__file__).resolve().parent
# Saved format sources (JSON) previously deployed to production; copy them here first.
SRC_DIR = ROOT / "print_format"
# We will build a standalone HTML (shared CSS + format HTML) and render with PyMuPDF's
# built-in HTML→PDF via pdfkit? No — PyMuPDF can't render HTML. Instead: count on the
# reference approach — measure PDF geometry we already have (.tmp/ref_pdf_geom.json) and
# read the saved format's company-header HTML/CSS to infer layout rules. So this script
# is really: read saved format JSON, extract header tokens.

def read_pick(name):
    path = SRC_DIR / name / f"{name}.json"
    data = json.loads(path.read_text(encoding="utf-8"))
    print(f"== {name}")
    print("  module:", data.get("module"))
    print("  is_standard:", data.get("standard"))
    print("  no_letterhead:", data.get("no_letterhead"))
    html = data.get("html") or ""
    css = data.get("css") or ""
    print("  html len:", len(html), "css len:", len(css))
    # company-header snippet
    import re
    hdr = re.search(r'<div class="company-header[^>]*>.{0,260}', html)
    print("  header:", (hdr.group(0)[:260] if hdr else "NONE"))
    print("  logo img class:", "company-logo" in html, "solua-global-logo" in html)
    print("  has shared css call:", "get_solua_print_css()" in html)
    # col widths
    cols = re.findall(r'<col [^>]*>', html)
    print("  cols:", " ".join(cols)[:400])
    logo_css = re.findall(r'\.company-logo\s*\{[^}]*\}', css + html)
    print("  company-logo css:", logo_css)
    return data

for n in ["A4-Designer-Deploy-20260926-v7", "A4-Designer-Deploy-20260926-v8"]:
    if (SRC_DIR / n).is_dir():
        try:
            read_pick(n)
        except Exception as e:
            print("ERR", n, e)
    else:
        print("MISSING", n, "-> will fetch from server")
