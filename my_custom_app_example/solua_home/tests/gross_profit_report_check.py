import importlib.util
import sys
import types


def decorator(*args, **kwargs):
    if args and callable(args[0]):
        return args[0]
    return lambda fn: fn


frappe = types.ModuleType("frappe")
frappe.whitelist = decorator
frappe.read_only = decorator
frappe.parse_json = lambda value: value
utils = types.ModuleType("frappe.utils")
utils.flt = lambda value, precision=None: round(float(value or 0), precision) if precision is not None else float(value or 0)
query_report = types.ModuleType("frappe.desk.query_report")
query_report.run = lambda **kwargs: None
desk = types.ModuleType("frappe.desk")
desk.query_report = query_report
frappe.desk = desk
sys.modules.update({
    "frappe": frappe,
    "frappe.utils": utils,
    "frappe.desk": desk,
    "frappe.desk.query_report": query_report,
})

spec = importlib.util.spec_from_file_location("gross_profit", "my_custom_app_example/solua_home/api/gross_profit.py")
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)

rows = [
    {"indent": 0, "sales_invoice": "ACC-SINV-1", "selling_amount": 1000, "buying_amount": 0, "gross_profit": 1000},
    {"indent": 1, "parent_invoice": "ACC-SINV-1", "sales_invoice": "ROD-1", "qty": 0, "valuation_rate": 60,
     "selling_amount": 950, "buying_amount": 0, "gross_profit": 950, "gross_profit_%": 100},
    {"indent": 0, "sales_invoice": "ACC-SINV-2", "selling_amount": 500, "buying_amount": 200, "gross_profit": 300},
    {"indent": 1, "parent_invoice": "ACC-SINV-2", "sales_invoice": "CURTAIN-1", "qty": 5, "valuation_rate": 40,
     "selling_amount": 500, "buying_amount": 200, "gross_profit": 300, "gross_profit_%": 60},
    {"sales_invoice": "Total", "selling_amount": 1500, "buying_amount": 200, "gross_profit": 1300},
]
module._recalculate_invoice_rows(
    rows,
    {("ACC-SINV-1", "ROD-1"): 10},
    {("ACC-SINV-1", "ROD-1"): -50},
)
assert rows[1]["qty"] == 10
assert rows[1]["buying_amount"] == 600
assert rows[1]["gross_profit"] == 350
assert rows[1]["gross_profit_%"] == round(350 / 950 * 100, 3)
assert rows[0]["buying_amount"] == 600
assert rows[4]["buying_amount"] == 800
assert rows[4]["selling_amount"] == 1450

unit_rows = [
    {"indent": 0, "sales_invoice": "ACC-SINV-3", "selling_amount": 2610, "buying_amount": 364, "gross_profit": 2246},
    {"indent": 1, "parent_invoice": "ACC-SINV-3", "sales_invoice": "ROD-BOX", "qty": 1, "valuation_rate": 364,
     "selling_amount": 2610, "buying_amount": 364, "gross_profit": 2246, "gross_profit_%": 86.054},
    {"sales_invoice": "Total", "selling_amount": 2610, "buying_amount": 364, "gross_profit": 2246},
]
module._recalculate_invoice_rows(
    unit_rows,
    {("ACC-SINV-3", "ROD-BOX"): 1},
    {},
    {("ACC-SINV-3", "ROD-BOX"): 6},
)
assert unit_rows[1]["qty"] == 1
assert unit_rows[1]["valuation_rate"] == 2184
assert unit_rows[1]["buying_amount"] == 2184
assert unit_rows[1]["gross_profit"] == 426
assert unit_rows[1]["gross_profit_%"] == round(426 / 2610 * 100, 3)
assert unit_rows[0]["buying_amount"] == 2184
assert unit_rows[2]["buying_amount"] == 2184

stock_uom_rows = [
    {"indent": 0, "sales_invoice": "ACC-SINV-4", "selling_amount": 7320, "buying_amount": 6360, "gross_profit": 960},
    {"indent": 1, "parent_invoice": "ACC-SINV-4", "sales_invoice": "ROD-STOCK", "qty": 12, "valuation_rate": 530,
     "selling_amount": 7320, "buying_amount": 6360, "gross_profit": 960, "gross_profit_%": 13.115},
    {"sales_invoice": "Total", "selling_amount": 7320, "buying_amount": 6360, "gross_profit": 960},
]
module._recalculate_invoice_rows(
    stock_uom_rows,
    {("ACC-SINV-4", "ROD-STOCK"): 2},
    {},
    {("ACC-SINV-4", "ROD-STOCK"): 12},
)
assert stock_uom_rows[1]["qty"] == 12
assert stock_uom_rows[1]["valuation_rate"] == 530
assert stock_uom_rows[1]["buying_amount"] == 6360
assert stock_uom_rows[1]["gross_profit"] == 960

assert module._price_only_return_names(
    [
        {"parent": "RET-PRICE", "item_code": "ROD", "qty": -1, "base_net_amount": -100},
        {"parent": "RET-FULL", "item_code": "CURTAIN", "qty": -10, "base_net_amount": -3341.6},
    ],
    {"RET-PRICE": "INV-PRICE", "RET-FULL": "INV-FULL"},
    {("INV-PRICE", "ROD"): 1, ("INV-FULL", "CURTAIN"): 10},
    {("INV-PRICE", "ROD"): 1000, ("INV-FULL", "CURTAIN"): 3341.6},
) == {"RET-PRICE"}

assert module._price_only_return_names(
    [{"parent": "RET-ADJ", "item_code": None, "qty": -1, "base_net_amount": -2400}],
    {"RET-ADJ": "INV-ADJ"},
    {},
    {},
) == {"RET-ADJ"}

adjustment_rows = [
    {"indent": 0, "sales_invoice": "ACC-SINV-5", "selling_amount": 1000, "buying_amount": 200},
    {"indent": 1, "parent_invoice": "ACC-SINV-5", "sales_invoice": "CURTAIN-5",
     "selling_amount": 1000, "buying_amount": 200},
    {"sales_invoice": "Total", "selling_amount": 1000, "buying_amount": 200},
]
module._append_price_adjustment_rows(
    adjustment_rows,
    {"ACC-SINV-5": [{"name": "RET-ADJ", "amount": -240}]},
)
module._recalculate_invoice_rows(
    adjustment_rows,
    {},
    {},
    {},
    {"ACC-SINV-5": [{"name": "RET-ADJ", "amount": -240}]},
)
invoice_row = next(row for row in adjustment_rows if row.get("sales_invoice") == "ACC-SINV-5")
total_row = next(row for row in adjustment_rows if row.get("sales_invoice") == "Total")
assert invoice_row["selling_amount"] == 760
assert invoice_row["buying_amount"] == 200
assert invoice_row["gross_profit"] == 560
assert total_row["selling_amount"] == 760
assert total_row["gross_profit"] == 560

grouped_result = {
    "columns": [{"fieldname": "customer"}],
    "result": [
        {"customer": "CUSTOMER", "selling_amount": 1000, "buying_amount": 600, "gross_profit": 400},
        {"customer": "Total", "selling_amount": 1000, "buying_amount": 600, "gross_profit": 400},
    ],
}
module._apply_grouped_total(
    grouped_result,
    {"selling_amount": 760, "buying_amount": 200, "gross_profit": 560},
)
grouped_total = grouped_result["result"][-1]
assert grouped_total["selling_amount"] == 760
assert grouped_total["buying_amount"] == 200
assert grouped_total["gross_profit"] == 560
assert grouped_total["gross_profit_%"] == round(560 / 760 * 100, 3)
print("PASS: amount-only credit keeps sold quantity and cost while reducing sales amount")
print("PASS: blank-item price adjustments are visible and deducted from invoice totals")
print("PASS: non-Invoice group totals also deduct blank-item price adjustments")
print("PASS: box sales use stock-UOM quantity for cost")
print("PASS: stock-UOM rows are not converted twice")
