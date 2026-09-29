"""Small isolated check for fuzzy Sales Order style lookup."""

import importlib.util
import sys
import types
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


class Row(dict):
    __getattr__ = dict.get


frappe = types.ModuleType("frappe")
frappe._ = lambda value: value
frappe.whitelist = lambda fn=None, **_kwargs: fn if fn else (lambda wrapped: wrapped)
frappe.read_only = lambda fn=None, **_kwargs: fn if fn else (lambda wrapped: wrapped)
frappe.session = types.SimpleNamespace(user="manager")
frappe.db = types.SimpleNamespace(exists=lambda *_args, **_kwargs: True)
frappe.has_permission = lambda *_args, **_kwargs: True
frappe.get_meta = lambda _doctype: types.SimpleNamespace(has_field=lambda _field: True)
frappe.utils = types.ModuleType("frappe.utils")
frappe.utils.flt = lambda value: float(value or 0)
frappe.utils.nowdate = lambda: "2026-09-29"
sys.modules["frappe"] = frappe
sys.modules["frappe.utils"] = frappe.utils

spec = importlib.util.spec_from_file_location("home_candidate", ROOT / "api/home.py")
home = importlib.util.module_from_spec(spec)
spec.loader.exec_module(home)

items = [
    Row(name="STYLE-151060", item_code="STYLE-151060", item_name="素雅窗帘", has_variants=1, variant_of="", disabled=0, custom_order_code="SH151060"),
    Row(name="STYLE-151060-01", item_code="STYLE-151060-01", item_name="素雅 1", has_variants=0, variant_of="STYLE-151060", disabled=0, custom_order_code=""),
]
attributes = [Row(parent="STYLE-151060-01", attribute="Cor", attribute_value="01")]


def matches(row, filters):
    for key, wanted in (filters or {}).items():
        if isinstance(wanted, (list, tuple)) and wanted[0] == "in":
            if row.get(key) not in wanted[1]:
                return False
        elif row.get(key) != wanted:
            return False
    return True


def fake_list(doctype, filters=None, fields=None, *, limit=0, order_by=None, or_filters=None):
    if doctype == "Item Barcode":
        return []
    if doctype == "Item Variant Attribute":
        return [row for row in attributes if matches(row, filters)]
    rows = [row for row in items if matches(row, filters)]
    if or_filters:
        rows = [
            row for row in items
            if matches(row, filters)
            and any(value.strip("%").lower() in str(row.get(field) or "").lower() for field, op, value in or_filters if op == "like")
        ]
    if limit:
        rows = rows[:limit]
    return rows


home._can_read = lambda _doctype: True
home._has_field = lambda _doctype, _field: True
home._list = fake_list

fuzzy = home.get_color_variants(barcode="151060", barcode_only=False)
assert fuzzy["state"] == "ok"
assert fuzzy["templates"][0]["variants"][0]["item_code"] == "STYLE-151060-01"
assert home.get_color_variants(barcode="151060", barcode_only=True)["state"] == "no_data"
print("PASS: Sales Order SKU/item-name lookup supports partial matching while strict barcode lookup stays exact")
