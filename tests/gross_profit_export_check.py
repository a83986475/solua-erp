"""Run without a Bench environment: python tests/gross_profit_export_check.py."""

import ast
from pathlib import Path
from types import SimpleNamespace


source = Path(__file__).parents[1] / "api/gross_profit.py"
tree = ast.parse(source.read_text(encoding="utf-8"))
function = next(node for node in tree.body if isinstance(node, ast.FunctionDef) and node.name == "_export_with_gross_profit_rows")
namespace = {"run": object()}
exec(compile(ast.Module(body=[function], type_ignores=[]), str(source), "exec"), namespace)
export_with_rows = namespace["_export_with_gross_profit_rows"]


def capture_run(module):
    return lambda: module.run


native_run = object()
custom_run = object()
module = SimpleNamespace(run=native_run)
assert export_with_rows(capture_run(module), module, "Stock Balance") is native_run
assert module.run is native_run

namespace["run"] = custom_run
assert export_with_rows(capture_run(module), module, "Gross Profit") is custom_run
assert module.run is native_run

print("gross_profit_export_check: OK")
