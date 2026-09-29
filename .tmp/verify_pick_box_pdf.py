"""生产回读：拣货单（简版/颜色版）真实单据渲染 HTML + PDF，确认折箱显示与 PDF 管线都正常。

log 处理器改成 StreamHandler：ubuntu 用户没有 bench logs 目录写权限。
"""
import logging
import os

os.chdir("/home/frappe/frappe-bench/sites")
import frappe  # noqa: E402
import frappe.utils.logger as _flog  # noqa: E402

_flog.create_handler = lambda *a, **k: [logging.StreamHandler()]
frappe.init(site="erp.solua.one", sites_path="/home/frappe/frappe-bench/sites")
frappe.connect()
frappe.set_user("Administrator")

from frappe.utils.pdf import get_pdf  # noqa: E402

for fmt in ("拣货单（简版）", "拣货单（颜色版）"):
    html = frappe.get_print("Pick List", "STO-PICK-2026-00002", print_format=fmt)
    pdf = get_pdf(html)
    checks = {
        "box_line": "<b>1 箱/Caixa</b>" in html,   # 简版：箱在主位
        "box_hint": "(= 1 箱/Caixa)" in html,       # 颜色版：本位数量下的折箱提示
        "base_hint": "(= 12 根)" in html,           # 简版：退到括号里的本位数量
        "total_with_unit": "180 根" in html,        # 合计带本位单位
        "leftover_jinja": "{%" in html,
        "pdf_ok": pdf[:4] == b"%PDF",
        "pdf_bytes": len(pdf),
        "html_bytes": len(html),
    }
    print(fmt, checks)

import sys
sys.stdout.flush()
