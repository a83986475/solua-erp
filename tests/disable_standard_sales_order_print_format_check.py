"""Run with Python; verifies the targeted, idempotent print-format migration."""
import importlib.util
from pathlib import Path
import sys
from types import ModuleType, SimpleNamespace

ROOT = Path(__file__).resolve().parents[1]
target = "Sales Order with Item Image"
custom = "客户订单确认单（颜色版）"
records = {
    target: SimpleNamespace(doc_type="Sales Order", standard="Yes", disabled=0),
    custom: SimpleNamespace(doc_type="Sales Order", disabled=0),
}
default = [target]
updates = []
setters = []
cache_clears = []

frappe = ModuleType("frappe")
frappe.db = SimpleNamespace(
    get_value=lambda doctype, name, fields, as_dict=False: records.get(name),
    set_value=lambda *args, **kwargs: updates.append((args, kwargs)),
)
frappe.get_meta = lambda doctype: SimpleNamespace(default_print_format=default[0])
frappe.make_property_setter = lambda values: setters.append(values)
frappe.clear_cache = lambda **kwargs: cache_clears.append(kwargs)
sys.modules["frappe"] = frappe

spec = importlib.util.spec_from_file_location("installer_check", ROOT / "install.py")
installer = importlib.util.module_from_spec(spec)
spec.loader.exec_module(installer)

installer.disable_standard_sales_order_image_format()
assert setters[0]["value"] == custom and cache_clears == [{"doctype": "Sales Order"}]
assert updates[0][0][:3] == ("Print Format", target, "disabled")

records[target].disabled = 1
default[0] = custom
installer.disable_standard_sales_order_image_format()
assert len(setters) == 1 and len(updates) == 1

records[custom].disabled = 1
try:
    installer.disable_standard_sales_order_image_format()
except RuntimeError as exc:
    assert custom in str(exc)
else:
    raise AssertionError("Disabled custom format was accepted")
assert len(updates) == 1
