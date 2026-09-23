"""Read-only checks for Sales Order barcode/description resolution."""
import importlib.util
import sys
import types
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


class Doc(dict):
    __getattr__ = dict.__getitem__
    __setattr__ = dict.__setitem__


items = {}
barcodes = {}

frappe = types.ModuleType("frappe")
frappe._ = lambda value: value
frappe.get_meta = lambda doctype: types.SimpleNamespace(has_field=lambda field: field in {
    "variant_of", "description", "custom_item_description_pt", "custom_label_barcode",
})
frappe.db = types.SimpleNamespace(
    get_value=lambda doctype, name, fields, as_dict=False: Doc(items.get(name, {}))
    if doctype == "Item" else None,
)
frappe.get_all = lambda doctype, filters=None, **kwargs: [
    Doc(row) for row in barcodes.get((filters or {}).get("parent"), [])
] if doctype == "Item Barcode" else []
frappe.utils = types.SimpleNamespace()
sys.modules["frappe"] = frappe

spec = importlib.util.spec_from_file_location("sales_order_display", ROOT / "printing" / "wholesale.py")
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)

# Variant without an independent barcode inherits the template's real barcode.
items.update({
    "TPL-RED": {"variant_of": "TPL", "description": "<p>English red</p>", "custom_item_description_pt": "<p>Cortina <b>vermelha</b><br>premium</p>"},
    "TPL": {"variant_of": "", "description": "Template description"},
})
barcodes["TPL"] = [{"barcode": "6901234567892", "barcode_type": "EAN"}]
display = module.get_item_sales_display("TPL-RED")
assert display["barcode"] == "6901234567892"
assert display["description"] == "Cortina vermelha premium"

# Portuguese text wins; when absent, the clean standard description is used.
items["PLAIN"] = {"variant_of": "", "description": "<div>Standard <i>description</i></div>", "custom_item_description_pt": ""}
assert module.get_item_sales_display("PLAIN")["description"] == "Standard description"

# Never turn an item code into a fake barcode.
items["NO-CODE"] = {"variant_of": "", "description": "No barcode"}
assert module.get_item_sales_display("NO-CODE")["barcode"] == ""

print("PASS: Sales Order barcode inheritance, Portuguese/standard description fallback, no item_code barcode")
