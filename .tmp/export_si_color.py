"""把只有数据库里的「批发销售单（颜色版）」导出成仓库里的磁盘源文件。

log 处理器改成 StreamHandler：ubuntu 用户没有 bench logs 目录写权限。
导出字段与 key 顺序对齐 print_format/so_new_header/so_new_header.json，方便以后从文件重导。
"""
import json
import logging
import os

os.chdir("/home/frappe/frappe-bench/sites")
import frappe  # noqa: E402
import frappe.utils.logger as _flog  # noqa: E402

_flog.create_handler = lambda *a, **k: [logging.StreamHandler()]
frappe.init(site="erp.solua.one", sites_path="/home/frappe/frappe-bench/sites")
frappe.connect()
frappe.set_user("Administrator")

NAME = "批发销售单（颜色版）"
KEYS = ["custom_format", "disabled", "doc_type", "docstatus", "doctype", "html", "css",
        "idx", "line_breaks", "module", "name", "print_format_builder", "print_format_type",
        "raw_commands", "raw_printing", "show_section_headings", "standard"]

doc = frappe.get_doc("Print Format", NAME)
out = {key: doc.get(key) for key in KEYS}
os.makedirs("/tmp/export", exist_ok=True)
# 版式对齐仓库里既有格式文件：1 空格缩进、CRLF 行尾、结尾不加换行
path = "/tmp/export/sales_invoice_wholesale_color.json"
text = json.dumps(out, ensure_ascii=False, indent=" ").replace("\n", "\r\n")
with open(path, "w", encoding="utf-8", newline="") as fh:
    fh.write(text)
print("wrote", path, os.path.getsize(path))
print("keys", list(out))
print("css", repr(out["css"]))
print("html_has_page", "@page" in out["html"], "css_has_page", "@page" in out["css"])
print("html_head", (out["html"] or "")[:160])
import sys
sys.stdout.flush()
