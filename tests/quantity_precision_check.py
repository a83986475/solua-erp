"""Run without Bench: python tests/quantity_precision_check.py."""
import importlib.util
import sys
import types
from pathlib import Path

root = Path(__file__).resolve().parents[1]
created = []
cleared = []

frappe = types.ModuleType("frappe")
frappe.db = types.SimpleNamespace(get_value=lambda *args: None)
frappe.get_meta = lambda doctype: types.SimpleNamespace(
	get_field=lambda fieldname: types.SimpleNamespace(fieldtype="Float")
	if doctype == "Sales Invoice" and fieldname == "total_qty" else None
)
frappe.make_property_setter = lambda args, **kwargs: created.append((args, kwargs))
frappe.clear_cache = lambda **kwargs: cleared.append(kwargs)
sys.modules["frappe"] = frappe

spec = importlib.util.spec_from_file_location("quantity_precision", root / "quantity_precision.py")
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)
module.ensure_quantity_precision()

assert len(created) == 1
args, kwargs = created[0]
assert args == {
	"doctype": "Sales Invoice", "doctype_or_field": "DocField", "fieldname": "total_qty",
	"property": "precision", "value": "0", "property_type": "Int",
}
assert kwargs == {}
assert cleared[0] == {"doctype": "Sales Invoice"}
print("quantity_precision_check: OK")
