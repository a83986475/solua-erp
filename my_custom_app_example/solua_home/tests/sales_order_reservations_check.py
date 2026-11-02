"""Run with: python tests/sales_order_reservations_check.py"""

import ast
from pathlib import Path


source = Path(__file__).parents[1] / "solua_wholesale/report/sales_order_reservations/sales_order_reservations.py"
tree = ast.parse(source.read_text(encoding="utf-8"))
functions = [node for node in tree.body if isinstance(node, ast.FunctionDef) and node.name == "_calculate_reserved_qty"]
namespace = {"flt": lambda value: float(value or 0)}
exec(compile(ast.Module(body=functions, type_ignores=[]), str(source), "exec"), namespace)
calculate = namespace["_calculate_reserved_qty"]

assert calculate({"qty": 10, "stock_qty": 10, "delivered_qty": 2, "returned_qty": 3}, True) == 5
assert calculate({"qty": 10, "stock_qty": 10, "delivered_qty": 2, "returned_qty": 3}, False) == 8
assert calculate({"qty": 10, "stock_qty": 20, "delivered_qty": 10, "returned_qty": 0}, True) == 0
assert calculate({"qty": 10, "stock_qty": 10, "delivered_qty": 0, "returned_qty": 0, "delivered_by_supplier": 1}, True) == 0
print("sales_order_reservations_check: OK")
