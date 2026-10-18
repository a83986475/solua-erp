"""Isolated retirement checks: exact names, live references, idempotence and link safety."""

import importlib.util
from pathlib import Path
import sys
import types

ROOT = Path(__file__).resolve().parents[1]
frappe = types.ModuleType("frappe")
sys.modules["frappe"] = frappe
spec = importlib.util.spec_from_file_location("reviewed_formats", ROOT / "printing/format_retirement.py")
policy = importlib.util.module_from_spec(spec)
spec.loader.exec_module(policy)
assert {dt: len(names) for dt, names in policy.RETIRED_FORMATS.items()} == {
    "Sales Order": 15, "Pick List": 3, "Delivery Note": 4, "Sales Invoice": 13,
}
assert policy.is_retired_format("客户订单确认单（颜色版）-紧凑版")
assert not policy.is_retired_format("差价退款 A4 可编辑版 - 销售订单 v2")
defaults = {
    "Sales Order": "ORDER CONFIRMACAO(PT）", "Pick List": "拣货单",
    "Delivery Note": "Guia de Remessa", "Sales Invoice": "FACTURA A4（8mm边距） v2 v3",
}
rows = {name: types.SimpleNamespace(doc_type=dt, disabled=0)
        for dt, names in policy.RETIRED_FORMATS.items() for name in names}
rows.update({name: types.SimpleNamespace(doc_type=dt, disabled=0) for dt, name in defaults.items()})
rows["Sales Auditing Voucher"] = types.SimpleNamespace(doc_type="Sales Invoice", disabled=1)
rows["Future Custom Format"] = types.SimpleNamespace(doc_type="Sales Order", disabled=0)
profile_default = "Sales Invoice with Item Image（现金折扣版）"
deleted = []
blocked = None


def set_value(dt, name, field, value):
    global profile_default
    if dt == "POS Profile":
        profile_default = value
    else:
        setattr(rows[name], field, value)


def delete_doc(dt, name, **kwargs):
    assert dt == "Print Format" and kwargs == {"ignore_permissions": True}
    if name == blocked:
        raise ValueError("linked document")
    deleted.append(name)
    del rows[name]


frappe.db = types.SimpleNamespace(
    exists=lambda dt, name: name in rows,
    get_value=lambda dt, name, field: getattr(rows.get(name), field, None),
    set_value=set_value,
)
frappe.get_doc = lambda dt, name: rows[name]
frappe.get_meta = lambda dt: types.SimpleNamespace(default_print_format=defaults.get(dt), has_field=lambda field: True)
frappe.get_all = lambda dt, **kwargs: ["Profile"] if profile_default in policy.RETIRED_FORMATS["Sales Invoice"] else []
frappe.delete_doc = delete_doc
frappe.clear_cache = lambda **kwargs: None

assert len(policy.apply_reviewed_retirements()) == 35
assert len(deleted) == len(set(deleted)) == 35
assert profile_default == defaults["Sales Invoice"]
assert rows["Sales Auditing Voucher"].disabled == 0
assert "Future Custom Format" in rows
assert policy.apply_reviewed_retirements() == []

blocked = policy.RETIRED_FORMATS["Sales Order"][0]
rows[blocked] = types.SimpleNamespace(doc_type="Sales Invoice", disabled=0)
try:
    policy.apply_reviewed_retirements()
except RuntimeError:
    pass
else:
    raise AssertionError("Mismatched document type accepted")
rows[blocked].doc_type = "Sales Order"
try:
    policy.apply_reviewed_retirements()
except ValueError as exc:
    assert str(exc) == "linked document"
else:
    raise AssertionError("Link validation bypassed")
assert blocked in rows

defaults["Sales Order"] = "Missing Format"
try:
    policy.apply_reviewed_retirements()
except RuntimeError:
    pass
else:
    raise AssertionError("Missing default accepted")

for name in policy.MARGIN_FORMATS:
    for key in ("format", "print_format"):
        frappe.form_dict = {key: name}
        assert "margin:8mm 8mm 10mm!important" in policy.get_reviewed_margin_css()
        assert "min-height:0!important" in policy.get_reviewed_margin_css()
for name in (None, "Standard", "ORDER CONFIRMACAO(PT）", "Guia de Remessa", "Future Custom Format"):
    frappe.form_dict = {"format": name}
    assert policy.get_reviewed_margin_css() == ""
print("PASS: 35 exact retirements, references, retained activation, idempotence, link checks and four scoped margins")
