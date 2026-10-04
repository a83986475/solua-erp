import importlib.util
import sys
import types
from pathlib import Path


class Doc(dict):
    __getattr__ = dict.get
    __setattr__ = dict.__setitem__


class Blocked(Exception):
    pass


values = {("Customer", "AN LAN", "default_price_list"): "Wholesale Selling 3",
          ("Sales Invoice", "level3", "selling_price_list"): "Wholesale Selling 3"}
def throw(message):
    raise Blocked(message)

sys.modules["frappe"] = types.SimpleNamespace(
    _=lambda value: value, db=types.SimpleNamespace(get_value=lambda dt, name, field: values.get((dt, name, field))),
    whitelist=lambda: lambda fn: fn, throw=throw,
)
sys.modules["frappe.utils"] = types.SimpleNamespace(flt=lambda value: float(value or 0))
spec = importlib.util.spec_from_file_location("cash_discount", Path(__file__).resolve().parents[1] / "cash_discount.py")
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)

def payment(customer="ordinary", invoice="ordinary", deduction=3):
    return Doc(party_type="Customer", party=customer,
        references=[Doc(reference_doctype="Sales Invoice", reference_name=invoice, allocated_amount=100)],
        deductions=[Doc(account="Discount Allowed - SH", amount=deduction)])

for doc in (payment("AN LAN"), payment(invoice="level3")):
    try:
        module.validate_payment_entry(doc)
    except Blocked:
        pass
    else:
        raise AssertionError("Level three cash discount was accepted")
module.validate_payment_entry(payment())
module.validate_payment_entry(payment("AN LAN", deduction=0))
module.validate_payment_entry(Doc(party_type="Supplier", deductions=[Doc(account="Discount Allowed - SH", amount=3)]))
row = Doc(discount=3, discount_type="Percentage", discounted_amount=3, discount_date="2026-10-09")
module.validate_sales_document(Doc(selling_price_list="Wholesale Selling 3", payment_schedule=[row]))
assert row.discount == 0 and row.discount_date is None and row.discounted_amount == 0
normal = Doc(discount=3)
module.validate_sales_document(Doc(customer="ordinary", payment_schedule=[normal]))
assert normal.discount == 3
print("PASS: customer/invoice exclusion, normal discount, no discount, supplier, payment schedule")
