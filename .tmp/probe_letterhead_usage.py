import os, json, logging

os.chdir("/home/frappe/frappe-bench/sites")
import frappe
import frappe.utils.logger as _flog
_flog.create_handler = lambda *a, **k: [logging.StreamHandler()]
frappe.init(site="erp.solua.one", sites_path="/home/frappe/frappe-bench/sites")
frappe.connect()
frappe.set_user("Administrator")

out = {}
for dt in ("Sales Order", "Sales Invoice", "Delivery Note", "Pick List"):
    total = frappe.db.count(dt)
    meta = frappe.get_meta(dt)
    if not meta.has_field("letter_head"):
        out[dt] = {"total": total, "has_letter_head_field": False}
        continue
    rows = frappe.db.sql(
        f"select letter_head, count(*) c from `tab{dt}` group by letter_head", as_dict=True)
    out[dt] = {"total": total, "has_letter_head_field": True, "by_letter_head": rows}

ps = frappe.get_doc("Print Settings")
out["print_settings"] = {k: ps.get(k) for k in
                         ("repeat_header_footer", "pdf_page_size", "with_letterhead") if ps.get(k) is not None}
out["get_default_letter_head"] = frappe.db.get_default("letter_head")

# where else is a default letter_head configured?
out["defaults"] = frappe.get_all("DefaultValue", filters={"defkey": ["like", "%letter%"]},
                                 fields=["name", "defkey", "defvalue", "parent"])

print(json.dumps(out, ensure_ascii=True, indent=1, default=str))
frappe.db.rollback()
