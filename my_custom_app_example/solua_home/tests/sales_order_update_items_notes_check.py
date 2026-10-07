import json
import sys
import types
from pathlib import Path
from types import SimpleNamespace


sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
calls = []
docs = iter(())


class Parent:
    def __init__(self, rows):
        self.rows = rows

    def get(self, fieldname):
        assert fieldname == "items"
        return self.rows


def whitelist(function=None):
	return function or (lambda wrapped: wrapped)


frappe = types.ModuleType("frappe")
frappe.parse_json = json.loads
frappe.whitelist = whitelist
frappe.get_doc = lambda *_: next(docs)
frappe.get_meta = lambda *_: SimpleNamespace(has_field=lambda fieldname: fieldname == "pos_additional_notes")
frappe.db = SimpleNamespace(set_value=lambda *args: calls.append(args))
sys.modules["frappe"] = frappe

native_module = types.ModuleType("erpnext.controllers.accounts_controller")


def native_update(*args):
    calls.append(("native", args))


native_module.update_child_qty_rate = native_update
for name in ("erpnext", "erpnext.controllers"):
    sys.modules[name] = types.ModuleType(name)
sys.modules[native_module.__name__] = native_module

from solua_home.api.child_items import update_child_qty_rate


old = SimpleNamespace(name="SOI-1", item_code="A", additional_notes="旧备注", pos_additional_notes="")
new = SimpleNamespace(name="SOI-2", item_code="B", additional_notes="", pos_additional_notes="")
docs = iter((Parent([old]), Parent([old, new])))
update_child_qty_rate(
    "Sales Order",
    [{"docname": "SOI-1", "item_code": "A", "additional_notes": "新备注"}, {"item_code": "B", "additional_notes": "新物料备注"}],
    "SO-1",
)
assert calls[0][0] == "native"
assert calls[1] == ("Sales Order Item", "SOI-1", "additional_notes", "新备注")
assert calls[2] == ("Sales Order Item", "SOI-1", "pos_additional_notes", "新备注")
assert calls[3] == ("Sales Order Item", "SOI-2", "additional_notes", "新物料备注")
assert calls[4] == ("Sales Order Item", "SOI-2", "pos_additional_notes", "新物料备注")

calls.clear()
update_child_qty_rate("Purchase Order", [{"item_code": "A"}], "PO-1")
assert calls[0][0] == "native"
print("PASS: submitted Sales Order item notes update and new-row notes mapping")
