"""Run without Bench: guards, preview, confirmation freshness and save behavior."""

import copy
import importlib.util
import sys
import types
import unittest
from pathlib import Path
from unittest.mock import Mock, patch


class Doc(dict):
    def __getattr__(self, key):
        return self.get(key)

    def __setattr__(self, key, value):
        self[key] = value

    def set(self, key, value):
        self[key] = value

    def as_dict(self):
        return copy.deepcopy(dict(self))

    def check_permission(self, permission):
        if permission in (self.get("denied") or []):
            raise PermissionError(permission)

    def save(self):
        self["saved"] = True


def fail(message):
    raise ValueError(message)


frappe = types.ModuleType("frappe")
frappe._ = lambda value: value
frappe.whitelist = lambda **kwargs: lambda fn: fn
frappe.throw = fail
frappe.db = types.SimpleNamespace(exists=Mock(return_value=False))
utils = types.ModuleType("frappe.utils")
utils.flt = lambda value: float(value or 0)
sales = types.ModuleType("erpnext.selling.doctype.sales_order.sales_order")
parent = types.ModuleType("erpnext.selling.doctype.sales_order")
parent.sales_order = sales
stock = types.ModuleType("solua_home.api.stock")
stock._pick_list_order_comparison = Mock(return_value={"rows": []})
modules = {"frappe": frappe, "frappe.utils": utils,
           "erpnext.selling.doctype.sales_order": parent, "solua_home.api.stock": stock}
spec = importlib.util.spec_from_file_location("pick_update", Path(__file__).resolve().parents[1] / "api/pick_list_update.py")
api = importlib.util.module_from_spec(spec)
with patch.dict(sys.modules, modules):
    spec.loader.exec_module(api)


class UpdateTests(unittest.TestCase):
    def setUp(self):
        self.row = Doc(name="old-row", item_code="BLACK", item_name="Black rod", sales_order="SO-1",
                       sales_order_item="SOI-1", qty=2, stock_qty=24, conversion_factor=12,
                       warehouse="Receiving", uom="Box", stock_uom="Piece", picked_qty=0)
        self.doc = Doc(name="PICK-1", docstatus=0, purpose="Delivery", modified="v1",
                       custom_pick_result="待拣货", custom_sales_order="SO-1", locations=[self.row],
                       company="Company", customer="Customer")
        self.order = Doc(name="SO-1", docstatus=1, status="To Deliver and Bill", modified="o1",
                         company="Company", customer="Customer")
        self.after = [Doc(self.row, qty=1, stock_qty=12),
                      Doc(self.row, name="new-row", item_code="SILVER", sales_order_item="SOI-2", qty=2)]

        def mapper(source, target_doc):
            self.assertEqual(source, "SO-1")
            self.assertEqual(target_doc.name, "PICK-1", "exclude this draft's stock from allocations")
            self.assertEqual(target_doc.locations, [], "do not append duplicate rows")
            self.assertEqual(target_doc.pick_manually, 0)
            target_doc.locations = copy.deepcopy(self.after)
            return target_doc

        sales.create_pick_list = mapper
        self.get_doc = Mock(side_effect=lambda *args, **kwargs: (
            Doc(copy.deepcopy(args[0])) if isinstance(args[0], dict)
            else self.doc if args[0] == "Pick List" else self.order
        ))
        frappe.get_doc = self.get_doc
        frappe.db.exists.reset_mock(return_value=True, side_effect=True)
        frappe.db.exists.return_value = False
        stock._pick_list_order_comparison.return_value = {"rows": []}
        self.module_patch = patch.dict(sys.modules, modules)
        self.module_patch.start()
        self.addCleanup(self.module_patch.stop)

    def test_preview_is_read_only_and_shows_stock_uom(self):
        result = api.preview("PICK-1")
        self.assertEqual([r["action"] for r in result["changes"]], ["调整", "新增"])
        self.assertEqual(result["changes"][0]["after_stock_qty"], 12)
        self.assertEqual(self.doc.locations, [self.row])
        self.assertFalse(self.doc.saved)

    def test_confirmation_saves_existing_draft_only(self):
        result = api.apply("PICK-1", api.preview("PICK-1")["token"])
        self.assertTrue(self.doc.saved)
        self.assertEqual(result, {"name": "PICK-1", "docstatus": 0, "updated": True})
        self.assertEqual(len(self.doc.locations), 2)
        self.assertEqual(self.doc.locations[1]["sales_order_item"], "SOI-2")
        self.assertIn(unittest.mock.call("Pick List", "PICK-1", for_update=True), self.get_doc.call_args_list)
        self.assertIn(unittest.mock.call("Sales Order", "SO-1", for_update=True), self.get_doc.call_args_list)

    def test_changed_order_pick_or_inventory_invalidates_confirmation(self):
        for target, field, value in [(self.order, "modified", "o2"), (self.doc, "modified", "v2"),
                                     (self.after[0], "warehouse", "Other")]:
            with self.subTest(field=field):
                token = api.preview("PICK-1")["token"]
                original = target[field]
                target[field] = value
                with self.assertRaisesRegex(ValueError, "已变化"):
                    api.apply("PICK-1", token)
                self.assertFalse(self.doc.saved)
                target[field] = original

    def test_all_guards_and_permissions(self):
        for target, field, value in [
            (self.doc, "docstatus", 1), (self.doc, "purpose", "Material Transfer"),
            (self.doc, "custom_pick_result", "缺货待补"), (self.row, "picked_qty", 1),
            (self.row, "picked_qty", -1), (self.row, "delivered_qty", 1),
            (self.row, "stock_reserved_qty", 1), (self.row, "batch_no", "Batch"),
            (self.row, "serial_no", "Serial"), (self.row, "serial_and_batch_bundle", "Bundle"),
            (self.row, "sales_order_item", ""), (self.row, "sales_order", "SO-2"),
            (self.order, "docstatus", 0), (self.order, "status", "Closed"),
            (self.order, "company", "Other"), (self.order, "customer", "Other"),
            (self.doc, "denied", ["write"]), (self.order, "denied", ["read"]),
        ]:
            with self.subTest(field=field, value=value):
                original = target.get(field)
                target[field] = value
                with self.assertRaises((ValueError, PermissionError)):
                    api.preview("PICK-1")
                target[field] = original
                self.assertFalse(self.doc.saved)

    def test_downstream_documents_block_update(self):
        for doctype in ("Delivery Note Item", "Sales Invoice Item", "Stock Reservation Entry"):
            frappe.db.exists.side_effect = lambda dt, filters: dt == doctype
            with self.assertRaises(ValueError):
                api.preview("PICK-1")

    def test_missing_confirmation_and_empty_result_do_not_save(self):
        with self.assertRaises(ValueError):
            api.apply("PICK-1", "")
        self.after = []
        with self.assertRaisesRegex(ValueError, "没有可生成"):
            api.preview("PICK-1")
        self.assertFalse(self.doc.saved)

    def test_unchanged_does_not_write_and_shortage_is_visible(self):
        self.after = [Doc(self.row)]
        stock._pick_list_order_comparison.return_value = {"rows": [
            {"item_code": "SILVER", "order_qty": 24, "planned_qty": 0, "stock_uom": "Piece"}
        ]}
        result = api.preview("PICK-1")
        self.assertFalse(result["changed"])
        self.assertEqual(result["unplanned"][0]["planned_qty"], 0)
        self.assertFalse(api.apply("PICK-1", result["token"])["updated"])
        self.assertFalse(self.doc.saved)

    def test_removal_and_rebinding_are_visible(self):
        before = api._rows(self.doc)
        self.doc.locations = [Doc(self.row, sales_order_item="replacement", qty=1, stock_qty=12)]
        changes = api._changes(before, api._rows(self.doc))
        self.assertEqual([r["action"] for r in changes], ["移除", "新增"])


if __name__ == "__main__":
    unittest.main()
