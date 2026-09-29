"""部署拣货单「按箱显示」改动到生产：wholesale.py + 两份拣货单格式 JSON。

log 处理器改成 StreamHandler：ubuntu 用户没有 bench logs 目录写权限。
"""
import json
import logging
import os
import shutil

os.chdir("/home/frappe/frappe-bench/sites")
import frappe  # noqa: E402
import frappe.utils.logger as _flog  # noqa: E402

_flog.create_handler = lambda *a, **k: [logging.StreamHandler()]
frappe.init(site="erp.solua.one", sites_path="/home/frappe/frappe-bench/sites")
frappe.connect()
frappe.set_user("Administrator")

APP = "/home/frappe/frappe-bench/apps/solua_home/solua_home"
COPIES = [
    ("/tmp/wholesale.py.new", f"{APP}/printing/wholesale.py"),
    ("/tmp/pick_list_simple.json", f"{APP}/print_format/pick_list_simple/pick_list_simple.json"),
    ("/tmp/pick_list_color.json", f"{APP}/print_format/pick_list_color/pick_list_color.json"),
]
for src, dst in COPIES:
    shutil.copyfile(src, dst)
    os.chmod(dst, 0o644)
    print("copied ->", dst, os.path.getsize(dst))

FIELDS = ["html", "css", "raw_commands", "raw_printing", "custom_format",
          "print_format_type", "standard", "module", "disabled", "idx",
          "line_breaks", "show_section_headings", "print_format_builder"]

for folder, name in (("pick_list_simple", "拣货单（简版）"), ("pick_list_color", "拣货单（颜色版）")):
    payload = json.load(open(f"/tmp/{folder}.json", encoding="utf-8"))
    doc = frappe.get_doc("Print Format", name)
    changed = []
    for field in FIELDS:
        if field not in payload:
            continue
        new = payload[field]
        if (doc.get(field) or "") != (new or ""):
            doc.set(field, new)
            changed.append(field)
    if changed:
        doc.save(ignore_permissions=True)
        print("updated", name, changed)
    else:
        print("unchanged", name)

frappe.db.commit()

for folder, name in (("pick_list_simple", "拣货单（简版）"), ("pick_list_color", "拣货单（颜色版）")):
    payload = json.load(open(f"/tmp/{folder}.json", encoding="utf-8"))
    doc = frappe.get_doc("Print Format", name)
    print(name, "html_match=", doc.html == payload["html"], "css_match=", doc.css == payload["css"],
          "module=", doc.module, "custom=", doc.custom_format, "type=", doc.print_format_type)
