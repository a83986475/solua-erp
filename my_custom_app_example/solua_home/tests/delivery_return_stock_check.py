"""Check the return-only negative-stock override without a Bench runtime."""

import importlib.util
import sys
import types
from pathlib import Path


class BaseDeliveryNote:
    is_return = 0

    def update_stock_ledger(self, allow_negative_stock=False):
        self.received_allow_negative_stock = allow_negative_stock


erpnext = types.ModuleType("erpnext")
erpnext.__path__ = []
stock = types.ModuleType("erpnext.stock")
stock.__path__ = []
doctype = types.ModuleType("erpnext.stock.doctype")
doctype.__path__ = []
delivery = types.ModuleType("erpnext.stock.doctype.delivery_note")
delivery.__path__ = []
module = types.ModuleType("erpnext.stock.doctype.delivery_note.delivery_note")
module.DeliveryNote = BaseDeliveryNote
sys.modules.update({
    "erpnext": erpnext,
    "erpnext.stock": stock,
    "erpnext.stock.doctype": doctype,
    "erpnext.stock.doctype.delivery_note": delivery,
    "erpnext.stock.doctype.delivery_note.delivery_note": module,
})

path = Path(__file__).resolve().parents[1] / "override" / "delivery_note.py"
spec = importlib.util.spec_from_file_location("delivery_note_override", path)
loaded = importlib.util.module_from_spec(spec)
spec.loader.exec_module(loaded)

return_note = loaded.CustomDeliveryNote()
return_note.is_return = 1
return_note.update_stock_ledger(False)
assert return_note.received_allow_negative_stock is True

sales_note = loaded.CustomDeliveryNote()
sales_note.is_return = 0
sales_note.update_stock_ledger(False)
assert sales_note.received_allow_negative_stock is False

print("PASS: only Delivery Note returns allow negative stock ledger repair")
