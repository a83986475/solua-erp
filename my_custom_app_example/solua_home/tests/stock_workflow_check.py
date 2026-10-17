"""Static contract checks for the Sales Order -> Pick List -> Delivery Note guard."""

import ast
import importlib.util
import sys
import types
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def functions(path):
    tree = ast.parse(path.read_text(encoding="utf-8-sig"))
    return {node.name for node in ast.walk(tree) if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))}


stock = ROOT / "api" / "stock.py"
sales = ROOT / "api" / "sales.py"
hooks = ROOT / "hooks.py"
install = ROOT / "install.py"
pick_list = ROOT / "override" / "pick_list.py"
child_items = ROOT / "api" / "child_items.py"

stock_functions = functions(stock)
assert {
    "get_sales_order_stock_requirements",
    "validate_stock_requirements",
    "validate_delivery_route",
    "validate_pick_list_result",
    "validate_pick_list_before_submit",
    "create_pick_list",
    "_pick_list_order_comparison",
    "get_pick_list_sales_order_comparison",
}.issubset(stock_functions)

stock_source = stock.read_text(encoding="utf-8-sig")
assert "pick_list_item" in stock_source
assert "picked_qty" in stock_source
assert "COALESCE(SUM(i.stock_qty),0)" in stock_source
assert "actual_qty - reserved_qty" in stock_source
assert "custom_shortage_note" in stock_source
assert "custom_sales_order" in stock_source
assert "销售订单对比未通过" in stock_source

sales_source = sales.read_text(encoding="utf-8-sig")
assert "get_sales_order_stock_requirements" in sales_source
assert "before_update_after_submit" in hooks.read_text(encoding="utf-8-sig")
assert "remaining = max(_row_stock_qty(item) - delivered_qty * factor, 0)" in stock_source

hooks_source = hooks.read_text(encoding="utf-8-sig")
assert "solua_home.override.pick_list.CustomPickList" in hooks_source
assert "solua_home.api.stock.validate_delivery_route" in hooks_source
assert "solua_home.api.stock.validate_pick_list_before_submit" in hooks_source
assert "erpnext.selling.doctype.sales_order.mapper.create_pick_list" in hooks_source
assert "pick_list_order_reconciliation_v20261009d.js" in hooks_source

install_source = install.read_text(encoding="utf-8-sig")
assert '"fieldname": "custom_pick_result"' in install_source
assert '"fieldname": "custom_shortage_note"' in install_source
assert '"fieldname": "custom_sales_order"' in install_source
assert '"fieldname": "custom_sales_order_comparison_data"' in install_source
assert '"fieldname": "custom_order_comparison_tab"' in install_source
assert '"fieldname": "custom_order_comparison_tab", "label": "订单对比区", "fieldtype": "Tab Break", "insert_after": "locations"' in install_source
assert '"fieldname": "custom_sales_order_comparison"' in install_source
assert "部分拣货" in install_source and "缺货待补" in install_source

assert "class CustomPickList(PickList)" in pick_list.read_text(encoding="utf-8-sig")
assert "_stock_previous_doc" in child_items.read_text(encoding="utf-8-sig")

fake_frappe = types.ModuleType("frappe")
fake_frappe._ = lambda value: value
fake_frappe.get_cached_value = lambda *args: 1
fake_frappe.whitelist = lambda *args, **kwargs: (args[0] if args and callable(args[0]) else (lambda fn: fn))
fake_utils = types.ModuleType("frappe.utils")
fake_utils.flt = lambda value=0, *args: float(value or 0)
fake_utils.cint = lambda value=0, *args: int(value or 0)
sys.modules.update({"frappe": fake_frappe, "frappe.utils": fake_utils})
spec = importlib.util.spec_from_file_location("stock_workflow_stock", stock)
loaded = importlib.util.module_from_spec(spec)
spec.loader.exec_module(loaded)


class Row(dict):
    __getattr__ = dict.get


class Doc(dict):
    def __getattr__(self, fieldname):
        return self.get(fieldname)

    def __setattr__(self, fieldname, value):
        self[fieldname] = value

    def has_product_bundle(self, item_code):
        return item_code == "BUNDLE"


plain = Doc(items=[Row(item_code="ITEM", stock_qty=10, qty=5, delivered_qty=2, conversion_factor=2, warehouse="WH")])
assert loaded.get_sales_order_stock_requirements(plain) == {("ITEM", "WH"): 6}

bundle = Doc(
    items=[Row(name="so-row", item_code="BUNDLE", qty=3, delivered_qty=1, warehouse="WH")],
    packed_items=[Row(parent_detail_docname="so-row", item_code="COMP", qty=2, warehouse="WH")],
)
assert abs(loaded.get_sales_order_stock_requirements(bundle)[("COMP", "WH")] - (4 / 3)) < 0.000001

fake_frappe.get_meta = lambda doctype: types.SimpleNamespace(has_field=lambda fieldname: True)
fake_frappe.throw = lambda message: (_ for _ in ()).throw(RuntimeError(message))
fake_frappe.db = types.SimpleNamespace(get_value=lambda *args, **kwargs: "SO-1")
partial = Doc(
    purpose="Delivery",
    custom_pick_result="部分拣货",
    locations=[Row(item_code="ITEM", stock_qty=10, picked_qty=4)],
)
loaded.validate_pick_list_result(partial, require_result=True)
assert partial.pick_manually == 1 and partial.scan_mode == 1

full = Doc(
    purpose="Delivery",
    custom_pick_result="已拣齐",
    locations=[Row(item_code="ITEM", stock_qty=10, picked_qty=10)],
)
loaded.validate_pick_list_result(full, require_result=True)

comparison_order = Doc(
    items=[
        Row(name="so-row-1", item_code="ITEM", item_name="Item", qty=5, stock_qty=10, delivered_qty=0, picked_qty=0, conversion_factor=2, stock_uom="EA", is_stock_item=1),
        Row(name="so-row-2", item_code="MISSING", item_name="Missing", qty=2, stock_qty=2, delivered_qty=0, picked_qty=0, conversion_factor=1, stock_uom="EA", is_stock_item=1),
    ],
    packed_items=[],
)
fake_frappe.get_doc = lambda doctype, name: comparison_order
comparison = loaded._pick_list_order_comparison(Doc(
    custom_sales_order="SO-1",
    locations=[Row(sales_order_item="so-row-1", item_code="ITEM", stock_qty=10, picked_qty=10)],
))
assert comparison["summary"]["missing_count"] == 1
assert comparison["summary"]["shortage_qty"] == 2
assert comparison["rows"][1]["status"] == "缺货/未生成拣货行"

try:
    loaded.validate_pick_list_result(Doc(
        purpose="Delivery",
        custom_sales_order="SO-1",
        custom_pick_result="已拣齐",
        locations=[Row(item_code="ITEM", stock_qty=10, picked_qty=10, sales_order_item="so-row-1")],
    ), require_result=True)
except RuntimeError as error:
    assert "销售订单对比未通过" in str(error)
else:
    raise AssertionError("a Pick List with a missing Sales Order line was accepted as full")

snapshot = Doc(
    docstatus=1,
    custom_sales_order="SO-1",
    custom_sales_order_comparison_data='{"sales_orders":["SO-1"],"rows":[{"sales_order":"SO-1","sales_order_item":"so-row-1","item_code":"OLD-ITEM","item_name":"Item","stock_uom":"EA","order_qty":10}]}',
    locations=[Row(sales_order_item="so-row-1", item_code="ITEM", stock_qty=10, picked_qty=10)],
)
comparison_order["items"][0].picked_qty = 10
snapshot_comparison = loaded._pick_list_order_comparison(snapshot)
assert snapshot_comparison["summary"]["shortage_qty"] == 0
assert snapshot_comparison["summary"]["extra_count"] == 0
assert snapshot_comparison["summary"]["complete"]

try:
    loaded.validate_pick_list_result(Doc(purpose="Delivery", custom_pick_result="待拣货"), require_result=True)
except RuntimeError:
    pass
else:
    raise AssertionError("unreported Pick List result was accepted")

print("PASS: stock workflow guard contracts are wired")
