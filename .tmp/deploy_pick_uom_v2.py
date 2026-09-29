import os, logging, json, re

os.chdir("/home/frappe/frappe-bench/sites")
import frappe
import frappe.utils.logger as _flog
_flog.create_handler = lambda *a, **k: [logging.StreamHandler()]
frappe.init(site="erp.solua.one", sites_path="/home/frappe/frappe-bench/sites")
frappe.connect()
frappe.set_user("Administrator")

BASE = "/home/frappe/frappe-bench/apps/solua_home/solua_home"
SIMPLE = "\u62e3\u8d27\u5355\uff08\u7b80\u7248\uff09"
out = {}

from solua_home import install as installer
from frappe.modules.import_file import import_file_by_path

out["format_exists"] = bool(frappe.db.exists("Print Format", installer.PICK_LIST_PRINT_FORMAT))
installer.configure_pick_list_printing()
import_file_by_path(f"{BASE}/print_format/pick_list_simple/pick_list_simple.json", force=True, ignore_version=True)
frappe.db.commit()

out["pick_default"] = frappe.get_meta("Pick List").default_print_format
out["property_setters"] = frappe.get_all(
    "Property Setter", filters={"doc_type": "Pick List", "property": "default_print_format"},
    fields=["name", "value", "property_type"])
out["allow_uom_from_item"] = frappe.db.get_single_value(
    "Stock Settings", "allow_uom_with_conversion_rate_defined_in_item")

# 单位下拉限制的数据基础：ERPNext 保证每个物料都有一行本位单位
out["items_total"] = frappe.db.count("Item")
out["items_missing_stock_uom_row"] = frappe.db.sql(
    "select count(*) from `tabItem` i where not exists (select 1 from `tabUOM Conversion Detail` d "
    "where d.parent = i.name and d.uom = i.stock_uom)")[0][0]
curtain = frappe.get_all("Item", filters={"has_variants": 1, "stock_uom": "\u6761"},
                         pluck="name", limit=1)
curtain_variant = frappe.get_all("Item", filters={"variant_of": ["in", curtain]}, pluck="name", limit=1) \
    if curtain else []
sample_codes = ["SH151138-2MS", "SH151138-2MS-1"] + curtain + curtain_variant
out["uom_tables"] = {
    code: [[r.uom, r.conversion_factor] for r in frappe.get_doc("Item", code).uoms]
    for code in sample_codes if frappe.db.exists("Item", code)}

pick = frappe.get_all("Pick List", filters={"docstatus": 1}, fields=["name"], order_by="creation desc", limit=1)
out["renders"] = {}
if pick:
    doc = frappe.get_doc("Pick List", pick[0].name)
    html = frappe.get_print("Pick List", doc.name, print_format=SIMPLE, as_pdf=False)
    row_uoms = [{"item": r.item_code, "uom": r.uom, "qty": r.qty, "sf": r.conversion_factor,
                 "stock_qty": r.stock_qty} for r in doc.locations[:3]]
    out["sample"] = {"name": doc.name, "rows": len(doc.locations), "first_rows": row_uoms}
    out["renders"][SIMPLE] = {
        "ok": True,
        "qty_cells": re.findall(r'class="col-qty num">(.*?)</td>', html, re.S)[:3],
        "has_pack": "\u7bb1/Caixa" in html,
        "pack_count": len(re.findall(r"\(= [^<]*\u7bb1/Caixa\)", html)),
        "no_jinja": "{%" not in html,
    }
    with open("/tmp/pick_list_simple_preview.html", "w", encoding="utf-8") as fh:
        fh.write(html)
    out["preview"] = "/tmp/pick_list_simple_preview.html"

# 用交易实际调用的换算查找验证：行单位选箱时 ERPNext 会用的换算式
from erpnext.stock.get_item_details import get_conversion_factor
out["get_conversion_factor"] = {
    code: get_conversion_factor(code, "\u7bb1/Caixa")["conversion_factor"]
    for code in ("SH151138-2MS-1", "SH151145-2MD-3", "SH151152-3MS-5", "SH151169-3MD-2")}

print(json.dumps(out, ensure_ascii=True, indent=1, default=str))
frappe.db.rollback()
