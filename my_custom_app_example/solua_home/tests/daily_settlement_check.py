"""Small check for signed POS returns and daily net sales."""
import importlib.util
import sys
import types
from pathlib import Path


class Row(dict):
    __getattr__ = dict.get


frappe = types.ModuleType("frappe")
frappe._ = lambda value: value
frappe.utils = types.ModuleType("frappe.utils")
frappe.utils.getdate = lambda value: value
frappe.utils.nowdate = lambda: "2026-10-10"
frappe.db = types.SimpleNamespace()
queries = []


def sql(query, *args, **kwargs):
    queries.append(query)
    if "FROM `tabSales Invoice` si" in query:
        return [Row(cashier="cashier@example.com", invoice_count=2, total_sales=100, return_count=1, return_amount=20)]
    return []


frappe.db.sql = sql
frappe.get_all = lambda *args, **kwargs: []
sys.modules["frappe"] = frappe
sys.modules["frappe.utils"] = frappe.utils

root = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("daily_settlement", root / "report/daily_settlement/daily_settlement.py")
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)
data = module.get_data({"report_date": "2026-10-10"})
assert "SUM(CASE WHEN si.is_return = 0 THEN si.grand_total ELSE 0 END)" in queries[0]
assert "SUM(CASE WHEN si.is_return = 1 THEN ABS(si.grand_total) ELSE 0 END)" in queries[0]
assert data[0]["net_sales"] == 80
assert data[-1]["net_sales"] == 80
assert module.get_columns()[0]["label"] == "收银员"
assert module.get_columns()[2]["label"] == "销售原额"
assert module.get_columns()[5]["label"] == "销售净额"
print("PASS: daily settlement treats return invoices as positive deductions and reports net sales")
