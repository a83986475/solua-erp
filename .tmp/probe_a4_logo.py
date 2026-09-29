import os, logging, json, re

os.chdir("/home/frappe/frappe-bench/sites")
import frappe
import frappe.utils.logger as _flog
_flog.create_handler = lambda *a, **k: [logging.StreamHandler()]
frappe.init(site="erp.solua.one", sites_path="/home/frappe/frappe-bench/sites")
frappe.connect()
frappe.set_user("Administrator")

get_wholesale = frappe.get_attr("solua_home.printing.wholesale.get_wholesale_print_data")
get_company = frappe.get_attr("solua_home.printing.wholesale.get_company_print_info")
get_a4 = frappe.get_attr("solua_home.printing.a4_designer.get_a4_print_data")

out = {"docs": {}}
targets = ["SAL-ORD-2026-00015"]
draft = frappe.get_all("Sales Order", filters={"docstatus": 0}, pluck="name", limit=1)
targets += draft
for name in targets:
    doc = frappe.get_doc("Sales Order", name)
    p = get_wholesale(doc)
    a4 = get_a4(doc)
    out["docs"][name] = {
        "docstatus": doc.docstatus,
        "has_snapshot": bool(doc.get("custom_wholesale_snapshot")),
        "p_company_keys": sorted((p.get("company") or {}).keys()),
        "p_company_logo": (p.get("company") or {}).get("logo"),
        "a4_company_logo": (a4.get("company") or {}).get("logo"),
        "get_company_logo": get_company(doc).get("logo"),
    }

# 设计器 Pick List 路径（不走快照）
pick = frappe.get_all("Pick List", filters={"docstatus": 1}, pluck="name", limit=1)
if pick:
    pdoc = frappe.get_doc("Pick List", pick[0])
    out["pick_list"] = {
        "name": pick[0],
        "a4_company_logo": (get_a4(pdoc).get("company") or {}).get("logo"),
    }

# 已保存的 v8 渲染里到底有没有 img（用快照路径重放）
rendered = frappe.render_template(frappe.db.get_value("Print Format", "A4-Designer-Deploy-20260926-v8", "html"),
                                  {"doc": frappe.get_doc("Sales Order", "SAL-ORD-2026-00015")})
out["v8_render"] = {
    "shared_logo": 'class="solua-global-logo"' in rendered,
    "company_logo": 'class="company-logo"' in rendered,
    "hides_shared": ".solua-global-logo{display:none" in rendered,
}

print(json.dumps(out, ensure_ascii=True, indent=1, default=str))
