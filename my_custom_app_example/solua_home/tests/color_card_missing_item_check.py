"""Ensure historical print data survives a removed Item master."""
import importlib.util
import sys
import types
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


class MissingItem(Exception):
    pass


frappe = types.ModuleType("frappe")
frappe.DoesNotExistError = MissingItem
frappe.get_doc = lambda doctype, name: (_ for _ in ()).throw(MissingItem(name))
frappe._ = lambda text: text
sys.modules["frappe"] = frappe

api_color_card = types.ModuleType("solua_home.api.color_card")
api_color_card.get_item_color_image = lambda item: ""
api_color_card.get_item_cor = lambda item_code, item=None: ""
api_color_card.get_public_color_card_url = lambda item_code: ""
sys.modules["solua_home.api.color_card"] = api_color_card

spec = importlib.util.spec_from_file_location("color_card_candidate", ROOT / "printing" / "color_card.py")
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)

assert module.get_item_color_info("SH151169-3MD-5") == {}
print("PASS: missing Item does not abort historical print rendering")
