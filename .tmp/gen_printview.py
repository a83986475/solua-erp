import os, json, logging

os.chdir("/home/frappe/frappe-bench/sites")
import frappe
import frappe.utils.logger as _flog
_flog.create_handler = lambda *a, **k: [logging.StreamHandler()]
frappe.init(site="erp.solua.one", sites_path="/home/frappe/frappe-bench/sites")
frappe.connect()
frappe.set_user("Administrator")

from frappe.www.printview import get_html_and_style

TARGETS = [
    ("Sales Order", "SAL-ORD-2026-00015", "客户订单确认单（颜色版）"),
    ("Delivery Note", "MAT-DN-2026-00006", "Guia de Remessa"),
    ("Pick List", "STO-PICK-2026-00002", "拣货单（简版）"),
]

out = {}
for dt, name, fmt in TARGETS:
    try:
        doc = frappe.get_doc(dt, name)
        res = get_html_and_style(doc=doc.as_json(), print_format=fmt, no_letterhead=0)
        (html, style) = res if isinstance(res, tuple) else (res.get("html"), res.get("style"))
        out[fmt] = {"html": html, "style": style, "len_html": len(html or ""), "len_style": len(style or ""),
                    "has_letterhead": "letterhead-container" in (html or "")}
    except Exception as exc:
        out[fmt] = {"error": str(exc)[:200]}

with open("/tmp/printview_real.json", "w", encoding="utf-8") as fh:
    json.dump(out, fh)
print(json.dumps({k: {kk: vv for kk, vv in v.items() if kk in ("len_html", "len_style", "has_letterhead", "error")}
                  for k, v in out.items()}, ensure_ascii=True, indent=1))
frappe.db.rollback()
