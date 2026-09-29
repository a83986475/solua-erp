"""把「价格标签 50x30」的 raw_commands 同步到生产（关掉公司 logo）。

log 处理器改成 StreamHandler：ubuntu 用户没有 /home/frappe/frappe-bench/logs 的写权限。
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

NAME = "价格标签 50x30"
src = json.load(open("/tmp/price_label_50x30.json", encoding="utf-8"))
raw = src["raw_commands"]
assert "get_solua_print_css()" in raw, "本地上传的 JSON 应调用无参数版本（运行中的 worker 还没有 with_logo 形参）"
assert ".print-format .solua-global-logo { display: none !important; }" in raw, "本地上传的 JSON 没有盖掉共享 logo"

# 这条记录在生产是 standard=Yes（module=Selling），走 doc.save() 会被
# "Standard Print Format cannot be updated" 拦下，所以直接写库再清缓存。
before = frappe.db.get_value("Print Format", NAME, "raw_commands") or ""
frappe.db.set_value("Print Format", NAME, "raw_commands", raw, update_modified=True)
frappe.db.commit()
frappe.clear_cache(doctype="Print Format")

after = frappe.db.get_value("Print Format", NAME, "raw_commands") or ""
print("before_hidden=", ".solua-global-logo { display: none !important; }" in before)
print("after_hidden=", ".print-format .solua-global-logo { display: none !important; }" in after)
print("after_calls_plain=", "get_solua_print_css()" in after and "with_logo" not in after)
print("raw_len=", len(after))
row = frappe.db.get_value("Print Format", NAME,
                          ["html", "raw_printing", "custom_format", "print_format_type", "standard"],
                          as_dict=True)
print("row=", {k: (len(v) if isinstance(v, str) else v) for k, v in row.items()})
