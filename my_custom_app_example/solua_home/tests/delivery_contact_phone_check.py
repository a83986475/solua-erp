"""Check Delivery Note store-phone synchronization without a Frappe site."""
import importlib.util
import sys
import types
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


class Row(dict):
    __getattr__ = dict.get
    __setattr__ = dict.__setitem__


class Contact(Row):
    def append(self, fieldname, values):
        row = Row(values)
        self.setdefault(fieldname, []).append(row)
        return row

    def save(self):
        self["save_calls"] = self.get("save_calls", 0) + 1


frappe = types.ModuleType("frappe")
frappe._ = lambda value: value
frappe.whitelist = lambda *args, **kwargs: lambda fn: fn
frappe.get_doc = lambda doctype, name: contact
frappe_utils = types.ModuleType("frappe.utils")
frappe_utils.cint = lambda value: int(value or 0)
frappe_utils.flt = lambda value: float(value or 0)
sys.modules["frappe"] = frappe
sys.modules["frappe.utils"] = frappe_utils

spec = importlib.util.spec_from_file_location("stock_candidate", ROOT / "api" / "stock.py")
stock = importlib.util.module_from_spec(spec)
spec.loader.exec_module(stock)

contact = Contact(
    links=[Row(link_doctype="Customer", link_name="CUSTOMER-1")],
    phone_nos=[
        Row(phone="OLD-MOBILE", is_primary_mobile_no=1),
        Row(phone="LANDLINE", is_primary_phone=1),
    ],
)
stock.sync_delivery_contact_phone(Row(
    docstatus=0,
    customer="CUSTOMER-1",
    contact_person="CONTACT-1",
    custom_store_phone="860566888",
))
assert contact.save_calls == 1
assert next(row for row in contact.phone_nos if row.phone == "860566888").is_primary_mobile_no == 1
assert not next(row for row in contact.phone_nos if row.phone == "OLD-MOBILE").is_primary_mobile_no
assert next(row for row in contact.phone_nos if row.phone == "LANDLINE").is_primary_phone == 1

stock.sync_delivery_contact_phone(Row(
    docstatus=0,
    customer="CUSTOMER-1",
    contact_person="CONTACT-1",
    custom_store_phone="860566888",
))
assert contact.save_calls == 1, "same phone should not save the Contact again"

contact.links = [Row(link_doctype="Customer", link_name="OTHER-CUSTOMER")]
stock.sync_delivery_contact_phone(Row(
    docstatus=0,
    customer="CUSTOMER-1",
    contact_person="CONTACT-1",
    custom_store_phone="NEW-NUMBER",
))
assert contact.save_calls == 1, "a Contact from another Customer must be ignored"

contact.links = [Row(link_doctype="Customer", link_name="CUSTOMER-1")]
stock.sync_delivery_contact_phone(Row(
    docstatus=1,
    customer="CUSTOMER-1",
    contact_person="CONTACT-1",
    custom_store_phone="SUBMITTED-NUMBER",
))
assert contact.save_calls == 1, "submitted Delivery Notes must not rewrite Contacts"

hooks = (ROOT / "hooks.py").read_text(encoding="utf-8")
assert '"after_insert": "solua_home.api.stock.sync_delivery_contact_phone"' in hooks
assert '"on_update": "solua_home.api.stock.sync_delivery_contact_phone"' in hooks
print("PASS: Delivery Note store phone syncs the linked Customer Contact primary mobile")
