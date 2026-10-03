"""Focused permission/data-shape checks for the homepage APIs (no site writes)."""
import importlib.util
import sys
import types
from pathlib import Path


class Row(dict):
    __getattr__ = dict.__getitem__


def identity(fn=None):
    return fn if fn else lambda value: value


frappe = types.ModuleType("frappe")
frappe._ = lambda value: value
frappe.whitelist = identity
frappe.read_only = identity
frappe.utils = types.ModuleType("frappe.utils")
frappe.utils.flt = lambda value, precision=None: float(value or 0)
frappe.utils.nowdate = lambda: "2026-10-03"
sys.modules["frappe"] = frappe
sys.modules["frappe.utils"] = frappe.utils
ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("home_candidate", ROOT / "api/home.py")
home = importlib.util.module_from_spec(spec)
spec.loader.exec_module(home)


def billing_rows(company, start, end):
    return [
        {"customer": "C1", "name": "DN1", "date": "2026-10-01", "amount": 10,
         "waiting_days": 2, "draft_invoices": ["SI1", "SI2"]},
        {"customer": "C1", "name": "DN2", "date": "2026-10-02", "amount": 20,
         "waiting_days": 1, "draft_invoices": []},
        {"customer": "C2", "name": "DN3", "date": "2026-10-03", "amount": 5,
         "waiting_days": 0, "draft_invoices": []},
    ]


unbilled = types.ModuleType("solua_home.api.unbilled")
unbilled.get_rows = billing_rows
sys.modules["solua_home.api.unbilled"] = unbilled
home._resolve_company = lambda company=None: types.SimpleNamespace(name=company or "Co")
home._can_read = lambda doctype: doctype in {"Delivery Note", "Sales Invoice", "Item", "Bin"}
home._can_create = lambda doctype: doctype == "Sales Invoice"
queue = home.get_billing_queue("Co")
assert queue["count"] == 2 and queue["delivery_note_count"] == 3
assert queue["customers"][0]["amount"] == 30
assert queue["customers"][0]["jobs"][0]["draft_invoices"] == ["SI1", "SI2"]
assert queue["customers"][0]["jobs"][1]["draft_invoices"] == []
home._can_read = lambda doctype: False
assert home.get_billing_queue("Co")["state"] == "no_permission"
home._can_read = lambda doctype: doctype in {"Item", "Bin"}

home._list = lambda doctype, filters=None, fields=None, **kwargs: []
assert home._low_stock("Warehouse")["state"] == "unconfigured"

variant = Row(name="SKU-C20", item_code="SKU-C20", item_name="20", variant_of="STYLE", has_variants=0,
              stock_uom="条", custom_order_code="STYLE", custom_spu_code="", custom_pos_short_name="")
template = Row(name="STYLE", item_code="STYLE", item_name="光感绒", has_variants=1,
               variant_of=None, stock_uom="条", custom_order_code="STYLE", custom_spu_code="", custom_pos_short_name="")
home._has_field = lambda doctype, field: field in {"name", "item_code", "item_name", "custom_order_code", "custom_spu_code", "custom_label_barcode"}
home._resolve_warehouse = lambda company, warehouse=None: warehouse or "W1"
def list_items(doctype, filters=None, fields=None, **kwargs):
    if doctype == "Item":
        if filters and filters.get("variant_of"):
            return [variant]
        if filters and filters.get("name") == "STYLE":
            return [template]
        return [template]
    if doctype == "Item Variant Attribute":
        return [Row(parent="SKU-C20", attribute_value="20")]
    if doctype == "Bin":
        return []  # No visible Bin row is unknown, never a fabricated zero.
    return []
home._list = list_items
result = home.search_items("STYLE", warehouse="W1", company="Co")
assert result["state"] == "ok" and len(result["items"]) == 2
sku = next(item for item in result["items"] if item["name"] == "SKU-C20")
assert sku["template_name"] == "光感绒" and sku["color"] == "20"
assert sku["actual_qty"] is None and sku["available_qty"] is None
print("PASS: all-backlog customer grouping preserves per-delivery drafts; permission empty state; unconfigured reorder thresholds; template and color search; missing Bin does not become zero stock")
