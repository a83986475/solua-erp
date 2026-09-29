import os, re, json, logging

os.chdir("/home/frappe/frappe-bench/sites")
import frappe
import frappe.utils.logger as _flog
_flog.create_handler = lambda *a, **k: [logging.StreamHandler()]
frappe.init(site="erp.solua.one", sites_path="/home/frappe/frappe-bench/sites")
frappe.connect()
frappe.set_user("Administrator")

from frappe.utils.pdf import inline_private_images, prepare_options

NAME = "客户订单确认单（公司抬头-新）"
h = frappe.get_print("Sales Order", "SAL-ORD-2026-00015", print_format=NAME, as_pdf=False)
h2, opts = prepare_options(h, None)
h3 = inline_private_images(h2)

out = {}
out["options"] = {k: str(v)[:60] for k, v in (opts or {}).items()}
out["imgs"] = [t[:200] for t in re.findall(r"<img[^>]*>", h3)[:5]]
out["logo_rules"] = [m.strip()[-150:] for m in re.findall(r"[^{}]*solua-global-logo[^{}]*\{[^}]*\}", h3)[:6]]
out["atpage"] = re.findall(r"@page\s*\{[^}]*\}", h3)[:4]
out["printformat_rules"] = [m for m in re.findall(r"\.print-format\s*\{[^}]*\}", h3)][:4]
# where does the logo img sit relative to <div class="print-format">
i = h3.find('class="solua-global-logo"')
out["context_before_logo"] = h3[max(0, i - 400):i + 200].replace("\n", "\\n")[-560:]
print(json.dumps(out, ensure_ascii=True, indent=1))
