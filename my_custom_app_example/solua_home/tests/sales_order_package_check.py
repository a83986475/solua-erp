"""Small isolated check for the Sales Order document package."""
import importlib.util
import io
import json
import sys
import types
from pathlib import Path
from zipfile import ZipFile

ROOT = Path(__file__).resolve().parents[1]


class Doc(dict):
    __getattr__ = dict.__getitem__
    __setattr__ = dict.__setitem__


docs = {
    "SO-1": Doc(
        doctype="Sales Order",
        name="SO-1",
        transaction_date="2026-09-30",
        customer_name="客人一",
        docstatus=1,
    ),
    "DN-1": Doc(
        doctype="Delivery Note",
        name="DN-1",
        posting_date="2026-09-30",
        docstatus=1,
    ),
    "PL-1": Doc(
        doctype="Pick List",
        name="PL-1",
        creation="2026-09-30 08:30:00",
        docstatus=0,
        locations=[Doc(item_code="ITEM-1", item_name="商品一", qty=3, picked_qty=0, uom="条", warehouse="WH-1")],
    ),
}
print_calls = []

frappe = types.ModuleType("frappe")
frappe._ = lambda text: text
frappe.PermissionError = PermissionError
frappe.whitelist = lambda *args, **kwargs: (lambda function: function)
frappe.concurrent_limit = lambda *args, **kwargs: (lambda function: function)
frappe.parse_json = json.loads
frappe.as_json = json.dumps
frappe.get_doc = lambda doctype, name: docs[name]
frappe.has_permission = lambda *args, **kwargs: True
frappe.get_all = lambda doctype, **kwargs: (
    ["DN-1"] if doctype == "Delivery Note Item" else ["PL-1"] if doctype == "Pick List Item" else []
)
frappe.get_print = lambda doctype, name, **kwargs: (
    print_calls.append((doctype, name, kwargs.get("doc", {}).get("custom_print_merge_order_code")))
    or f"<html>{doctype}/{name}</html>"
)
frappe.throw = lambda message, exc=None: (_ for _ in ()).throw((exc or ValueError)(message))
frappe.local = types.SimpleNamespace(response=types.SimpleNamespace())
frappe.utils = types.ModuleType("frappe.utils")
frappe.utils.cint = lambda value: int(value or 0)
frappe.utils.flt = lambda value: float(value or 0)
frappe.utils.nowdate = lambda: "2026-09-30"
frappe.utils.xlsxutils = types.ModuleType("frappe.utils.xlsxutils")
frappe.utils.xlsxutils.make_xlsx = lambda table, sheet_name, **kwargs: io.BytesIO(
    (sheet_name + ":" + str(table)).encode("utf-8")
)
sys.modules["frappe"] = frappe
sys.modules["frappe.utils"] = frappe.utils
sys.modules["frappe.utils.xlsxutils"] = frappe.utils.xlsxutils

pdf = types.ModuleType("frappe.utils.pdf")
pdf.get_pdf = lambda html, options: html.encode("utf-8")
sys.modules["frappe.utils.pdf"] = pdf

wholesale = types.ModuleType("solua_home.printing.wholesale")
items = [
    {"order_code": "SH-1", "item_code": "SH-1-BLACK", "barcode": "111", "qty": 2, "rate": 10, "amount": 20, "uom": "条"},
    {"order_code": "SH-1", "item_code": "SH-1-WHITE", "barcode": "222", "qty": 3, "rate": 10, "amount": 30, "uom": "条"},
]
wholesale.get_wholesale_print_data = lambda doc: {"items": [dict(row) for row in items]}
wholesale._merge_customer_print_items = lambda rows: [
    {**rows[0], "qty": rows[0]["qty"] + rows[1]["qty"], "amount": rows[0]["amount"] + rows[1]["amount"]}
]
wholesale.get_item_color_info = lambda item_code: {}
wholesale._get_pick_list_additional_notes = lambda row: ""
wholesale.get_item_sales_display = lambda item_code, description: {"barcode": "", "description": description or ""}
wholesale.get_item_spu = lambda item_code: ""
wholesale.format_print_uom = lambda value, item_code=None: value
solua_home = types.ModuleType("solua_home")
solua_home.__path__ = []
api = types.ModuleType("solua_home.api")
api.__path__ = []
printing = types.ModuleType("solua_home.printing")
printing.__path__ = []
color_card = types.ModuleType("solua_home.printing.color_card")
color_card.get_item_color_info = wholesale.get_item_color_info
sys.modules["solua_home"] = solua_home
sys.modules["solua_home.api"] = api
sys.modules["solua_home.printing"] = printing
sys.modules["solua_home.printing.color_card"] = color_card
sys.modules["solua_home.printing.wholesale"] = wholesale

designer = types.ModuleType("solua_home.api.a4_designer")
designer._active_print_format = lambda doctype: f"{doctype} format"
sys.modules["solua_home.api.a4_designer"] = designer

spec = importlib.util.spec_from_file_location("export_candidate", ROOT / "api/export.py")
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)

assert len(module._customer_import_table(docs["SO-1"], True)) == 2
assert len(module._customer_import_table(docs["SO-1"], False)) == 3
module.download_sales_order_package(json.dumps(["SO-1"], ensure_ascii=False))

with ZipFile(io.BytesIO(frappe.local.response.filecontent)) as archive:
    names = archive.namelist()
    assert names == [
        "SO-1_客人一/01_销售订单_SO-1.pdf",
        "SO-1_客人一/02_客户导入表_合并.xlsx",
        "SO-1_客人一/03_交货单_1_DN-1.pdf",
        "SO-1_客人一/04_拣货单_1_PL-1.pdf",
        "SO-1_客人一/05_员工拣货表_1_PL-1.xlsx",
    ]

assert print_calls == [
    ("Sales Order", "SO-1", 1),
    ("Delivery Note", "DN-1", 1),
    ("Pick List", "PL-1", None),
]
print("PASS: Sales Order package includes merged customer files and unmerged pick files")
