import os, json, logging, re

os.chdir("/home/frappe/frappe-bench/sites")
import frappe
import frappe.utils.logger as _flog
_flog.create_handler = lambda *a, **k: [logging.StreamHandler()]
frappe.init(site="erp.solua.one", sites_path="/home/frappe/frappe-bench/sites")
frappe.connect()
frappe.set_user("Administrator")

from frappe.modules.import_file import import_file_by_path

BASE = "/home/frappe/frappe-bench/apps/solua_home/solua_home/print_format"
out = {}

# 1) 磁盘格式：重新导入（已补 @page）
import_file_by_path(f"{BASE}/sales_invoice_wholesale_color_v2/sales_invoice_wholesale_color_v2.json",
                    force=True, ignore_version=True)

# 2) DB 手建格式：没有任何 css，也没有 @page → 打印时页边距/缩放与样张不一致
DB_ONLY = "批发销售单（颜色版）"
pf = frappe.get_doc("Print Format", DB_ONLY)
c = pf.css or ""
if not re.search(r"@page", c):
    pf.css = "@page{size:A4;margin:12mm}" + c
    pf.save(ignore_permissions=True)
    out["db_only_patched"] = True
else:
    out["db_only_patched"] = False

frappe.db.commit()

for name in ["批发销售单（颜色版）", "批发销售单（颜色版）新版"]:
    doc = frappe.get_doc("Print Format", name)
    h = doc.html or ""
    out[name] = {
        "css_len": len(doc.css or ""), "at_page": bool(re.search(r"@page", doc.css or "")),
        "uses_shared_css": "get_solua_print_css" in h,
        "undefined": "no such element",
    }

# render check with a synthesized in-memory Sales Invoice if any exist
si = frappe.get_all("Sales Invoice", fields=["name"], limit=1)
out["sales_invoices"] = [s.name for s in si]
if si:
    for name in ["批发销售单（颜色版）", "批发销售单（颜色版）新版"]:
        try:
            hh = frappe.get_print("Sales Invoice", si[0].name, print_format=name, as_pdf=False)
            out[name]["render"] = {"ok": True, "undefined": hh.count("no such element"),
                                   "no_jinja": "{%" not in hh, "logo": 'class="solua-global-logo"' in hh,
                                   "band": '<div class="solua-brand">' in hh}
        except Exception as exc:
            out[name]["render"] = {"ok": False, "error": str(exc)[:160]}
else:
    out["note"] = "生产上 0 张 Sales Invoice，只能做静态检查"

print(json.dumps(out, ensure_ascii=True, indent=1, default=str))
frappe.db.rollback()
