"""Run without Bench: python .../tests/invoice_stock_guard_check.py."""
import importlib.util
import pathlib
import sys
import types

queries = []
def exists(doctype, filters):
    queries.append((doctype, filters))
    return filters.get("name") == "submitted-dn" or filters.get("so_detail") == "delivered-row"

def fail(message, *args):
    raise ValueError(message)

sys.modules["frappe"] = types.SimpleNamespace(
    db=types.SimpleNamespace(exists=exists), _=lambda text: text,
    whitelist=lambda: lambda fn: fn, throw=fail,
)
path = pathlib.Path(__file__).resolve().parents[1] / "invoice_stock_guard.py"
spec = importlib.util.spec_from_file_location("stock_guard", path)
guard = importlib.util.module_from_spec(spec)
spec.loader.exec_module(guard)
assert guard.has_delivery_note([{"delivery_note": "submitted-dn"}])
assert not guard.has_delivery_note([{"delivery_note": "cancelled-dn"}])
linked = {"sales_order": "order", "item_code": "sku", "so_detail": "delivered-row"}
assert guard.has_delivery_note([linked])
assert queries[-1][1]["docstatus"] == 1
assert not guard.has_delivery_note([dict(linked, so_detail="undelivered-row")])
assert not guard.has_delivery_note([{"item_code": "direct-sale"}])
class Invoice:
    update_stock = 1
    def get(self, field):
        return [linked]
try:
    guard.validate_stock_update(Invoice())
except ValueError:
    pass
else:
    raise AssertionError("Delivery-backed stock update was allowed")
Invoice.update_stock = 0
guard.validate_stock_update(Invoice())
print("invoice stock guard checks passed")
