"""Run without a Bench environment: python tests/receivable_store_check.py."""

import importlib.util
import json
import sys
from pathlib import Path
from types import ModuleType


ROOT = Path(__file__).resolve().parents[1]


def load(name, path):
    spec = importlib.util.spec_from_file_location(name, ROOT / path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


class Invoice(dict):
    docstatus = 0

    @property
    def name(self):
        return self.get("name")

    def set(self, name, value):
        self[name] = value


class Meta:
    def has_field(self, field):
        return field == "custom_store_name"


def invoice(name, **values):
    doc = Invoice(name=name, company="Solua", customer="Chain", **values)
    doc.meta = Meta()
    return doc


records = {
    "Sales Invoice": [
        invoice("SAVED", custom_store_name="Original name"),
        invoice("OLD"), invoice("MIXED"), invoice("PARTIAL"),
        invoice("EMPTY"), invoice("WRONG"), invoice("VIA-DN"),
        invoice("CREDIT", is_return=1, return_against="OLD"),
        invoice("CREDIT-SAVED", is_return=1, return_against="SAVED"),
    ],
    "Sales Invoice Item": [
        {"parent": inv, "parenttype": "Sales Invoice", **row}
        for inv, row in (
            ("OLD", {"sales_order": "SO-A"}),
            ("MIXED", {"sales_order": "SO-A"}),
            ("MIXED", {"sales_order": "SO-B"}),
            ("PARTIAL", {"sales_order": "SO-A"}),
            ("PARTIAL", {"sales_order": "SO-EMPTY"}),
            ("WRONG", {"sales_order": "SO-WRONG"}),
            ("VIA-DN", {"dn_detail": "DNI-A"}),
        )
    ],
    "Sales Order": [
        {"name": name, "customer": customer, "company": "Solua", "custom_store_name": store}
        for name, customer, store in (
            ("SO-A", "Chain", " Loja A "), ("SO-A2", "Chain", "Loja A"),
            ("SO-B", "Chain", "Loja B"), ("SO-EMPTY", "Chain", None),
            ("SO-WRONG", "Other Chain", "Loja A"),
        )
    ],
    "Sales Order Item": [{"name": "SOI-A", "parent": "SO-A", "parenttype": "Sales Order"}],
    "Delivery Note Item": [
        {"name": "DNI-A", "parenttype": "Delivery Note", "against_sales_order": "SO-A"}
    ],
}


def get_all(doctype, filters, fields):
    def matches(row, field, value):
        if isinstance(value, list):
            operator, values = value
            assert operator == "in"
            return row.get(field) in values
        return row.get(field) == value

    return [
        {field: row.get(field) for field in fields}
        for row in records[doctype]
        if all(matches(row, field, value) for field, value in filters.items())
    ]


frappe = ModuleType("frappe")
frappe.get_all = get_all
sys.modules["frappe"] = frappe
module = load("solua_home.api.receivable_store", "api/receivable_store.py")

draft = invoice(None, items=[{"sales_order": "SO-A"}, {"sales_order": "SO-A2"}, {}])
assert module.apply_invoice_store(draft) is draft
assert draft[module.STORE_FIELD] == "Loja A"
draft["items"] = [{"so_detail": "SOI-A"}]
assert module.apply_invoice_store(draft)[module.STORE_FIELD] == "Loja A"
draft["items"] = [{"sales_order": "SO-A"}, {"sales_order": "SO-B"}]
assert module.apply_invoice_store(draft)[module.STORE_FIELD] is None
draft["items"] = [{"sales_order": "SO-A"}, {"dn_detail": "MISSING"}]
assert module.apply_invoice_store(draft)[module.STORE_FIELD] is None
draft["items"] = [{"sales_order": "SO-A"}]
draft.docstatus = 1
assert module.apply_invoice_store(draft)[module.STORE_FIELD] == "Loja A"
draft.docstatus = 2
draft["items"] = []
assert module.apply_invoice_store(draft)[module.STORE_FIELD] == "Loja A"

expected = {
    "SAVED": "Original name", "OLD": "Loja A", "VIA-DN": "Loja A",
    "CREDIT": "Loja A", "CREDIT-SAVED": "Original name",
}
assert module.get_invoice_stores({row.name for row in records["Sales Invoice"]}) == expected

report_path = "solua_wholesale/report/solua_accounts_receivable/solua_accounts_receivable.py"
report_module_name = "solua_home.solua_wholesale.report.solua_accounts_receivable.solua_accounts_receivable"
native = ModuleType("frappe.desk.query_report")
native.get_report_doc = lambda name: name
rows = [
    {"voucher_type": "Sales Invoice", "voucher_no": "OLD", "outstanding": 42},
    {"voucher_type": "Sales Invoice", "voucher_no": "MIXED", "outstanding": 50},
    {"voucher_type": "Payment Entry", "voucher_no": "PAY-1", "outstanding": -10},
    {"party": "Chain", "outstanding": 82},
    {},
]
native.get_report_result = lambda name, filters: (
    [{"fieldname": "party"}, {"fieldname": "outstanding"}],
    [dict(row) for row in rows],
    None, {"chart": "original"}, None, 1,
)
sys.modules[native.__name__] = native
report = load(report_module_name, report_path)
columns, result, *extras = report.execute({"company": "Solua"})
assert [col["fieldname"] for col in columns] == ["party", module.STORE_FIELD, "outstanding"]
assert result[0][module.STORE_FIELD] == "Loja A"
assert result[1][module.STORE_FIELD] == "未指定门店"
assert result[2:] == rows[2:]
assert [row.get("outstanding") for row in result] == [row.get("outstanding") for row in rows]
assert extras == [None, {"chart": "original"}, None, 1]

original_columns = [{"fieldname": "party", "label": "往来单位", "width": 230}, {"fieldname": "outstanding"}]
saved_filters = {"company": "Solua", "group_by_party": 1}
config = ModuleType("test_config")
config.report_type = "Custom Report"
config.reference_report = report.BASE_REPORT
config.json = json.dumps({"columns": original_columns, "filters": saved_filters, "test_property": 1})
saves = []
config.save = lambda **kwargs: saves.append(kwargs)
frappe.db = ModuleType("db")
frappe.db.exists = lambda doctype, name: name == report.CUSTOM_REPORT
frappe.get_doc = lambda doctype, name: config
frappe.parse_json = json.loads
frappe.as_json = json.dumps
patch = load("receivable_store_patch", "patches/v20261113_receivable_store_name.py")
patch.execute()
patch.execute()
assert len(saves) == 1
settings = json.loads(config.json)
assert config.reference_report == report.REPORT_NAME
assert settings["columns"][::2] == original_columns
assert settings["columns"][1]["fieldname"] == module.STORE_FIELD
assert settings["filters"] == saved_filters
assert settings["test_property"] == 1

print("receivable_store_check: OK")
