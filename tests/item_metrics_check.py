"""Run with Python; isolated fixtures never connect to a site or write business data."""
import importlib.util
import sys
import types
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

ROLE_CALLS = []
WRITES = []
SQL = []
GET_ALL = []
CREATED = []

class Row(dict):
    """Frappe returns documents, so the module reads columns as attributes."""

    __getattr__ = dict.__getitem__


frappe = types.ModuleType("frappe")
frappe._ = lambda text: text
frappe.whitelist = lambda *a, **k: (lambda fn: fn)
frappe.clear_cache = lambda **kwargs: None
frappe.only_for = lambda roles: ROLE_CALLS.append(roles)
utils = types.ModuleType("frappe.utils")
utils.flt = lambda value, precision=None: round(float(value or 0), precision) if precision is not None else float(value or 0)
frappe.utils = utils

HAS_COLUMN = {"Item": True}
ITEM_ROWS = {
    "RED": {"name": "RED", "has_variants": 0, "variant_of": "TPL", "stock_uom": "条",
            "custom_stock_qty": 0, "custom_variant_stock_qty": 0,
            "custom_rate_cost": 0, "custom_rate_home": 0, "custom_rate_wholesale": 0, "custom_rate_retail": 0},
    "TPL": {"name": "TPL", "has_variants": 1, "variant_of": "", "stock_uom": "条",
            "custom_stock_qty": 0, "custom_variant_stock_qty": 0,
            "custom_rate_cost": 0, "custom_rate_home": 0, "custom_rate_wholesale": 0, "custom_rate_retail": 0},
    "BAR": {"name": "BAR", "has_variants": 0, "variant_of": "", "stock_uom": "根",
            "custom_stock_qty": 99, "custom_variant_stock_qty": 0,
            "custom_rate_cost": 0, "custom_rate_home": 0, "custom_rate_wholesale": 0, "custom_rate_retail": 660},
}
STOCK_ROWS = [{"item_code": "RED", "qty": 12.0}, {"item_code": "BAR", "qty": 60.0}]
VARIANT_ROWS = [{"template": "TPL", "qty": 30.0}]
PRICE_ROWS = [
    {"item_code": "RED", "price_list": "Standard Selling", "rate": 900.0, "uom": "条"},
    {"item_code": "RED", "price_list": "Standard Selling", "rate": 800.0, "uom": "件"},
    {"item_code": "RED", "price_list": "Wholesale Selling", "rate": 480.0, "uom": "条"},
    {"item_code": "RED", "price_list": "Wholesale Selling 3", "rate": 430.0, "uom": "条"},
    {"item_code": "RED", "price_list": "Standard Buying", "rate": 334.157142857, "uom": "条"},
    {"item_code": "TPL", "price_list": "Standard Selling", "rate": 1580.0, "uom": "条"},
    {"item_code": "BAR", "price_list": "Standard Selling", "rate": 660.0, "uom": "根"},
]


def sql(query, params=None, as_dict=False, **kwargs):
    SQL.append(query)
    params = params or {}
    if "tabItem Price" in query:
        codes = set(params["codes"])
        return [Row(row) for row in PRICE_ROWS if row["item_code"] in codes and row["price_list"] in params["lists"]]
    if "`tabItem` i" in query:
        codes = set(params["codes"])
        return [Row(row) for row in VARIANT_ROWS if row["template"] in codes]
    if "`tabBin` b" in query:
        codes = set(params["codes"])
        return [Row(row) for row in STOCK_ROWS if row["item_code"] in codes]
    raise AssertionError("unexpected query: " + query)


def get_all(doctype, filters=None, fields=None, limit_page_length=None, pluck=None, **kwargs):
    GET_ALL.append((doctype, filters))
    if doctype != "Item":
        raise AssertionError("unexpected doctype " + doctype)
    if pluck:
        return list(ITEM_ROWS)
    codes = filters["name"][1]
    return [Row(ITEM_ROWS[code]) for code in codes if code in ITEM_ROWS]


class CustomField(dict):
    def __getattr__(self, key):
        return self[key]

    def insert(self, **kwargs):
        CREATED.append((self["dt"], self["fieldname"], self["fieldtype"], self.get("in_list_view"),
                        self.get("read_only"), self.get("insert_after")))
        return self


def get_doc(arg, *args, **kwargs):
    if isinstance(arg, dict):
        return CustomField(arg)
    raise AssertionError("unexpected get_doc: %r" % (arg,))


EXISTING_FIELDS = set()
frappe.db = types.SimpleNamespace(
    has_column=lambda dt, field: HAS_COLUMN[dt],
    exists=lambda dt, filters: (dt == "Custom Field" and (filters["dt"], filters["fieldname"]) in EXISTING_FIELDS)
    or (dt == "Custom Field" and False),
    sql=sql,
    set_value=lambda dt, name, values, **kwargs: WRITES.append((dt, name, dict(values), kwargs.get("update_modified"))),
)
frappe.get_all = get_all
frappe.get_doc = get_doc
frappe.get_meta = lambda dt: types.SimpleNamespace(has_field=lambda field: field == "standard_rate")
sys.modules["frappe"] = frappe
sys.modules["frappe.utils"] = utils

spec = importlib.util.spec_from_file_location("item_metrics_candidate", ROOT / "item_metrics.py")
metrics = importlib.util.module_from_spec(spec)
spec.loader.exec_module(metrics)

# ---- price lists per field -------------------------------------------------
assert metrics.PRICE_FIELDS == {
    "custom_rate_cost": "Standard Buying",
    "custom_rate_home": "Wholesale Selling 3",
    "custom_rate_wholesale": "Wholesale Selling",
    "custom_rate_retail": "Standard Selling",
}, metrics.PRICE_FIELDS
assert set(metrics.STOCK_VOUCHERS) == {"Stock Entry", "Stock Reconciliation", "Purchase Receipt",
                                       "Purchase Invoice", "Delivery Note", "Sales Invoice", "POS Invoice"}

# ---- refresh names the items, prefers the stock UOM, skips customer rows ----
GET_ALL.clear()
WRITES.clear()
updated = metrics.refresh_items(["RED", "TPL"])
written = {name: values for _dt, name, values, _um in WRITES}
assert updated == 2 and set(written) == {"RED", "TPL"}, (updated, written)
assert written["RED"]["custom_stock_qty"] == 12.0
assert written["RED"]["custom_rate_retail"] == 900.0, written["RED"]  # 条 beats 件, customer rows never reach the query
assert written["RED"]["custom_rate_wholesale"] == 480.0
assert written["RED"]["custom_rate_home"] == 430.0
assert written["RED"]["custom_rate_cost"] == 334.16  # mirrored value is rounded for display
assert "custom_variant_stock_qty" not in written["RED"], "single items have no variant total"
assert written["TPL"]["custom_variant_stock_qty"] == 30.0
assert written["TPL"]["custom_rate_retail"] == 1580.0
assert "custom_stock_qty" not in written["TPL"], "a template with no own Bin keeps 0"
assert all(kwargs is False for *_x, kwargs in WRITES), "metric writes must not bump modified"
price_sql = [q for q in SQL if "tabItem Price" in q][0]
assert "ifnull(ip.customer, '') = ''" in price_sql and "ifnull(ip.supplier, '') = ''" in price_sql
stock_sql = [q for q in SQL if "`tabBin` b" in q][0]
assert "is_group" in stock_sql and "disabled" in stock_sql, "group/disabled warehouses must not count"
assert "group by b.item_code" in stock_sql

# ---- a variant edit also realigns its template -----------------------------
for _dt, name, values, _u in WRITES:  # pretend the writes land in the database
    ITEM_ROWS[name].update(values)
GET_ALL.clear()
WRITES.clear()
metrics.refresh_items(["RED"], stock=True, prices=True)
fetched = [tuple(filters["name"][1]) for _dt, filters in GET_ALL]
assert any("TPL" in codes for codes in fetched), fetched  # the variant's template rides along
assert WRITES == [], "nothing changed, so nothing is written"

# ---- stock-only and price-only paths --------------------------------------
WRITES.clear()
metrics.refresh_items(["BAR"], stock=True, prices=False)
assert WRITES == [("Item", "BAR", {"custom_stock_qty": 60.0}, False)], WRITES
ITEM_ROWS["BAR"].update(WRITES[-1][2])
WRITES.clear()
metrics.refresh_items(["BAR"], stock=False, prices=True)
assert WRITES == [] and ITEM_ROWS["BAR"]["custom_rate_retail"] == 660
metrics.refresh_items(["BAR"], stock=True, prices=False)
assert WRITES == [], "a second run must not rewrite unchanged values"
metrics.refresh_items(["BAR"], prices=False)
assert WRITES == []

# ---- voucher / price / item hooks -----------------------------------------
ITEM_ROWS["RED"]["custom_stock_qty"] = 0
ITEM_ROWS["TPL"]["custom_variant_stock_qty"] = 0
WRITES.clear()
voucher = types.SimpleNamespace(items=[types.SimpleNamespace(item_code="RED"),
                                      types.SimpleNamespace(item_code="RED"),
                                      types.SimpleNamespace(item_code="BAR"),
                                      types.SimpleNamespace(item_code="")])
metrics.on_stock_voucher_change(voucher)
assert sorted(name for _dt, name, _v, _u in WRITES) == ["RED", "TPL"], WRITES
assert all(set(values) <= {metrics.STOCK_FIELD, metrics.VARIANT_STOCK_FIELD} for _dt, _n, values, _u in WRITES)
WRITES.clear()
metrics.on_stock_voucher_change(types.SimpleNamespace(items=[]))
ITEM_ROWS["RED"]["custom_rate_retail"] = 0
metrics.on_item_price_change(types.SimpleNamespace(item_code="RED"))
assert [(name, values) for _dt, name, values, _u in WRITES] == [("RED", {"custom_rate_retail": 900.0})], WRITES
assert metrics.refresh_items([]) == 0 and metrics.refresh_items(None) == 0

# ---- field creation is complete and idempotent -----------------------------
created = metrics.ensure_item_metric_fields()
assert created == list(metrics.PRICE_FIELDS) + [metrics.STOCK_FIELD, metrics.VARIANT_STOCK_FIELD], created
assert set(metrics.METRIC_FIELDS) == set(created)
assert [field[1] for field in CREATED] == created
assert all(field[2] == "Currency" for field in CREATED[:4])
assert [field[2] for field in CREATED[4:]] == ["Float", "Float"]
assert all(field[3] == 1 and field[4] == 1 for field in CREATED), "columns must be read-only list columns"
assert CREATED[0][5] == "standard_rate", CREATED[0]
assert CREATED[4][5] == "custom_rate_retail" and CREATED[5][5] == metrics.STOCK_FIELD, CREATED
EXISTING_FIELDS.update(("Item", name) for name in created)
CREATE = list(CREATED)
assert metrics.ensure_item_metric_fields() == [] and CREATED == CREATE, "rerun must not duplicate fields"

# ---- whitelisted refresh is role-gated ------------------------------------
metrics.refresh_all_item_metrics()
assert ROLE_CALLS and "System Manager" in ROLE_CALLS[0]
HAS_COLUMN["Item"] = False
WRITES.clear()
assert metrics.refresh_all_items() == 0 and metrics.refresh_items(["RED"]) == 0 and WRITES == []
HAS_COLUMN["Item"] = True

print("PASS: item metrics map the four price lists, prefer the stock UOM, skip customer rows, "
      "sum leaf-warehouse stock, aggregate template variants, refresh only on change, and create "
      "the six read-only list columns once")
