"""Ensure variant swatch attachments win over inherited template images."""
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
frappe.conf = {}
frappe.db = types.SimpleNamespace(
    get_value=lambda doctype, name, field: "/files/rod-template.png" if doctype == "Item" else None,
    has_column=lambda *_args: True,
)
frappe.utils = types.ModuleType("frappe.utils")
frappe.utils.get_url = lambda: "https://erp.solua.one"
frappe.get_all = lambda *_args, **_kwargs: [
    Row(
        file_name="SH151138-2MS-2.png",
        file_url="/files/SH151138-2MS-2.png",
        attached_to_field="custom_swatch_image",
    )
]
sys.modules["frappe"] = frappe
sys.modules["frappe.utils"] = frappe.utils

spec = importlib.util.spec_from_file_location("color_card_candidate", ROOT / "api" / "color_card.py")
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)

item = Row(
    name="SH151138-2MS-Bronze-Antigo",
    item_code="SH151138-2MS-Bronze-Antigo",
    variant_of="SH151138-2MS",
    image="/files/rod-template.png",
    custom_swatch_image=None,
)
assert module.get_item_color_image(item) == "/files/SH151138-2MS-2.png"
print("PASS: custom_swatch_image attachment wins over inherited template image")
