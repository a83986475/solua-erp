import os, json, logging

os.chdir("/home/frappe/frappe-bench/sites")
import frappe
import frappe.utils.logger as _flog
_flog.create_handler = lambda *a, **k: [logging.StreamHandler()]
frappe.init(site="erp.solua.one", sites_path="/home/frappe/frappe-bench/sites")
frappe.connect()
frappe.set_user("Administrator")

TARGET = "PRINT DESIGN 销售订单"
SOURCE = "Sales Order DIY"

PAYLOAD = ["print_designer_print_format", "print_designer_settings", "print_designer_header",
           "print_designer_body", "print_designer_footer", "print_designer_after_table",
           "print_designer_preview_img", "print_designer_template_app"]

target = frappe.get_doc("Print Format", TARGET)
source = frappe.get_doc("Print Format", SOURCE)

before = {f: (len(target.get(f)) if isinstance(target.get(f), str) else target.get(f)) for f in PAYLOAD}

# 空壳格式：print_designer=1 但 payload 全是 None，Print Designer 解析时 json.loads(None) 直接抛错
copied = []
for field in PAYLOAD:
    value = source.get(field)
    if value not in (None, ""):
        target.set(field, value)
        copied.append(field)
target.save(ignore_permissions=True)
frappe.db.commit()

after = {f: (len(target.get(f)) if isinstance(target.get(f), str) else target.get(f)) for f in PAYLOAD}

out = {"before": before, "copied": copied, "after": after}
try:
    html = frappe.get_print("Sales Order", "SAL-ORD-2026-00015", print_format=TARGET, as_pdf=False)
    out["render"] = {"ok": True, "len": len(html), "no_jinja": "{%" not in html,
                     "has_logo": "data:image" in html or "logo" in html.lower()}
    with open("/tmp/pd_format_render.html", "w", encoding="utf-8") as fh:
        fh.write(html)
except Exception as exc:
    out["render"] = {"ok": False, "error": str(exc)[:200]}

print(json.dumps(out, ensure_ascii=True, indent=1, default=str))
