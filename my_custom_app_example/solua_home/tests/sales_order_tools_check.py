"""Small isolated checks for Sales Order upload and bulk-selection tools."""

import importlib.util
import json
import sys
import types
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


class Dict(dict):
    __getattr__ = dict.get
    __setattr__ = dict.__setitem__


frappe = types.ModuleType("frappe")
frappe._dict = lambda value=None: Dict(value or {})
frappe._ = lambda value: value
frappe.parse_json = json.loads
frappe.whitelist = lambda fn=None, **_kwargs: fn if fn else (lambda wrapped: wrapped)
frappe.utils = types.SimpleNamespace(nowdate=lambda: "2026-09-22")
frappe_utils = types.ModuleType("frappe.utils")
frappe_utils.nowdate = lambda: "2026-09-22"
frappe_utils.cint = lambda value: int(value or 0)
frappe_utils.flt = lambda value: float(value or 0)
frappe.throw = lambda message: (_ for _ in ()).throw(ValueError(str(message)))

masters = {
    "GOOD": Dict(name="GOOD", item_name="Good item", item_group="Curtains", variant_of="TPL", has_variants=0, disabled=0, is_stock_item=1),
    "DISABLED": Dict(name="DISABLED", item_name="Disabled", item_group="Curtains", has_variants=0, disabled=1, is_stock_item=1),
    "TEMPLATE": Dict(name="TEMPLATE", item_name="Template", item_group="Curtains", has_variants=1, disabled=0, is_stock_item=1),
    "NO-PRICE": Dict(name="NO-PRICE", item_name="No price", item_group="Curtains", has_variants=0, disabled=0, is_stock_item=1),
}


class DB:
    def get_value(self, doctype, name, fields, as_dict=False):
        if doctype != "Item":
            return None
        return masters.get(name)


frappe.db = DB()
frappe.get_meta = lambda *_args, **_kwargs: types.SimpleNamespace(has_field=lambda _field: True)
sys.modules["frappe"] = frappe
sys.modules["frappe.utils"] = frappe_utils

stock_api = types.ModuleType("solua_home.api.stock")
stock_api.validate_transaction_quantities = lambda _doc: None
sys.modules["solua_home.api.stock"] = stock_api

bin_api = types.ModuleType("erpnext.stock.get_item_details")
bin_api.get_bin_details = lambda item_code, warehouse, company=None, include_child_warehouses=False: {
    "actual_qty": 10 if item_code == "GOOD" else 0,
    "reserved_qty": 3 if item_code == "GOOD" else 0,
}
sys.modules["erpnext.stock.get_item_details"] = bin_api

color_card = types.ModuleType("solua_home.printing.color_card")
color_card.get_item_color_info = lambda _code: {
    "order_code": "GOOD-01", "color_code": "01", "color_name": "Red", "image": "/red.png", "template_code": "TPL"
}
sys.modules["solua_home.printing.color_card"] = color_card

wholesale = types.ModuleType("solua_home.printing.wholesale")
wholesale.get_item_sales_display = lambda _code, description="": {"barcode": "6901234567892", "description": "Portuguese description"}
sys.modules["solua_home.printing.wholesale"] = wholesale

spec = importlib.util.spec_from_file_location("sales_candidate", ROOT / "api/sales.py")
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)

native_calls = []


def native_details(item_code, context, qty=1, warehouse=None, price_list=None):
    native_calls.append((item_code, context.get("company"), context.get("customer"), context.get("price_list"), context.get("transaction_date"), warehouse, price_list))
    if item_code == "NO-PRICE":
        rate = 0
    else:
        rate = 100 if price_list in (None, "Wholesale Selling 3") else 480
    return Dict(
        item_name=masters[item_code].item_name,
        description="Native standard description",
        uom="条", stock_uom="条", conversion_factor=1, warehouse=warehouse or "Receiving - SH",
        rate=rate, price_list_rate=rate,
    )


module._native_sales_item_details = native_details
module._display_price = lambda _code, _context, price_list, warehouse=None: 480 if price_list == "Wholesale Selling" else 430
frappe.get_all = lambda doctype, **_kwargs: [masters["GOOD"]] if doctype == "Item" else []

parsed, parse_errors = module._parse_table_rows([
    ["SKU", "数量"], ["GOOD", 2], ["GOOD", 3], ["NO-PRICE", 1], ["GOOD", 0]
])
assert parsed[0]["qty"] == 5 and len(parse_errors) == 1 and "正整数" in parse_errors[0]["error"]

context = {
    "company": "Solua Home, Lda", "customer": "Customer A", "price_list": "Wholesale Selling 3",
    "currency": "MZN", "transaction_date": "2026-09-22", "set_warehouse": "Receiving - SH",
}
result = module._resolve_sales_rows(parsed[:1], context)
assert result["summary"] == {"valid": 1, "errors": 0}
row = result["rows"][0]
assert row["qty"] == 5 and row["available_qty"] == 7 and row["custom_item_barcode"] == "6901234567892"
assert row["wholesale_rate"] == 480 and row["standard_selling_rate"] == 430
assert native_calls[0][1:5] == ("Solua Home, Lda", "Customer A", "Wholesale Selling 3", "2026-09-22")

bad = module._resolve_sales_rows([
    {"item_code": "MISSING", "qty": 1}, {"item_code": "TEMPLATE", "qty": 1},
    {"item_code": "DISABLED", "qty": 1}, {"item_code": "NO-PRICE", "qty": 1},
], context)
assert bad["summary"]["valid"] == 0 and bad["summary"]["errors"] == 4
assert any("模板物料" in item["error"] for item in bad["errors"])
assert any("当前销售价格表" in item["error"] for item in bad["errors"])

paste = module.preview_sales_order_paste("货号\t数量\nGOOD\t2\nGOOD\t1", json.dumps(context))
assert paste["summary"] == {"valid": 1, "errors": 0} and paste["rows"][0]["qty"] == 3
search = module.search_sales_order_items(json.dumps(context), json.dumps({"warehouse": "Receiving - SH", "in_stock": 1}))
assert len(search["items"]) == 1 and search["items"][0]["available_qty"] == 7
print("PASS: upload aliases/merge, native pricing context, exception summary, live Bin available quantity")
