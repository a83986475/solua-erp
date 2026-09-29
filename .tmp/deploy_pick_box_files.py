"""通过 bench console 以 frappe 身份执行：复制文件 + 更新两份拣货单 Print Format。

用法：echo "exec(open('/tmp/deploy_pick_box_files.py').read())" | bench --site erp.solua.one console
"""
import json
import os
import shutil

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

frappe.set_user("Administrator")
for folder, name in (("pick_list_simple", "拣货单（简版）"), ("pick_list_color", "拣货单（颜色版）")):
    payload = json.load(open(f"/tmp/{folder}.json", encoding="utf-8"))
    doc = frappe.get_doc("Print Format", name)
    changed = [f for f in FIELDS
               if f in payload and (doc.get(f) or "") != (payload[f] or "")]
    for f in changed:
        doc.set(f, payload[f])
    if changed:
        doc.save(ignore_permissions=True)
        print("updated", name, changed)
    else:
        print("unchanged", name)

frappe.db.commit()

for folder, name in (("pick_list_simple", "拣货单（简版）"), ("pick_list_color", "拣货单（颜色版）")):
    payload = json.load(open(f"/tmp/{folder}.json", encoding="utf-8"))
    doc = frappe.get_doc("Print Format", name)
    norm = lambda s: (s or "").replace("\r\n", "\n")
    print(name, "html_match=", norm(doc.html) == norm(payload["html"]),
          "css_match=", norm(doc.css) == norm(payload["css"]),
          "module=", doc.module, "custom=", doc.custom_format, "type=", doc.print_format_type,
          "standard=", doc.standard)
import sys
sys.stdout.flush()
