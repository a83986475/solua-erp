"""Replicate saved A4 designer format HTML for SAL-ORD-2026-00015 and compare with
reference PDF geometry. The saved format HTML is Jinja + shared CSS, so we cannot
render it locally without a Jinja env. Instead: from the reference PDF we already know
the company-header geometry (logo 15.4x12.3mm at 11.9,11.9; title centered at 104.9mm;
parties table at 14.0mm left, 107.0mm right, 2mm padding; separators at 72.5 and 84.2mm).

We now know what the saved v8 HTML *says* (no company-header, no logo, shared CSS call).
Missing: company-header + logo. We'll detect this programmatically and report the delta.
"""
import base64, json, re
from pathlib import Path
import pymupdf

# Use absolute paths - run from project root or adjust.
_cwd = Path.cwd()
if (_cwd.name == ".tmp") or (_cwd / ".tmp").is_dir():
    base = _cwd / ".tmp"
else:
    base = Path(__file__).resolve().parent / ".tmp"

enc = (base / "v8_pf_dump.html").read_text(encoding="utf-8")
html = re.sub(r"<!--SOLUA_A4_DESIGNER:.*-->", "", enc)
print("v8 html len:", len(html))
print("has company-header:", "company-header" in html)
print("has company-logo img:", ".company-logo" in html)
print("has shared css:", "get_solua_print_css()" in html)

# What the user's reference PDF (Chrome print of A4-Designer-Deploy-20260926-v8 at
# the time it was created) showed vs what the v8 HTML currently says:
#   ref PDF: company-header + logo (15.4x12.3mm at 11.9,11.9) + title centered
#   v8 HTML now: h2 title only, no company-header, no logo, parties table present
# So the v8 FORMAT SOURCE LOGIC (api/a4_designer.py's _template / render_v8_html)
# was updated since v8 was saved - the saved format is from an EARLIER version of
# api/a4_designer.py that DID include company-header + logo.
#
# Equivalent: re-derive the layout: the saved v8 doesn't have company-header. So
# comparing saved format to reference is moot - the reference was produced by an
# earlier revision of api/a4_designer.py (the one that was in effect when v8 was saved
# at 2026-09-26 12:15).
#
# So the task reduces to: make the CURRENT api/a4_designer.py's company-header + logo
# render like the reference (logo 15.4x12.3mm, title centered). We know:
#   header: <div class="company-header"><img class="company-logo" ...><h2>title</h2></div>
#   .company-header{position:relative} .company-logo{position:absolute;left:0;top:0}
#   logo must be sized to ~15.4mm wide (or 12mm tall, aspect 949:768 → 12mm/768*949=14.83mm wide)
#   title h2 centered, font 18pt, color #99732c, line-height 1.15
#   parties table as currently
#   If the user wants a more elaborate header (striped rows etc.), we'd see that in the
#   reference. The reference PDF header is SIMPLE: logo top-left, title centered, parties
#   two-column below. That IS the v7/v8-style header (pre-commit that removed it).
#   Confirmed: reference = legacy A4 design (v7/v8 era, before cfcd96ad14) behavior.
#
# So: restore the company-header + logo to api/a4_designer.py matching that era's layout,
# with the logo sizing that yields 15.4mm wide (or naturally ~14.8mm to match reference
# exactly). We'll use width:15mm as a nice round number (≈ reference 15.4mm).
print("\nReference geometry from PDF (mm):")
g = json.loads((base / "ref_pdf_geom.json").read_text(encoding="utf-8"))
for r in g:
    if r["y0"] < 34:
        print("  ", r)
print("\nParties separator rects (y<95):")
rs = json.loads((base / "ref_pdf_rects.json").read_text(encoding="utf-8"))
for r in rs:
    if r[1] < 95:
        print("  ", r)
