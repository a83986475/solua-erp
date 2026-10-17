"""No-site checks for the three safe return states."""
import importlib.util
import sys
import types
from pathlib import Path

frappe = types.ModuleType("frappe")
frappe.whitelist = frappe.read_only = lambda: (lambda fn: fn)
sys.modules["frappe"] = frappe
utils = types.ModuleType("frappe.utils")
utils.flt = lambda value, *args: float(value or 0)
utils.date_diff = lambda *args: 0
utils.nowdate = lambda: "2026-10-12"
sys.modules["frappe.utils"] = utils
home = types.ModuleType("solua_home.api.home")
home._can_read = home._can_create = lambda dt: True
home._list = lambda *args, **kwargs: []
sys.modules["solua_home.api.home"] = home
unbilled = types.ModuleType("solua_home.api.unbilled")
unbilled.billing_module = lambda: None
sys.modules["solua_home.api.unbilled"] = unbilled
spec = importlib.util.spec_from_file_location(
    "return_reconciliation",
    Path(__file__).resolve().parents[1] / "api/return_reconciliation.py",
)
m = importlib.util.module_from_spec(spec)
spec.loader.exec_module(m)

base_return = {"item_code": "SH151077", "qty": -24, "sales_order": "SO-1", "so_detail": "SO-ROW"}
exact_invoice = [{"invoice": "SI-1", "item_code": "SH151077", "qty": 24, "sales_order": "SO-1", "so_detail": "SO-ROW", "is_return": 0}]
assert m.classify_return_lines([base_return], exact_invoice)["state"] == "已开票待贷项"
assert m.classify_return_lines([base_return], [])["state"] == "未开票无需贷项"
assert m.classify_return_lines([base_return], [{**exact_invoice[0], "so_detail": "OTHER-ROW"}])["state"] == "明细不一致"
assert m.classify_return_lines([base_return], exact_invoice, [{"invoice": "SI-1", "item_code": "SH151077", "qty": -24, "so_detail": "SO-ROW"}])["state"] == "明细不一致"
assert m.classify_return_lines([{**base_return, "qty": -5, "original_qty": 50}], [{**exact_invoice[0], "qty": 45}])["state"] == "原发票数量已覆盖"
print("PASS: exact billed, unbilled, mismatched detail and already credited returns")
