import os, re, json, logging

os.chdir("/home/frappe/frappe-bench/sites")
import frappe
import frappe.utils.logger as _flog
_flog.create_handler = lambda *a, **k: [logging.StreamHandler()]
frappe.init(site="erp.solua.one", sites_path="/home/frappe/frappe-bench/sites")
frappe.connect()
frappe.set_user("Administrator")

from frappe.utils.pdf import inline_private_images

NAME = "客户订单确认单（公司抬头-新）"
html = frappe.get_print("Sales Order", "SAL-ORD-2026-00015", print_format=NAME, as_pdf=False)
html = inline_private_images(html)

# all style blocks (shared print css + format css live inside the document)
styles = re.findall(r"<style[^>]*>(.*?)</style>", html, re.S)
# the print-format container markup
start = html.find('<div class="print-format">')
end = html.rfind("</div>", 0, html.find('<div class="action-banner'))
body = html[start:end] if start != -1 else ""

out = {"styles": styles, "body": body, "total_styles": len(styles)}
with open("/tmp/format_sheet.json", "w", encoding="utf-8") as fh:
    json.dump(out, fh)
print(json.dumps({"styles": len(styles), "body_len": len(body),
                  "has_logo": "data:image/png" in body,
                  "has_title": "订单确认单" in body}))
