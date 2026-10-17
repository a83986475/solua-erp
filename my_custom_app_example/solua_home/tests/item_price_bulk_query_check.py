"""The bulk-price selector keeps templates and ordinary Items, respecting permissions."""

import importlib.util
from pathlib import Path
import sys
import types

calls = []
allowed = True


def deny(message, error):
    raise error(message)


frappe = types.ModuleType("frappe")
frappe._ = lambda text: text
frappe.whitelist = lambda: lambda fn: fn
frappe.validate_and_sanitize_search_inputs = lambda fn: fn
frappe.only_for = lambda roles: calls.append(("roles", roles))
frappe.has_permission = lambda *args: allowed
frappe.PermissionError = PermissionError
frappe.throw = deny
items = [
    {"name": "SH1", "item_name": "Template", "variant_of": None, "disabled": 0},
    {"name": "SH1-RED", "item_name": "Variant", "variant_of": "SH1", "disabled": 0},
    {"name": "SH2", "item_name": "Ordinary", "variant_of": "", "disabled": 0},
    {"name": "SH3", "item_name": "Disabled", "variant_of": "", "disabled": 1},
]


def get_list(doctype, **kwargs):
    calls.append((doctype, kwargs))
    assert kwargs["filters"] == {"disabled": 0, "variant_of": ["is", "not set"]}
    term = kwargs["or_filters"]["name"][1].strip("%")
    assert kwargs["or_filters"]["item_name"] == ["like", f"%{term}%"]
    rows = [item for item in items if not item["disabled"] and not item["variant_of"]
            and (term in item["name"] or term in item["item_name"])]
    rows = rows[kwargs["limit_start"]:kwargs["limit_start"] + kwargs["limit_page_length"]]
    return [{key: row[key] for key in kwargs["fields"]} if not kwargs["as_list"]
            else [row[key] for key in kwargs["fields"]] for row in rows]


frappe.get_list = get_list
utils = types.ModuleType("frappe.utils")
utils.flt = float
sys.modules.update({"frappe": frappe, "frappe.utils": utils})
spec = importlib.util.spec_from_file_location("item_price_bulk", Path(__file__).parents[1] / "api/item_price_bulk.py")
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)

query = module.item_query
assert query("Item", "", "name", 0, 20) == [["SH1", "Template"], ["SH2", "Ordinary"]]
assert query("Item", "SH1", "name", 0, 20) == [["SH1", "Template"]]
assert query("Item", "Ordinary", "name", 0, 20, as_dict=True) == [{"name": "SH2", "item_name": "Ordinary"}]
assert query("Item", "", "name", 1, 1) == [["SH2", "Ordinary"]]
assert query("User", "", "name", 0, 20, {"variant_of": "SH1"}) == [["SH1", "Template"], ["SH2", "Ordinary"]]
allowed = False
count = len(calls)
try:
    query("Item", "", "name", 0, 20)
except PermissionError:
    pass
else:
    raise AssertionError("Item Price write permission is required")
assert len(calls) == count + 1, "denied requests must not query Items"
print("PASS: bulk-price query includes templates/ordinary Items, excludes variants/disabled Items, searches, paginates and checks access")
