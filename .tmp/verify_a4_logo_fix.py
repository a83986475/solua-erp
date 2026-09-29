import os, logging, json, re, base64

os.chdir("/home/frappe/frappe-bench/sites")
import frappe
import frappe.utils.logger as _flog
_flog.create_handler = lambda *a, **k: [logging.StreamHandler()]
frappe.init(site="erp.solua.one", sites_path="/home/frappe/frappe-bench/sites")
frappe.connect()
frappe.set_user("Administrator")

from solua_home.api import a4_designer as api
from solua_home.printing.a4_designer import get_a4_print_data
from solua_home.printing.wholesale import get_wholesale_print_data
from frappe.utils.pdf import get_pdf

out = {}
doc = frappe.get_doc("Sales Order", "SAL-ORD-2026-00015")
draft_names = frappe.get_all("Sales Order", filters={"docstatus": 0}, pluck="name", limit=1)

out["provider"] = {
    "submitted_snapshot_company_keys": sorted((get_wholesale_print_data(doc).get("company") or {}).keys()),
    "submitted_logo": (get_a4_print_data(doc).get("company") or {}).get("logo"),
}
if draft_names:
    out["provider"]["draft_logo"] = (get_a4_print_data(
        frappe.get_doc("Sales Order", draft_names[0])).get("company") or {}).get("logo")
pick = frappe.get_all("Pick List", filters={"docstatus": 1}, pluck="name", limit=1)
if pick:
    out["provider"]["pick_list_logo"] = (get_a4_print_data(frappe.get_doc("Pick List", pick[0])).get("company") or {}).get("logo")

# 用当前模板重放已保存的 v8 配置（不写库），验证渲染与 PDF
fmt = frappe.get_doc("Print Format", "A4-Designer-Deploy-20260926-v8")
marker = re.search(r"<!--SOLUA_A4_DESIGNER:v1:([A-Za-z0-9_\-=]+)-->", fmt.html or "")
config = json.loads(base64.urlsafe_b64decode(marker.group(1).encode()).decode())
rendered = frappe.render_template(api._template(api._validate_config(config)), {"doc": doc})
logo_img = re.findall(r'<img[^>]*class="company-logo"[^>]*>', rendered)
out["current_template_render"] = {
    "len": len(rendered),
    "company_logo_img": logo_img[:1],
    "hides_shared_logo": ".solua-global-logo{display:none" in rendered,
    "no_jinja": "{%" not in rendered,
    "has_totals": "Total Qty / \u603b\u6570\u91cf" in rendered,
}
page = ('<!doctype html><html><head><meta charset="utf-8"></head><body><div class="print-format">'
        + rendered + "</div></body></html>")
with_logo = get_pdf(page)
without_logo = get_pdf(re.sub(r'<img[^>]*class="company-logo"[^>]*>', "", page))
out["pdf"] = {"with_logo": len(with_logo), "without_logo": len(without_logo),
              "logo_embedded": len(with_logo) - len(without_logo) > 20000}

# 回归：生产上现有的自定义格式都还能渲染
formats = {
    "A4-Designer-Deploy-20260926-v8": ("Sales Order", doc.name),
    "A4-Designer-Deploy-20260926-v7": ("Sales Order", doc.name),
    "\u5ba2\u6237\u8ba2\u5355\u786e\u8ba4\u5355\uff08\u989c\u8272\u7248\uff09": ("Sales Order", doc.name),
    "Guia de Remessa": ("Delivery Note", None),
    "\u6279\u53d1\u9500\u552e\u5355\uff08\u989c\u8272\u7248\uff09\u65b0\u7248": ("Sales Invoice", None),
    "\u62e3\u8d27\u5355\uff08\u7b80\u7248\uff09": ("Pick List", None),
    "\u62e3\u8d27\u5355\uff08\u989c\u8272\u7248\uff09": ("Pick List", None),
}
out["regressions"] = {}
for name, (doctype, docname) in formats.items():
    target = docname or (frappe.get_all(doctype, filters={"docstatus": 1}, pluck="name",
                                         order_by="creation desc", limit=1) or [None])[0]
    try:
        html = frappe.get_print(doctype, target, print_format=name, as_pdf=False)
        out["regressions"][name] = {"ok": True, "len": len(html), "no_jinja": "{%" not in html}
    except Exception as exc:
        out["regressions"][name] = {"ok": False, "error": str(exc)[:160]}

print(json.dumps(out, ensure_ascii=True, indent=1, default=str))
