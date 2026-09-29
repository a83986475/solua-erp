import os, logging, json, re

os.chdir("/home/frappe/frappe-bench/sites")
import frappe
import frappe.utils.logger as _flog
_flog.create_handler = lambda *a, **k: [logging.StreamHandler()]
frappe.init(site="erp.solua.one", sites_path="/home/frappe/frappe-bench/sites")
frappe.connect()
frappe.set_user("Administrator")

from frappe.utils.pdf import get_pdf, inline_private_images
from frappe.core.doctype.file.utils import find_file_by_url

out = {}
out["company_logo_field"] = frappe.db.get_value("Company", "Solua Home, Lda", "company_logo")
out["file_record"] = frappe.db.get_value("File", {"file_name": "SOLUA LOGO.png"},
                                         ["name", "file_url", "is_private", "file_size"], as_dict=True)
out["find_raw_space"] = bool(find_file_by_url("/private/files/SOLUA LOGO.png"))
out["find_quoted"] = bool(find_file_by_url("/private/files/SOLUA%20LOGO.png"))

html_tag = '<img src="http://erp.solua.one/private/files/SOLUA LOGO.png">'
out["inline_http_space"] = inline_private_images(html_tag)[:70]
out["inline_https_quoted"] = inline_private_images(
    '<img src="https://erp.solua.one/private/files/SOLUA%20LOGO.png">')[:70]

# 打印格式的实际渲染：logo 标签长什么样
fmt = frappe.get_doc("Print Format", "\u62e3\u8d27\u5355\uff08\u7b80\u7248\uff09")
pick = frappe.get_all("Pick List", filters={"docstatus": 1}, fields=["name"], order_by="creation desc", limit=1)
html = frappe.get_print("Pick List", pick[0].name, print_format=fmt.name, as_pdf=False)
out["logo_tag"] = re.findall(r"<img[^>]*solua-global-logo[^>]*>", html)[:1]

# PDF：带 logo vs 去掉 logo 的体积对比，判断图片是否真的进了 PDF
plain = get_pdf(html)
without = get_pdf(re.sub(r"<img[^>]*solua-global-logo[^>]*>", "", html))
out["pdf_bytes_with_logo"] = len(plain)
out["pdf_bytes_without_logo"] = len(without)
out["logo_embedded"] = len(plain) - len(without) > 20000

print(json.dumps(out, ensure_ascii=True, indent=1, default=str))
