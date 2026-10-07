"""Focused, database-free checks for submitted receipt cost mirroring."""

import importlib
import json
from pathlib import Path
import sys
import types
from unittest.mock import Mock, patch


frappe = types.ModuleType("frappe")
frappe.utils = types.ModuleType("frappe.utils")
frappe.utils.flt = lambda value, precision=None: round(float(value or 0), precision) if precision is not None else float(value or 0)
frappe.utils.cint = lambda value: int(value or 0)
frappe.utils.getdate = lambda value: value
frappe.utils.nowdate = lambda: "2026-10-03"
frappe.throw = lambda message: (_ for _ in ()).throw(RuntimeError(message))
frappe.get_precision = lambda doctype, fieldname: 2
frappe._ = lambda message: message
frappe.db = types.SimpleNamespace(sql=Mock(), get_value=Mock(), set_value=Mock(), exists=Mock())
frappe.get_all = Mock()
frappe.get_doc = Mock()
frappe.whitelist = lambda **kwargs: lambda fn: fn
sys.modules["frappe"] = frappe
sys.modules["frappe.utils"] = frappe.utils
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
stock_api = types.ModuleType("solua_home.api.stock")
stock_api.validate_transaction_quantities = lambda *args, **kwargs: None
sys.modules["solua_home.api.stock"] = stock_api
sys.modules.pop("solua_home.receipt_cost_sync", None)
sync = importlib.import_module("solua_home.receipt_cost_sync")


class Doc(dict):
    __getattr__ = dict.__getitem__


def check_weighted_final_line_amount():
    # Amount includes line basic amount and distributed landed costs; 120 is the
    # existing FIFO stock valuation rate and must not be used for this new batch.
    frappe.get_all.return_value = [
        {"item_code": "ITEM-1", "stock_uom": "Each", "transfer_qty": 2, "amount": 250, "valuation_rate": 120},
        {"item_code": "ITEM-1", "stock_uom": "Each", "transfer_qty": 2, "amount": 250, "valuation_rate": 120},
    ]
    costs = sync._entry_costs(Doc({"purpose": "Material Receipt", "docstatus": 1, "name": "STE-1"}))
    assert costs[("ITEM-1", "Each")] == 125


def check_newest_time_key():
    common = {"posting_date": "2026-10-03", "creation": "2026-10-03 10:00:00", "name": "STE"}
    nine = sync._voucher_key({**common, "posting_time": "9:00:00"})
    ten = sync._voucher_key({**common, "posting_time": "10:00:00"})
    assert nine < ten


def check_only_newest_receipt_updates():
    item = types.SimpleNamespace(name="ITEM-1", stock_uom="Each")
    doc = Doc({"name": "STE-NEW", "company": "Solua Home", "docstatus": 1, "purpose": "Material Receipt",
           "posting_date": "2026-10-03", "posting_time": "10:00:00", "creation": "2026-10-03 10:00:00"})
    with patch.object(sync, "_entry_costs", return_value={("ITEM-1", "Each"): 125}), \
         patch.object(sync, "_lock_items"), patch.object(sync, "_company_currency", return_value="MZN"), \
         patch.object(sync, "_read_state", return_value=None), \
         patch.object(sync, "_latest_receipt", return_value={"name": "STE-FUTURE"}), \
         patch.object(sync, "_set_rate") as set_rate, patch.object(sync, "_write_state"):
        frappe.get_doc.return_value = item
        sync.on_submit(doc)
        set_rate.assert_not_called()


def check_write_errors_escape_for_transaction_rollback():
    item = types.SimpleNamespace(name="ITEM-1", stock_uom="Each")
    doc = Doc({"name": "STE-NEW", "company": "Solua Home", "docstatus": 1, "purpose": "Material Receipt",
           "posting_date": "2026-10-03", "posting_time": "10:00:00", "creation": "2026-10-03 10:00:00"})
    with patch.object(sync, "_entry_costs", return_value={("ITEM-1", "Each"): 125}), \
         patch.object(sync, "_lock_items"), patch.object(sync, "_company_currency", return_value="MZN"), \
         patch.object(sync, "_read_state", return_value=None), \
         patch.object(sync, "_latest_receipt", return_value={"name": "STE-NEW"}), \
         patch.object(sync, "_matching_prices", return_value=[]), \
         patch.object(sync, "_set_rate", side_effect=RuntimeError("price save failed")):
        frappe.get_doc.return_value = item
        try:
            sync.on_submit(doc)
        except RuntimeError as exc:
            assert str(exc) == "price save failed"
        else:
            raise AssertionError("price write failure was swallowed")


def check_state_uses_database_price_precision():
    item = types.SimpleNamespace(name="ITEM-1", stock_uom="Each")
    price = types.SimpleNamespace(name="PRICE-1", valid_from=None, valid_upto=None)
    doc = Doc({"name": "STE-NEW", "company": "Solua Home", "docstatus": 1, "purpose": "Material Receipt",
           "posting_date": "2026-10-03", "posting_time": "10:00:00", "creation": "2026-10-03 10:00:00"})
    state_write = Mock()
    with patch.object(sync, "_entry_costs", return_value={("ITEM-1", "Each"): 10 / 3}), \
         patch.object(sync, "_lock_items"), patch.object(sync, "_company_currency", return_value="MZN"), \
         patch.object(sync, "_read_state", return_value=None), \
         patch.object(sync, "_latest_receipt", return_value={"name": "STE-NEW"}), \
         patch.object(sync, "_matching_prices", return_value=[]), \
         patch.object(sync, "_set_rate", return_value=(price, True)), \
         patch.object(sync, "_write_state", state_write):
        frappe.get_doc.return_value = item
        frappe.db.get_value.return_value = 3.333333333
        sync.on_submit(doc)
    saved = state_write.call_args.args[1]
    assert saved["applied_rate"] == 3.333333333
    assert saved["managed_dates"] == {"valid_from": "", "valid_upto": ""}


def check_expired_managed_price_is_not_reused():
    item = types.SimpleNamespace(name="ITEM-1", stock_uom="Each")
    old_price = types.SimpleNamespace(name="PRICE-OLD", item_code="ITEM-1", price_list="Standard Buying",
        uom="Each", currency="MZN", buying=1, selling=0, supplier=None, customer=None,
        price_list_rate=100, valid_from=None, valid_upto="2026-10-02")
    new_price = types.SimpleNamespace(name="PRICE-NEW", valid_from=None, valid_upto=None)
    state = {"version": 1, "baseline": {"exists": False}, "item_price": "PRICE-OLD", "created": True,
        "applied_rate": 100, "managed_dates": {"valid_from": "", "valid_upto": "2026-10-02"},
        "latest_voucher": "STE-OLD", "latest_key": ["2026-10-02", 10, 0, 0, 0, "", "STE-OLD"]}
    doc = Doc({"name": "STE-NEW", "company": "Solua Home", "docstatus": 1, "purpose": "Material Receipt",
        "posting_date": "2026-10-03", "posting_time": "10:00:00", "creation": "2026-10-03 10:00:00"})
    item_price_state = {}
    with patch.object(sync, "_entry_costs", return_value={("ITEM-1", "Each"): 125}), \
         patch.object(sync, "_lock_items"), patch.object(sync, "_company_currency", return_value="MZN"), \
         patch.object(sync, "_read_state", return_value=state), \
         patch.object(sync, "_latest_receipt", return_value={"name": "STE-NEW"}), \
         patch.object(sync, "_matching_prices", return_value=[]), \
         patch.object(sync, "_set_rate", return_value=(new_price, True)) as set_rate, \
         patch.object(sync, "_write_state", side_effect=lambda code, value: item_price_state.update(value)):
        frappe.get_doc.side_effect = [item, old_price]
        frappe.db.exists.return_value = True
        frappe.db.get_value.return_value = 125
        sync.on_submit(doc)
    assert set_rate.call_args.args[0] is None
    assert item_price_state["item_price"] == "PRICE-NEW"


def check_cancel_restores_previous_batch():
    item = types.SimpleNamespace(name="ITEM-1", stock_uom="Each")
    price = types.SimpleNamespace(name="PRICE-1", item_code="ITEM-1", price_list="Standard Buying", uom="Each",
        currency="MZN", buying=1, selling=0, supplier=None, customer=None, price_list_rate=125,
        valid_from=None, valid_upto=None, save=Mock(), delete=Mock())
    state = {"version": 1, "baseline": {"exists": True, "rate": 90}, "item_price": "PRICE-1", "created": False,
             "applied_rate": 125, "managed_dates": {"valid_from": "", "valid_upto": ""},
             "latest_voucher": "STE-2", "latest_key": ["2026-10-03", 10, 0, 0, 0, "", "STE-2"]}
    doc = Doc({"name": "STE-2", "purpose": "Material Receipt"})
    with patch.object(sync, "_entry_costs_for_cancel", return_value={("ITEM-1", "Each")}), \
         patch.object(sync, "_lock_items"), patch.object(sync, "_read_state", return_value=state), \
         patch.object(sync, "_latest_receipt", return_value={"name": "STE-1", "rate": 100,
             "key": ["2026-10-03", 9, 0, 0, 0, "", "STE-1"]}):
        frappe.get_doc.side_effect = [item, price]
        frappe.db.get_value.return_value = 100
        frappe.db.exists.return_value = True
        sync.on_cancel(doc)
    assert price.price_list_rate == 100
    price.save.assert_called_once_with(ignore_permissions=True)
    assert json.loads(frappe.db.set_value.call_args.args[3])["latest_voucher"] == "STE-1"


def run_cancel_case(state, price, voucher="STE-2"):
    item = types.SimpleNamespace(name="ITEM-1", stock_uom="Each")
    doc = Doc({"name": voucher, "purpose": "Material Receipt"})
    with patch.object(sync, "_entry_costs_for_cancel", return_value={("ITEM-1", "Each")}), \
         patch.object(sync, "_lock_items"), patch.object(sync, "_read_state", return_value=state), \
         patch.object(sync, "_latest_receipt", return_value=None):
        frappe.get_doc.side_effect = [item, price] if state and state.get("latest_voucher") == voucher else [item]
        frappe.db.exists.return_value = True
        frappe.db.set_value.reset_mock()
        sync.on_cancel(doc)


def check_cancel_restores_initial_baseline():
    item_price = types.SimpleNamespace(name="PRICE-1", item_code="ITEM-1", price_list="Standard Buying",
        uom="Each", currency="MZN", buying=1, selling=0, supplier=None, customer=None,
        price_list_rate=125, valid_from=None, valid_upto=None, save=Mock(), delete=Mock())
    state = {"version": 1, "baseline": {"exists": True, "rate": 90}, "item_price": "PRICE-1", "created": False,
        "applied_rate": 125, "managed_dates": {"valid_from": "", "valid_upto": ""}, "latest_voucher": "STE-2"}
    run_cancel_case(state, item_price)
    assert item_price.price_list_rate == 90
    item_price.save.assert_called_once_with(ignore_permissions=True)


def check_cancel_deletes_only_managed_created_price():
    created = types.SimpleNamespace(name="PRICE-NEW", item_code="ITEM-1", price_list="Standard Buying",
        uom="Each", currency="MZN", buying=1, selling=0, supplier=None, customer=None,
        price_list_rate=125, valid_from=None, valid_upto=None, save=Mock(), delete=Mock())
    generic = Mock()
    state = {"version": 1, "baseline": {"exists": False}, "item_price": "PRICE-NEW", "created": True,
        "applied_rate": 125, "managed_dates": {"valid_from": "", "valid_upto": ""}, "latest_voucher": "STE-2"}
    run_cancel_case(state, created)
    created.delete.assert_called_once_with(ignore_permissions=True)
    generic.delete.assert_not_called()


def check_cancel_preserves_manual_price_or_dates():
    cases = [(125, {"price_list_rate": 150}, 125),
             (3.333333333, {"price_list_rate": 3.333333334}, 3.333333333),
             (125, {"valid_upto": "2026-12-31"}, 125)]
    for original_rate, manual_change, applied_rate in cases:
        price = types.SimpleNamespace(name="PRICE-1", item_code="ITEM-1", price_list="Standard Buying",
            uom="Each", currency="MZN", buying=1, selling=0, supplier=None, customer=None,
            price_list_rate=original_rate, valid_from=None, valid_upto=None, save=Mock(), delete=Mock())
        for key, value in manual_change.items():
            setattr(price, key, value)
        state = {"version": 1, "baseline": {"exists": True, "rate": 90}, "item_price": "PRICE-1",
            "created": False, "applied_rate": applied_rate, "managed_dates": {"valid_from": "", "valid_upto": ""},
            "latest_voucher": "STE-2"}
        run_cancel_case(state, price)
        price.save.assert_not_called()
        price.delete.assert_not_called()


def check_cancel_nonlatest_receipt_does_not_change_price():
    price = Mock()
    state = {"version": 1, "item_price": "PRICE-1", "latest_voucher": "STE-3"}
    run_cancel_case(state, price)
    price.save.assert_not_called()
    price.delete.assert_not_called()
    frappe.db.set_value.assert_not_called()


def check_reference_selection_and_price_floor():
    from solua_home.api import sales

    def row(rate, uom="Each", valid_from=None, valid_upto=None, supplier=None, customer=None, modified="2026-10-03"):
        return types.SimpleNamespace(name=f"P-{rate}-{uom}", item_code="ITEM-1", price_list="Standard Buying",
            price_list_rate=rate, valid_from=valid_from, valid_upto=valid_upto, buying=1, selling=0,
            uom=uom, currency="MZN", supplier=supplier, customer=customer, modified=modified)

    def call_with(rows, entered):
        frappe.db.get_value.side_effect = lambda dt, name, field: (
            "Each" if dt == "Item" and field == "stock_uom" else
            "Item One" if dt == "Item" and field == "item_name" else
            200 if dt == "Item" and field == "valuation_rate" else
            "MZN" if dt == "Price List" and field == "currency" else None)
        frappe.get_all.return_value = rows
        frappe.db.sql.return_value = [{"cost": 200}]
        return sales.check_price_above_cost("ITEM-1", entered)

    assert call_with([row(220)], 210)["cost"] == 220 and not call_with([row(220)], 210)["ok"]
    assert call_with([row(220)], 220)["ok"]
    assert call_with([row(180)], 190)["ok"]
    assert call_with([row(250, uom=""), row(220)], 210)["cost"] == 220
    assert call_with([row(210, uom="")], 210)["ok"]
    assert call_with([row(300, valid_from="2026-10-04")], 210)["ok"]
    assert call_with([row(300, valid_upto="2026-10-02")], 210)["ok"]
    assert call_with([row(300, supplier="SUP-1")], 210)["ok"]
    assert call_with([], 190)["cost"] == 200 and not call_with([], 190)["ok"]


check_weighted_final_line_amount()
check_newest_time_key()
check_only_newest_receipt_updates()
check_write_errors_escape_for_transaction_rollback()
check_state_uses_database_price_precision()
check_expired_managed_price_is_not_reused()
check_cancel_restores_previous_batch()
check_cancel_restores_initial_baseline()
check_cancel_deletes_only_managed_created_price()
check_cancel_preserves_manual_price_or_dates()
check_cancel_nonlatest_receipt_does_not_change_price()
check_reference_selection_and_price_floor()
print("receipt cost sync checks passed")
