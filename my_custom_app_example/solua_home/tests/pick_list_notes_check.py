"""Small isolated check for Sales Order -> Pick List note mapping."""
import importlib.util
import sys
import types
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


class Doc(dict):
    __getattr__ = dict.__getitem__
    __setattr__ = dict.__setitem__


sales_order_items = {
    "SOI-1": {"parent": "SO-1", "additional_notes": "", "pos_additional_notes": "每箱十条"},
}
sales_order_notes = {"SO-1": "周五前送到"}

frappe = types.ModuleType("frappe")
frappe._ = lambda text: text
frappe.utils = types.ModuleType("frappe.utils")
frappe.utils.cint = lambda value: int(value or 0)
frappe.utils.flt = lambda value: float(value or 0)
frappe.db = types.SimpleNamespace()


def get_value(doctype, name, fields, **kwargs):
    if doctype == "Sales Order Item":
        return sales_order_items.get(name)
    if doctype == "Sales Order":
        return sales_order_notes.get(name, "")
    return None


frappe.db.get_value = get_value
frappe.get_meta = lambda doctype: types.SimpleNamespace(has_field=lambda field: field in {"custom_additional_notes", "pos_additional_notes"})
frappe.throw = lambda message: (_ for _ in ()).throw(ValueError(message))
sys.modules["frappe"] = frappe
sys.modules["frappe.utils"] = frappe.utils

spec = importlib.util.spec_from_file_location("stock_candidate", ROOT / "api/stock.py")
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)

pick = Doc(
    doctype="Pick List",
    locations=[Doc(sales_order_item="SOI-1", sales_order="SO-1", custom_additional_notes="")],
    custom_additional_notes="",
)
module.copy_sales_order_pick_notes(pick)
assert pick.locations[0].custom_additional_notes == "每箱十条"
assert pick.custom_additional_notes == "周五前送到"

existing = Doc(
    doctype="Pick List",
    locations=[Doc(sales_order_item="SOI-1", sales_order="SO-1", custom_additional_notes="现场改备注")],
    custom_additional_notes="现场订单备注",
)
module.copy_sales_order_pick_notes(existing)
assert existing.locations[0].custom_additional_notes == "现场改备注"
assert existing.custom_additional_notes == "现场订单备注"
print("PASS: Sales Order line/header notes copy to Pick List and preserve manual values")
