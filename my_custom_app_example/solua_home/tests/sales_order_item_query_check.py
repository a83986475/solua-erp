from pathlib import Path


ROOT = Path(__file__).parents[1]
query_source = (ROOT / "api" / "sales_order_item_query.py").read_text(encoding="utf-8")
form_source = (ROOT / "public" / "js" / "sales_order_item_query_v20261014.js").read_text(encoding="utf-8")

assert "barcode_tbl.barcode == txt" in query_source
assert "barcode_tbl.barcode.like" not in query_source
assert 'field not in {"description", "item_group"}' in query_source
assert 'query: itemQuery' in form_source
assert '"Sales Order"' in form_source
print("PASS: Sales Order item query keeps fuzzy item fields and exact barcode matching")
