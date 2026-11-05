"""Small source-level regression checks for active Pick List routing."""

import ast
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
STOCK_SOURCE = (ROOT / "api" / "stock.py").read_text(encoding="utf-8")


def load_remaining_qty():
    tree = ast.parse(STOCK_SOURCE)
    node = next(
        item for item in tree.body
        if isinstance(item, ast.FunctionDef) and item.name == "_pick_list_remaining_qty"
    )
    namespace = {
        "flt": lambda value: float(value or 0),
        "_row_value": lambda row, fieldname, default=None: row.get(fieldname, default),
        "max": max,
    }
    exec(compile(ast.Module(body=[node], type_ignores=[]), str(ROOT / "api" / "stock.py"), "exec"), namespace)
    return namespace["_pick_list_remaining_qty"]


remaining_qty = load_remaining_qty()
assert remaining_qty({"stock_qty": 2, "picked_qty": 0, "delivered_qty": 0}) == 2
assert remaining_qty({"stock_qty": 2, "picked_qty": 2, "delivered_qty": 1}) == 1
assert remaining_qty({"stock_qty": 2, "picked_qty": 2, "delivered_qty": 2}) == 0
assert "p.docstatus<2" in STOCK_SOURCE
assert "COALESCE(p.status, '') NOT IN ('Completed', 'Cancelled')" in STOCK_SOURCE
assert "get_active_pick_lists_for_sales_order" in STOCK_SOURCE
print("PASS: active Pick List remaining quantity and status gates")
