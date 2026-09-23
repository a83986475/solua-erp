"""Run with Python; isolated fixtures never connect to a site or write business data."""
import importlib.util
import sys
import types
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

pdf_calls = []
xlsx_calls = []
opened_doctypes = []


class Doc(dict):
    __getattr__ = dict.__getitem__
    __setattr__ = dict.__setitem__


def fail(message, exc=None):
    raise (exc or ValueError)(str(message))


def flt(value):
    try:
        return float(value or 0)
    except (TypeError, ValueError):
        return 0.0


def cint(value):
    try:
        return int(value or 0)
    except (TypeError, ValueError):
        return 0


def get_doc(doctype, name=None):
    opened_doctypes.append((doctype, name))
    if doctype not in frappe.__allowed:
        raise ValueError(f"unknown doctype {doctype}")
    return frappe.__docs[doctype]


utils = types.ModuleType("frappe.utils")
utils.cint = cint
utils.flt = flt
utils.nowdate = lambda: "2026-09-23"

frappe = types.ModuleType("frappe")
frappe._ = lambda text: text
frappe.throw = fail
frappe.PermissionError = PermissionError
frappe.whitelist = lambda *args, **kwargs: (lambda function: function)
frappe.scrub = lambda value: value.lower().replace(" ", "_")
frappe.get_doc = get_doc
frappe.has_permission = lambda doctype, ptype="read", doc=None: doctype not in frappe.__blocked
frappe.utils = utils
frappe.__docs = {}
frappe.__allowed = set()
frappe.__blocked = set()
sys.modules["frappe"] = frappe
sys.modules["frappe.utils"] = utils

desk = types.ModuleType("frappe.desk")
desk_utils = types.ModuleType("frappe.desk.utils")


def provide_binary_file(filename, extension, content):
    pdf_calls.append({"filename": filename, "extension": extension, "content": content})


desk_utils.provide_binary_file = provide_binary_file
sys.modules["frappe.desk"] = desk
sys.modules["frappe.desk.utils"] = desk_utils

xlsxutils = types.ModuleType("frappe.utils.xlsxutils")


def build_xlsx_response(data, filename, styles=None):
    xlsx_calls.append({"data": data, "filename": filename})


xlsxutils.build_xlsx_response = build_xlsx_response
sys.modules["frappe.utils.xlsxutils"] = xlsxutils

# --- stubs for the two printing helpers the export reuses -------------------
wholesale = types.ModuleType("solua_home.printing.wholesale")


def get_wholesale_print_data(doc):
    return doc["print_data"]


wholesale.get_wholesale_print_data = get_wholesale_print_data
wholesale.get_item_sales_display = lambda code, description="": {"barcode": f"BC-{code}", "description": f"desc {code}"}
sys.modules["solua_home.printing.wholesale"] = wholesale

color = types.ModuleType("solua_home.printing.color_card")
color.get_item_color_info = lambda code: {"order_code": f"ORD-{code}", "color_code": "01", "color_name": "Red"}
sys.modules["solua_home.printing.color_card"] = color

spec = importlib.util.spec_from_file_location("export_candidate", ROOT / "api/export.py")
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)


def wholesale_doc(doctype, items, **extra):
    doc = Doc(doctype=doctype, name="DOC-1", docstatus=1, posting_date="2026-09-20", customer="CUST-1",
              customer_name="Customer 1", status="To Bill", currency="MZN", print_data={"items": items})
    doc.update(extra)
    frappe.__docs[doctype] = doc
    frappe.__allowed.add(doctype)
    return doc


def print_items():
    return [
        {"item_code": "A-01", "item_name": "Curtain A", "order_code": "ORD-A", "color_code": "01", "color": "Red",
         "barcode": "BC1", "description": "Red curtain", "qty": 2.5, "uom": "条", "rate": 100, "amount": 250,
         "warehouse": "W1", "ordered_qty": 10, "delivered_before_qty": 3, "remaining_qty": 5},
        {"item_code": "B-02", "item_name": "Curtain B", "order_code": "ORD-B", "color_code": "02", "color": "Blue",
         "barcode": "BC2", "description": "Blue curtain", "qty": 1, "uom": "条", "rate": 300, "amount": 300,
         "warehouse": "W1", "ordered_qty": 4, "delivered_before_qty": 4, "remaining_qty": 0},
    ]


def row_of(table, label):
    for row in table:
        if row and row[0] == label:
            return row
    raise AssertionError(f"row {label!r} not found in {table}")


def index_of(header, label):
    return header.index(label)


# ---------------------------------------------------------------- 列定义
assert module.EXPORT_DOCTYPES == ("Sales Order", "Sales Invoice", "Delivery Note", "Pick List")
assert module.DOCTYPE_COLUMNS["Pick List"] == ("idx", "item_code", "item_name", "color_code", "color", "barcode",
                                              "description", "qty", "picked_qty", "uom", "warehouse")
assert "ordered_qty" in module.DOCTYPE_COLUMNS["Delivery Note"]
assert "ordered_qty" not in module.DOCTYPE_COLUMNS["Sales Order"]
for key in module.DOCTYPE_COLUMNS["Sales Order"]:
    assert key in module.LABELS, key

options = module.get_export_options("Sales Order")
assert [column["key"] for column in options["columns"]] == list(module.DOCTYPE_COLUMNS["Sales Order"])
assert "amount" in options["defaults"] and "qty" in options["defaults"]
assert [entry["value"] for entry in options["formats"]] == ["xlsx", "csv"]
for doctype in ("Sales Invoice", "Delivery Note", "Pick List"):
    assert module.get_export_options(doctype)["columns"], doctype

try:
    module.get_export_options("Item")
    raise AssertionError("unsupported doctype must be rejected")
except ValueError as error:
    assert "不支持导出" in str(error)

# ------------------------------------------------- 选中列：过滤 + 保持列顺序
columns = module._selected_columns("Delivery Note", "remaining_qty, qty, not_a_column, item_code")
assert columns == ["item_code", "qty", "remaining_qty"], columns
assert module._selected_columns("Sales Order", None) == list(module.DOCTYPE_COLUMNS["Sales Order"])
assert module._selected_columns("Sales Order", "amount") == ["amount"]
try:
    module._selected_columns("Sales Order", "nope")
    raise AssertionError("an empty selection must be rejected")
except ValueError as error:
    assert "至少选择一列" in str(error)

# ------------------------------------------------------------------ 构建表格
doc = wholesale_doc("Delivery Note", print_items())
table = module.build_table(doc, None, 1, 1)
assert table[0] == ["单据类型", "Delivery Note"]
assert table[1] == ["单号", "DOC-1"]
assert table[2] == ["日期", "2026-09-20"]
assert table[3] == ["客户", "Customer 1"]
assert table[4] == ["状态", "To Bill"]
assert table[5] == [], "a blank spacer row separates the header block"
header = table[6]
assert header == [module.LABELS[key] for key in module.DOCTYPE_COLUMNS["Delivery Note"]], header
first = table[7]
assert first[index_of(header, "货号")] == "A-01"
assert first[index_of(header, "数量")] == 2.5, "quantity must stay a number for Excel"
assert first[index_of(header, "金额")] == 250
assert first[index_of(header, "订购数量")] == 10
second = table[8]
assert second[index_of(header, "色号")] == "02" and second[index_of(header, "颜色")] == "Blue"
total = table[-1]
assert total[0] == "合计"
assert total[index_of(header, "数量")] == 3.5, total
assert total[index_of(header, "金额")] == 550, total
assert total[index_of(header, "订购数量")] == 14 and total[index_of(header, "剩余数量")] == 5
assert total[index_of(header, "条码")] == "", "text columns have no total"

# 单选一列时，合计标签不能吃掉数字
single = module.build_table(doc, "qty", 0, 1)
assert single == [["数量"], [2.5], [1], [3.5]], single
with_label = module.build_table(doc, "idx,qty", 0, 1)
assert with_label == [["序号", "数量"], [1, 2.5], [2, 1], ["合计", 3.5]], with_label

# 抬头 / 合计行可以分别关掉
assert module.build_table(doc, "item_code,qty", 0, 0) == [["货号", "数量"], ["A-01", 2.5], ["B-02", 1]]
assert module.build_table(doc, "item_code", 0, 1)[-1] == ["合计"]
assert len(module.build_table(doc, None, 1, 0)) == 6 + 1 + 2, "header + column labels + 2 item rows"

# 空明细：只剩表头与合计 0
empty = wholesale_doc("Sales Order", [])
assert module.build_table(empty, "item_code,qty", 0, 1) == [["货号", "数量"], ["合计", 0]]

# CSV 带 BOM、CRLF，且中文表头可读
frappe.__docs["Delivery Note"] = doc
module.export_document_table("Delivery Note", "DOC-1", "item_code,qty,description", "csv", 1, 1)
csv_call = pdf_calls[-1]
assert csv_call["extension"] == "csv"
assert csv_call["filename"].startswith("delivery-note-DOC-1-2026-09-23"), csv_call["filename"]
text = csv_call["content"].decode("utf-8")
assert text.startswith("\ufeff"), "BOM keeps Excel from mangling Chinese"
assert "\r\n" in text
lines = text.split("\r\n")
assert lines[0] == "\ufeff单据类型,Delivery Note", lines[0]
assert lines[1] == "单号,DOC-1" and lines[3] == "客户,Customer 1", lines[:4]
assert "" in lines, "the blank spacer row survives the export"
assert "货号,描述,数量" in lines, lines
assert "A-01,Red curtain,2.5" in text
assert lines[-2] == "合计,,3.5", text[-40:]

# Excel 拿到的是一模一样的行
module.export_document_table("Delivery Note", "DOC-1", "item_code,qty", "xlsx", 0, 1)
xlsx_call = xlsx_calls[-1]
assert xlsx_call["data"] == [["货号", "数量"], ["A-01", 2.5], ["B-02", 1], ["合计", 3.5]], xlsx_call["data"]
assert xlsx_call["filename"].startswith("delivery-note-DOC-1-")

# 拣货单：没有价格，靠 color/print helper 拼行
# 拣货单的行在 locations 子表（Pick List Item），不是 items
pick = Doc(doctype="Pick List", name="PL-1", docstatus=0, status="Open", creation="2026-09-19 08:00:00",
           locations=[Doc(item_code="A-01", item_name="", qty=3, picked_qty=2, uom="条", warehouse="W2"),
                      Doc(item_code="B-02", item_name="Curtain B", description="row desc", qty=1.5, picked_qty=1.5,
                          uom="条", warehouse="W2")])
frappe.__docs["Pick List"] = pick
frappe.__allowed.add("Pick List")
table = module.build_table(pick, None, 1, 1)
assert [row[0] for row in table[:4]] == ["单据类型", "单号", "日期", "状态"], "Pick List has no customer row"
assert table[4] == []
header = table[5]
assert header == ["序号", "货号", "商品名称", "色号", "颜色", "条码", "描述", "数量", "已拣数量", "单位", "仓库"], header
assert table[6] == [1, "A-01", "A-01", "01", "Red", "BC-A-01", "desc A-01", 3, 2, "条", "W2"], table[6]
assert table[7][index_of(header, "描述")] == "desc B-02", "row description falls back to the item master"
assert table[-1][index_of(header, "数量")] == 4.5 and table[-1][index_of(header, "已拣数量")] == 3.5
assert "金额" not in header
pick_only_qty = module.build_table(pick, "item_code,qty,picked_qty", 0, 1)
assert pick_only_qty == [["货号", "数量", "已拣数量"], ["A-01", 3, 2], ["B-02", 1.5, 1.5], ["合计", 4.5, 3.5]]

# --------------------------------------------------------------- 权限 / 白名单
frappe.__blocked.add("Pick List")
try:
    module.export_document_table("Pick List", "PL-1")
    raise AssertionError("missing read permission must be rejected")
except PermissionError:
    pass
frappe.__blocked.discard("Pick List")

try:
    module.export_document_table("Item", "ITEM-1")
    raise AssertionError("unsupported doctype must not be exported")
except ValueError as error:
    assert "不支持导出" in str(error)

assert module.get_export_document("Delivery Note", "DOC-1").name == "DOC-1"
assert ("Delivery Note", "DOC-1") in opened_doctypes

print("PASS: export columns, row building, totals row, csv/xlsx payload, permissions")
