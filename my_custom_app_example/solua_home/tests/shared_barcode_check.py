"""Run with Python; use isolated mocks and never connect to an ERPNext site."""
import importlib.util
from pathlib import Path
import sys
import types

ROOT = Path(__file__).resolve().parents[1]
messages = []
barcode_rows = []
get_all_handler = None
get_value_handler = None


class Doc(dict):
    __getattr__ = dict.__getitem__
    __setattr__ = dict.__setitem__

    def is_new(self):
        return False


class FakeDB:
    def has_column(self, *args):
        return False

    def get_value(self, *args, **kwargs):
        if get_value_handler:
            return get_value_handler(*args, **kwargs)
        return None


def get_all(doctype, *args, **kwargs):
    if get_all_handler:
        return get_all_handler(doctype, *args, **kwargs)
    if doctype == "Item Barcode":
        if kwargs.get("pluck"):
            return [row.get(kwargs["pluck"]) for row in barcode_rows]
        return barcode_rows
    return []


frappe = types.ModuleType("frappe")
frappe._ = lambda text: text
frappe.msgprint = lambda message, **kwargs: messages.append((message, kwargs))
frappe.throw = lambda message, **kwargs: (_ for _ in ()).throw(AssertionError(message))
frappe.whitelist = lambda *args, **kwargs: (lambda fn: fn)
frappe.get_all = get_all
frappe.db = FakeDB()
frappe.utils = types.ModuleType("frappe.utils")
frappe.utils.cint = lambda value: int(value or 0)
frappe.utils.flt = lambda value: float(value or 0)
sys.modules["frappe"] = frappe
sys.modules["frappe.utils"] = frappe.utils


def load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


stock = load("shared_barcode_stock", ROOT / "api" / "stock.py")
label_helpers = load("shared_barcode_helpers", ROOT / "printing" / "label_helpers.py")
pos = load("shared_barcode_pos", ROOT / "api" / "pos.py")

solua_home = types.ModuleType("solua_home")
solua_home.__path__ = []
api_package = types.ModuleType("solua_home.api")
api_package.__path__ = []
stock_package = types.ModuleType("solua_home.api.stock")
stock_package.validate_positive_integer_qty = lambda *args, **kwargs: None
sys.modules["solua_home"] = solua_home
sys.modules["solua_home.api"] = api_package
sys.modules["solua_home.api.stock"] = stock_package
label_api = load("shared_barcode_label_api", ROOT / "api" / "label_print.py")


def make_color_variant(label="OLD-LABEL"):
    return Doc(
        name="TPL-RED",
        item_code="TPL-RED",
        item_name="Curtain / Red",
        variant_of="TPL",
        attributes=[{"attribute": "Cor", "attribute_value": "Red"}],
        barcodes=[],
        custom_label_barcode=label,
        is_stock_item=1,
        valuation_rate=10,
    )


# A single non-empty template barcode is inherited unchanged.
barcode_rows = [{"barcode": "6901234567890"}]
variant = make_color_variant()
stock.validate_item(variant)
assert variant.custom_label_barcode == "6901234567890"

# Missing or multiple distinct template barcodes preserve the old value and warn.
for rows, expected_reason in (([], "没有非空 Item Barcode"), ([{"barcode": "A"}, {"barcode": "B"}], "有多个不同 Item Barcode")):
    barcode_rows = rows
    messages.clear()
    variant = make_color_variant()
    stock.validate_item(variant)
    assert variant.custom_label_barcode == "OLD-LABEL"
    assert messages and expected_reason in messages[-1][0]

# POS barcode scanning resolves the native template barcode into a color-choice response.
def pos_get_value(doctype, name, fieldname=None, *args, **kwargs):
    if doctype == "Item Barcode":
        return "TPL" if name == {"barcode": "6901234567890"} else None
    if doctype == "Item" and name == "TPL" and fieldname == "has_variants":
        return 1
    if doctype == "Item" and name == "TPL" and fieldname == "item_name":
        return "Curtain"
    if doctype == "Item Variant Attribute" and name.get("parent") == "TPL-RED":
        return "Red"
    return None


def pos_get_all(doctype, *args, **kwargs):
    if doctype == "Item":
        return [types.SimpleNamespace(item_code="TPL-RED", item_name="Curtain / Red", image="/red.png")]
    return []


get_value_handler = pos_get_value
get_all_handler = pos_get_all
response = pos.scan_barcode_for_pos("6901234567890")
assert response["type"] == "template"
assert response["template_code"] == "TPL"
assert response["colors"][0]["variant_code"] == "TPL-RED"
pos_js = (ROOT / "public" / "js" / "pos_custom.js").read_text(encoding="utf-8")
assert 'res.type === "template"' in pos_js and "show_color_picker(res)" in pos_js

# The Print Format helper and label-search API prefer/list the shared custom label barcode.
variant = types.SimpleNamespace(
    name="TPL-RED", variant_of="TPL", custom_label_barcode="6901234567890",
    barcodes=[types.SimpleNamespace(barcode="WRONG-VARIANT-CODE", barcode_type="")],
)
assert label_helpers._get_barcode(variant) == ("6901234567890", "code128")

get_all_handler = lambda doctype, *args, **kwargs: []
get_value_handler = lambda doctype, name, fieldname=None, *args, **kwargs: "6901234567890" if fieldname == "custom_label_barcode" else None
api_barcodes = label_api._get_barcodes("TPL-RED", True)
assert api_barcodes == [{"barcode": "6901234567890", "barcode_type": "EAN"}]

# Confirm the UI wizard's insert/save path remains covered by Item.validate.
hooks = (ROOT / "hooks.py").read_text(encoding="utf-8")
variants_source = (ROOT / "api" / "variants.py").read_text(encoding="utf-8")
wizard_source = (ROOT / "public" / "js" / "item_variant_wizard.js").read_text(encoding="utf-8")
assert '"validate": "solua_home.api.stock.validate_item"' in hooks
assert "v.insert()" in variants_source and "v.save(ignore_permissions=True)" in variants_source
assert "solua_home.api.variants.bulk_create_variants" in wizard_source

print("shared barcode checks passed: inheritance, missing/multiple warnings, POS template color choice, label priority, wizard hook path")
