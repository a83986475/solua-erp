"""Regression check for source Sales Order reservations in Pick List planning."""

import importlib.util
import sys
import types
from pathlib import Path


class Row(dict):
    __getattr__ = dict.get

    def __setattr__(self, key, value):
        self[key] = value


class PickList(Row):
    def append(self, fieldname, value):
        self.setdefault(fieldname, []).append(Row(value))

    def remove(self, row):
        self["locations"].remove(row)


class BasePickList:
    def set_item_locations(self, save=False):
        return None


fake_frappe = types.ModuleType("frappe")
fake_frappe.get_doc = lambda *args: None
fake_utils = types.ModuleType("frappe.utils")
fake_utils.flt = lambda value: float(value or 0)
fake_pick_list = types.ModuleType("erpnext.stock.doctype.pick_list.pick_list")
fake_pick_list.PickList = BasePickList
fake_bundle = types.ModuleType("erpnext.selling.doctype.product_bundle.product_bundle")
fake_bundle.get_active_product_bundle = lambda item_code: None
fake_item_details = types.ModuleType("erpnext.stock.get_item_details")
fake_stock_balance = types.ModuleType("erpnext.stock.stock_balance")

sys.modules.update({
    "frappe": fake_frappe,
    "frappe.utils": fake_utils,
    "erpnext.stock.doctype.pick_list.pick_list": fake_pick_list,
    "erpnext.selling.doctype.product_bundle.product_bundle": fake_bundle,
    "erpnext.stock.get_item_details": fake_item_details,
    "erpnext.stock.stock_balance": fake_stock_balance,
})

spec = importlib.util.spec_from_file_location(
    "pick_list_override",
    Path(__file__).resolve().parents[1] / "override" / "pick_list.py",
)
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)


order = Row(
    name="SO-1",
    docstatus=1,
    company="Company",
    items=[
        Row(name="SOI-09", item_code="SH151107-09", item_name="09", description="09",
            warehouse="Receiving", uom="条", stock_uom="条", conversion_factor=1,
            qty=10, picked_qty=0, delivered_qty=0, delivered_by_supplier=0),
        Row(name="SOI-13", item_code="SH151107-13", item_name="13", description="13",
            warehouse="Receiving", uom="条", stock_uom="条", conversion_factor=1,
            qty=4, picked_qty=0, delivered_qty=0, delivered_by_supplier=0),
    ],
)

bins = {
    "SH151107-09": {"actual_qty": 12},
    "SH151107-13": {"actual_qty": 4},
}
reserved = {"SH151107-09": 10, "SH151107-13": 4}
fake_frappe.get_doc = lambda doctype, name: order
fake_item_details.get_bin_details = lambda item_code, warehouse, company: bins[item_code]
fake_stock_balance.get_reserved_qty = lambda item_code, warehouse: reserved[item_code]

doc = PickList(
    purpose="Delivery",
    custom_sales_order="SO-1",
    parent_warehouse="Receiving",
    locations=[Row(
        item_code="SH151107-09", sales_order="SO-1", sales_order_item="SOI-09",
        product_bundle_item=None, qty=2, stock_qty=2, actual_qty=12, picked_qty=0,
    )],
)
module._reconcile_sales_order_locations(doc)

rows = {row.sales_order_item: row for row in doc.locations}
assert rows["SOI-09"].qty == 10 and rows["SOI-09"].stock_qty == 10
assert rows["SOI-13"].qty == 4 and rows["SOI-13"].stock_qty == 4

# A different order's reservation must still reduce the source order's plan.
reserved["SH151107-09"] = 16
module._reconcile_sales_order_locations(doc)
assert rows["SOI-09"].qty == 6 and rows["SOI-09"].stock_qty == 6

print("pick_list_reservation_check: ok")
