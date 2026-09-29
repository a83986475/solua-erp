import os, logging, json, re, base64

os.chdir("/home/frappe/frappe-bench/sites")
import frappe
import frappe.utils.logger as _flog
_flog.create_handler = lambda *a, **k: [logging.StreamHandler()]
frappe.init(site="erp.solua.one", sites_path="/home/frappe/frappe-bench/sites")
frappe.connect()
frappe.set_user("Administrator")

from solua_home.api import a4_designer as api

out = {}
fmt = frappe.get_doc("Print Format", "A4-Designer-Deploy-20260926-v8")
html_saved = fmt.html or ""
marker = re.search(r"<!--SOLUA_A4_DESIGNER:v1:([A-Za-z0-9_\-=]+)-->", html_saved)
config = json.loads(base64.urlsafe_b64decode(marker.group(1).encode()).decode())
out["config_loaded"] = bool(config)

# 当前代码会生成什么（不写库）
clean = api._validate_config(json.loads(json.dumps(config)))
html_new = api._template(clean)
out["new_template"] = {
    "len": len(html_new),
    "company_header": "company-header" in html_new,
    "hides_shared_logo": ".solua-global-logo{display:none" in html_new,
    "has_company_logo_img": 'class="company-logo"' in html_new,
    "has_payment": "Plano de pagamento" in html_new,
    "same_columns": re.findall(r"<th>([^<]+)</th>", html_new) == re.findall(r"<th>([^<]+)</th>", html_saved),
}
out["saved_template"] = {
    "len": len(html_saved),
    "company_header": "company-header" in html_saved,
    "hides_shared_logo": ".solua-global-logo{display:none" in html_saved,
    "has_company_logo_img": 'class="company-logo"' in html_saved,
}

doc = frappe.get_doc("Sales Order", "SAL-ORD-2026-00015")
out["company_print_info_keys"] = sorted((frappe.get_attr("solua_home.printing.wholesale.get_company_print_info")(doc) or {}).keys())
out["company_logo_value"] = (frappe.get_attr("solua_home.printing.wholesale.get_company_print_info")(doc) or {}).get("logo")

for tag, html in (("saved", html_saved), ("new", html_new)):
    rendered = frappe.render_template(html, {"doc": doc})
    out.setdefault("renders", {})[tag] = {
        "len": len(rendered),
        "no_jinja": "{%" not in rendered,
        "logo_imgs": re.findall(r'<img[^>]*>', rendered)[:2],
        "company_header": "company-header" in rendered,
    }
    with open(f"/tmp/a4_{tag}_render.html", "w", encoding="utf-8") as fh:
        fh.write(rendered)

print(json.dumps(out, ensure_ascii=True, indent=1, default=str))
