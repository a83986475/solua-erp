import os, json, logging

os.chdir("/home/frappe/frappe-bench/sites")
import frappe
import frappe.utils.logger as _flog
_flog.create_handler = lambda *a, **k: [logging.StreamHandler()]
frappe.init(site="erp.solua.one", sites_path="/home/frappe/frappe-bench/sites")
frappe.connect()
frappe.set_user("Administrator")

from frappe.www.printview import get_context
from frappe.utils.pdf import inline_private_images

TARGETS = [
    ("Sales Order", "SAL-ORD-2026-00015", "客户订单确认单（颜色版）"),
    ("Delivery Note", "MAT-DN-2026-00006", "Guia de Remessa"),
    ("Pick List", "STO-PICK-2026-00002", "拣货单（简版）"),
]

out = {}
for dt, name, fmt in TARGETS:
    try:
        frappe.form_dict = frappe._dict(doctype=dt, name=name, print_format=fmt,
                                        no_letterhead="0", trigger_print="0",
                                        settings="{}", style=None, key=None,
                                        pdf_generator="wkhtmltopdf")
        ctx = get_context(frappe._dict())
        body = inline_private_images(ctx["body"])
        # the desk print preview shows the letterhead even though /printview omits it
        doc = frappe.get_doc(dt, name)
        lh = frappe.get_doc("Letter Head", doc.get("letter_head") or "Company Letterhead - Grey")
        lh_html = frappe.utils.jinja.render_template(lh.get("content") or "", {"doc": doc.as_dict()})
        lh_html = inline_private_images(lh_html)
        out[fmt] = {"body": body, "style": ctx["print_style"], "letterhead": lh_html,
                    "len_body": len(body), "has_letterhead": "letterhead-container" in lh_html}
    except Exception as exc:
        out[fmt] = {"error": str(exc)[:250]}

with open("/tmp/printview_ctx.json", "w", encoding="utf-8") as fh:
    json.dump(out, fh)
print(json.dumps({k: {kk: vv for kk, vv in v.items() if kk != "body" and kk != "style"}
                  for k, v in out.items()}, ensure_ascii=True, indent=1))
frappe.db.rollback()
