import os, re, json, logging

os.chdir("/home/frappe/frappe-bench/sites")
import frappe
import frappe.utils.logger as _flog
_flog.create_handler = lambda *a, **k: [logging.StreamHandler()]
frappe.init(site="erp.solua.one", sites_path="/home/frappe/frappe-bench/sites")
frappe.connect()
frappe.set_user("Administrator")

import solua_home.printing.wholesale as wm

SO = "SAL-ORD-2026-00015"
out = {"signature_ok": None, "formats": {}}
try:
    out["signature_ok"] = wm.format_print_money(430.49, currency="MZN", precision=0)
    out["precision2"] = wm.format_print_money(430.567, currency="MZN", precision=2)
except Exception as exc:
    out["signature_ok"] = "ERR " + str(exc)[:120]

for name in ["客户订单确认单（A4新版）", "客户订单确认单（颜色版）-紧凑版",
             "客户订单确认单（颜色版）-紧凑无边框版", "客户订单确认单（颜色版）"]:
    try:
        h = frappe.get_print("Sales Order", SO, print_format=name, as_pdf=False)
        out["formats"][name] = {
            "ok": True, "undefined": h.count("no such element"), "jinja_left": h.count("{%"),
            "global_logo": h.count('class="solua-global-logo"'),
            "company_header": h.count("company-header"),
            "h2": re.findall(r"<h2[^>]*>(.*?)</h2>", h, re.S)[:1],
            "at_page": re.findall(r"@page\s*\{[^}]*\}", h)[:1],
        }
    except Exception as exc:
        out["formats"][name] = {"ok": False, "error": str(exc)[:140]}

print(json.dumps(out, ensure_ascii=True, indent=1, default=str))
frappe.db.rollback()
