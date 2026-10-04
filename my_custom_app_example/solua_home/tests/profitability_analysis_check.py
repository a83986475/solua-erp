"""Run with: python tests/profitability_analysis_check.py"""

import ast
from pathlib import Path


source = Path(__file__).parents[1] / "solua_wholesale/report/profitability_analysis/profitability_analysis.py"
tree = ast.parse(source.read_text(encoding="utf-8"))
functions = [
	node for node in tree.body
	if isinstance(node, ast.FunctionDef) and node.name == "is_opening_stock_receipt_adjustment"
]
namespace = {"cstr": lambda value: str(value or "")}
exec(compile(ast.Module(body=functions, type_ignores=[]), str(source), "exec"), namespace)
exclude = namespace["is_opening_stock_receipt_adjustment"]

assert exclude("Stock Adjustment", "Stock Entry", "Material Receipt")
assert exclude(" Stock Adjustment ", "Stock Entry", "Material Receipt")
assert not exclude("Stock Adjustment", "Stock Entry", "Material Issue")
assert not exclude("Stock Adjustment", "Delivery Note", "Material Receipt")
assert not exclude("Cost of Goods Sold", "Stock Entry", "Material Receipt")
print("profitability_analysis_check: OK")
