"""Run without a Bench environment: python tests/template_stock_tree_check.py."""
import ast
import json
from pathlib import Path

source = Path(__file__).parents[1] / "solua_wholesale/report/template_stock_tree/template_stock_tree.py"
tree = ast.parse(source.read_text(encoding="utf-8"))
functions = [node for node in tree.body if isinstance(node, ast.FunctionDef) and node.name in {"_filter_items", "_report_values", "group_rows"}]
namespace = {"json": json, "flt": float}
namespace["cint"] = int
exec(compile(ast.Module(body=functions, type_ignores=[]), str(source), "exec"), namespace)
items = {
    "TPL": dict(name="TPL", item_name="Template", has_variants=1, stock_uom="条"),
    "RED": dict(name="RED", item_name="Red", variant_of="TPL", stock_uom="条"),
    "BLUE": dict(name="BLUE", item_name="Blue", variant_of="TPL", stock_uom="条"),
}
assert set(namespace["_filter_items"](items, True)) == {"TPL", "RED", "BLUE"}
assert "SH151060-LEGACY" not in namespace["_filter_items"]({"SH151060-LEGACY": {}}, True)
assert "SH151060-LEGACY" in namespace["_filter_items"]({"SH151060-LEGACY": {}}, False)
bins = [dict(item_code="RED", warehouse="A", actual_qty=20, reserved_qty=6),
        dict(item_code="BLUE", warehouse="A", actual_qty=34, reserved_qty=0),
        dict(item_code="RED", warehouse="B", actual_qty=2, reserved_qty=3)]
rows = namespace["group_rows"](items, bins)
assert len(rows) == 3
assert (rows[0]["actual_qty"], rows[0]["reserved_qty"], rows[0]["available_qty"]) == (56, 9, 47)
opening_rows = namespace["group_rows"](items, bins, opening_quantities={"RED": 20, "BLUE": 34})
assert next(row for row in opening_rows if row["item_code"] == "TPL")["opening_qty"] == 54
assert next(row for row in opening_rows if row["item_code"] == "RED")["opening_qty"] == 20
sales_rows = namespace["group_rows"](items, bins, opening_quantities={"RED": 20, "BLUE": 34}, sold_quantities={"RED": 4, "BLUE": 12})
assert next(row for row in sales_rows if row["item_code"] == "TPL")["sold_qty"] == 16
assert next(row for row in sales_rows if row["item_code"] == "RED")["sold_qty"] == 4
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
rod_items = {
    "ROD": dict(name="ROD", item_name="Curtain rod", has_variants=1, stock_uom="根",
                report_uom="箱/Caixa", report_factor=12),
    "ROD-1": dict(name="ROD-1", item_name="Curtain rod / Red", variant_of="ROD",
                  stock_uom="根", report_uom="箱/Caixa", report_factor=12),
}
rod_rows = namespace["group_rows"](rod_items, [dict(item_code="ROD-1", warehouse="A", actual_qty=24, reserved_qty=12)])
rod_parent = next(row for row in rod_rows if row["item_code"] == "ROD")
rod_child = next(row for row in rod_rows if row["item_code"] == "ROD-1")
assert rod_parent["stock_uom"] == rod_child["stock_uom"] == "箱/Caixa"
assert (rod_parent["actual_qty"], rod_parent["reserved_qty"], rod_parent["available_qty"]) == (2, 1, 1)
assert (rod_child["actual_qty"], rod_child["reserved_qty"], rod_child["available_qty"]) == (2, 1, 1)
pvc_items = {
    "PVC": dict(name="PVC", item_name="PVC", has_variants=1, stock_uom="Nos", report_uom="卷", report_factor=1),
    "PVC-1": dict(name="PVC-1", item_name="PVC / 048", variant_of="PVC", stock_uom="Nos", report_uom="卷", report_factor=1),
}
pvc_rows = namespace["group_rows"](pvc_items, [dict(item_code="PVC-1", warehouse="A", actual_qty=25, reserved_qty=4)])
pvc_child = next(row for row in pvc_rows if row["item_code"] == "PVC-1")
assert pvc_child["stock_uom"] == "卷"
assert (pvc_child["actual_qty"], pvc_child["reserved_qty"], pvc_child["available_qty"]) == (25, 4, 21)
print("template_stock_tree_check: OK")
