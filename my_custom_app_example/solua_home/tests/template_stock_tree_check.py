"""Run without a Bench environment: python tests/template_stock_tree_check.py."""
import ast
import json
from pathlib import Path

source = Path(__file__).parents[1] / "solua_wholesale/report/template_stock_tree/template_stock_tree.py"
tree = ast.parse(source.read_text(encoding="utf-8"))
function = next(node for node in tree.body if isinstance(node, ast.FunctionDef) and node.name == "group_rows")
namespace = {"json": json, "flt": float}
exec(compile(ast.Module(body=[function], type_ignores=[]), str(source), "exec"), namespace)
items = {
    "TPL": dict(name="TPL", item_name="Template", has_variants=1, stock_uom="条"),
    "RED": dict(name="RED", item_name="Red", variant_of="TPL", stock_uom="条"),
    "BLUE": dict(name="BLUE", item_name="Blue", variant_of="TPL", stock_uom="条"),
}
bins = [dict(item_code="RED", warehouse="A", actual_qty=20, reserved_qty=6),
        dict(item_code="BLUE", warehouse="A", actual_qty=34, reserved_qty=0),
        dict(item_code="RED", warehouse="B", actual_qty=2, reserved_qty=3)]
rows = namespace["group_rows"](items, bins)
assert len(rows) == 3
assert (rows[0]["actual_qty"], rows[0]["reserved_qty"], rows[0]["available_qty"]) == (56, 9, 47)
assert rows[1]["parent_id"] == rows[0]["node_id"] and rows[1]["indent"] == 1
assert namespace["group_rows"](items, [bins[2]])[2]["available_qty"] == -1
assert len({row["node_id"] for row in rows}) == len(rows)
assert namespace["group_rows"]({"RED": items["RED"]}, bins) == []
items["BLUE"]["stock_uom"] = "箱"
assert len([r for r in namespace["group_rows"](items, bins) if r["indent"] == 0]) == 2
items["BLUE"]["stock_uom"] = "条"
items["PLAIN"] = dict(name="PLAIN", item_name="Ordinary", stock_uom="条")
items["EMPTY"] = dict(name="EMPTY", item_name="Empty template", stock_uom="条", has_variants=1)
rows = namespace["group_rows"](items, [])
assert {r["item_code"] for r in rows if r["indent"] == 0} == {"TPL", "PLAIN", "EMPTY"}
assert all(r["actual_qty"] == r["reserved_qty"] == r["available_qty"] == 0 for r in rows)
plain = namespace["group_rows"](items, [dict(item_code="PLAIN", warehouse="A", actual_qty=5, reserved_qty=1),
                                         dict(item_code="PLAIN", warehouse="B", actual_qty=7, reserved_qty=2)])
assert next(r for r in plain if r["item_code"] == "PLAIN")["available_qty"] == 9
print("template_stock_tree_check: OK")
