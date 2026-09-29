import os, json, logging

os.chdir("/home/frappe/frappe-bench/sites")
import frappe
import frappe.utils.logger as _flog
_flog.create_handler = lambda *a, **k: [logging.StreamHandler()]
frappe.init(site="erp.solua.one", sites_path="/home/frappe/frappe-bench/sites")
frappe.connect()
frappe.set_user("Administrator")

FIELDS = ["print_designer", "print_designer_print_format", "print_designer_settings",
          "print_designer_header", "print_designer_body", "print_designer_footer",
          "print_designer_template_app", "print_designer_after_table", "print_designer_preview_img"]

out = {}
for name in ["PRINT DESIGN 销售订单", "Sales Order PD v2", "Sales Order DIY"]:
    pf = frappe.get_doc("Print Format", name)
    rec = {}
    for f in FIELDS:
        v = pf.get(f)
        if isinstance(v, str):
            rec[f] = {"len": len(v), "head": v[:120]}
        else:
            rec[f] = {"type": type(v).__name__, "value": str(v)[:80]}
    out[name] = rec

out["_apps"] = frappe.get_installed_apps() if hasattr(frappe, "get_installed_apps") else []
print(json.dumps(out, ensure_ascii=True, indent=1, default=str))
frappe.db.rollback()
