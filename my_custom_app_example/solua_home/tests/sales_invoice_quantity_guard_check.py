"""Small no-site regression check for cross-source Sales Invoice overbilling."""

import importlib.util
import sys
import types
from pathlib import Path


class Dict(dict):
    __getattr__ = dict.get
    __setattr__ = dict.__setitem__


frappe = types.ModuleType("frappe")
frappe._ = lambda value: value
frappe.whitelist = lambda fn=None, **_kwargs: fn if fn else (lambda wrapped: wrapped)
frappe_utils = types.ModuleType("frappe.utils")
frappe_utils.cint = lambda value: int(value or 0)
frappe_utils.flt = lambda value: float(value or 0)
frappe.throw = lambda message: (_ for _ in ()).throw(ValueError(str(message)))
sys.modules["frappe"] = frappe
sys.modules["frappe.utils"] = frappe_utils

stock_api = types.ModuleType("solua_home.api.stock")
stock_api.validate_transaction_quantities = lambda _doc: None
sys.modules["solua_home.api.stock"] = stock_api


class DB:
    def sql(self, query, _params, as_dict=False):
        if "tabSales Order Item" in query:
            return [Dict(name="SO-1", stock_qty=10, qty=10)]
        if "tabDelivery Note Item" in query:
            return [Dict(name="DN-1", stock_qty=10, qty=10)]
        return [Dict(so_detail="SO-1", dn_detail=None, stock_qty=6, qty=6, is_return=0)]


frappe.db = DB()
spec = importlib.util.spec_from_file_location(
    "sales", Path(__file__).resolve().parents[1] / "api/sales.py"
)
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)

duplicate = Dict(
    name="NEW-SI",
    company="Co",
    docstatus=0,
    items=[Dict(so_detail="SO-1", dn_detail="DN-1", stock_qty=6, qty=6)],
)
try:
    module._validate_invoice_source_quantities(duplicate)
except ValueError as error:
    assert "累计开票数量超过可开票数量" in str(error)
else:
    raise AssertionError("cross-source duplicate invoice was not blocked")

partial = Dict(
    name="NEW-SI",
    company="Co",
    docstatus=0,
    items=[Dict(so_detail="SO-1", dn_detail="DN-1", stock_qty=4, qty=4)],
)
module._validate_invoice_source_quantities(partial)

assert module._invoice_source_overages(
    [Dict(so_detail="SO-1", dn_detail="DN-1", stock_qty=5, qty=5)],
    [Dict(dn_detail="DN-1", stock_qty=6, qty=6, is_return=0)],
    {("so", "SO-1"): 10, ("dn", "DN-1"): 10},
) == {("dn", "DN-1"): 1.0}
print("PASS: Sales Order and Delivery Note invoices share one quantity guard")
