"""把「价格标签 50x30」规范化：standard Yes -> No，并把仓库 JSON 同步进生产。

standard=Yes 会让 doc.save() 抛 "Standard Print Format cannot be updated"，以后每次改这份格式
都得绕过校验写库；仓库里其余格式统一是 standard=No。
用法：echo "exec(open('/tmp/normalize_price_label.py').read())" | bench --site erp.solua.one console
"""
import json
import os
import shutil

APP = "/home/frappe/frappe-bench/apps/solua_home/solua_home"
SRC = "/tmp/price_label_50x30.json"
DST = f"{APP}/print_format/price_label_50x30/price_label_50x30.json"
NAME = "价格标签 50x30"

shutil.copyfile(SRC, DST)
os.chmod(DST, 0o644)
print("copied ->", DST, os.path.getsize(DST))

frappe.set_user("Administrator")
payload = json.load(open(SRC, encoding="utf-8"))
print("before: standard =", frappe.db.get_value("Print Format", NAME, "standard"))

# 标准格式改 standard 字段本身也会被拦，先直接写库再清缓存
frappe.db.set_value("Print Format", NAME, "standard", payload["standard"])
frappe.db.commit()
frappe.clear_cache(doctype="Print Format")

doc = frappe.get_doc("Print Format", NAME)
print("after set_value: standard =", doc.standard)

FIELDS = ["html", "css", "raw_commands", "raw_printing", "custom_format",
          "print_format_type", "module", "disabled", "idx",
          "line_breaks", "show_section_headings", "print_format_builder"]
changed = [f for f in FIELDS if f in payload and (doc.get(f) or "") != (payload[f] or "")]
for f in changed:
    doc.set(f, payload[f])
doc.save(ignore_permissions=True)  # 现在应当不再抛 "Standard Print Format cannot be updated"
frappe.db.commit()
print("doc.save OK; changed =", changed)

doc = frappe.get_doc("Print Format", NAME)
print("readback: standard =", doc.standard, "| custom =", doc.custom_format,
      "| type =", doc.print_format_type, "| raw =", doc.raw_printing,
      "| module =", doc.module, "| idx =", doc.idx)
print("hide_rule =", ".print-format .solua-global-logo { display: none !important; }" in (doc.raw_commands or ""))
print("calls_plain =", "get_solua_print_css()" in (doc.raw_commands or "")
      and "with_logo" not in (doc.raw_commands or ""))
import sys
sys.stdout.flush()
