"""Exercise the real list endpoint without a Frappe installation."""
import ast
from pathlib import Path
from types import SimpleNamespace

source = Path(__file__).resolve().parents[1] / "api" / "mobile.py"
tree = ast.parse(source.read_text(encoding="utf-8"))
function = next(node for node in tree.body if isinstance(node, ast.FunctionDef) and node.name == "list_sales_orders")
function.decorator_list = []
calls = []
sql_calls = []


def get_all(doctype, **kwargs):
    calls.append((doctype, kwargs))
    if kwargs.get("fields") == [{"COUNT": "name", "as": "total"}]:
        return [SimpleNamespace(total=45)]
    return []


def sql(statement, params, **kwargs):
    sql_calls.append((statement, params, kwargs))
    return ["SO-MATCH"]


namespace = {
    "frappe": SimpleNamespace(get_all=get_all, db=SimpleNamespace(sql=sql)),
    "_require_admin": lambda: None,
    "_sales_order_relations_batch": lambda names, docstatus_by_name: {
        name: {"delivery_notes": [], "sales_invoices": [], "pick_lists": [],
               "can_create_delivery": False, "can_create_pick_list": False}
        for name in names
    },
}
exec(compile(ast.Module(body=[function], type_ignores=[]), str(source), "exec"), namespace)
list_orders = namespace["list_sales_orders"]
result = list_orders(page=2)
assert result["page_count"] == 3 and result["has_prev"] and result["has_next"]
assert calls[-1][1]["limit_start"] == 20
assert calls[-1][1]["order_by"] == "transaction_date desc, creation desc, name desc"
result = list_orders(page=999, limit=10, sort="invalid", query="SKY", item_query="SH-PVC1.0")
assert result["page"] == 5 and not result["has_next"]
assert calls[-1][1]["limit_start"] == 40
assert calls[-1][1]["filters"]["name"] == ["in", ["SO-MATCH"]]
assert calls[-1][1]["or_filters"][0] == ["name", "like", "%SKY%"]
assert sql_calls[-1][1] == {"query": "%SH-PVC1.0%"}
assert "variant_of" in sql_calls[-1][0]
result = list_orders(page="bad", limit="bad", sort="amount_desc")
assert result["page"] == 1 and result["page_length"] == 20
assert calls[-1][1]["order_by"].startswith("grand_total desc")
print("mobile order pagination checks passed")

delivery_source = source.with_name("mobile_delivery.py")
delivery_tree = ast.parse(delivery_source.read_text(encoding="utf-8"))
pending_function = next(node for node in delivery_tree.body if isinstance(node, ast.FunctionDef) and node.name == "_pending_item")
pending_namespace = {"flt": lambda value: float(value or 0)}
exec(compile(ast.Module(body=[pending_function], type_ignores=[]), str(delivery_source), "exec"), pending_namespace)
pending = pending_namespace["_pending_item"]
assert pending({"qty": 4, "delivered_qty": 1, "uom": "箱", "conversion_factor": 12})["pending_qty"] == 3
assert pending({"qty": 4, "delivered_qty": 5})["pending_qty"] == 0
assert pending({"qty": 4, "delivered_qty": None})["pending_qty"] == 4
print("mobile pending delivery quantity checks passed")
