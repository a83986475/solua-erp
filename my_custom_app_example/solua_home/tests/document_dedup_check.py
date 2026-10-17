"""Static contract checks for cross-surface draft reuse and duplicate guards."""

import ast
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
stock = (ROOT / "api" / "stock.py").read_text(encoding="utf-8-sig")
mobile = (ROOT / "api" / "mobile.py").read_text(encoding="utf-8-sig")
sales = (ROOT / "api" / "sales.py").read_text(encoding="utf-8-sig")
unbilled = (ROOT / "api" / "unbilled.py").read_text(encoding="utf-8-sig")
hooks = (ROOT / "hooks.py").read_text(encoding="utf-8-sig")
home = (ROOT / "solua_wholesale" / "page" / "solua_home" / "solua_home.js").read_text(encoding="utf-8-sig")

for source, functions in ((stock, {
    "get_existing_draft_delivery_note",
    "get_existing_draft_pick_list",
    "validate_single_draft_source",
    "make_delivery_note",
    "create_pick_list",
}), (unbilled, {"make_sales_invoice", "make_sales_invoice_from_sales_order"})):
    names = {node.name for node in ast.walk(ast.parse(source)) if isinstance(node, ast.FunctionDef)}
    assert functions <= names

assert "FOR UPDATE" in stock
assert "FOR UPDATE" in sales
assert "validate_single_draft_source" in stock
assert '"solua_home.api.stock.validate_single_draft_source"' in hooks
assert '"erpnext.selling.doctype.sales_order.mapper.make_delivery_note"' in hooks
assert '"erpnext.selling.doctype.sales_order.mapper.make_sales_invoice"' in hooks
assert '"erpnext.stock.doctype.delivery_note.mapper.make_sales_invoice"' in hooks
assert "get_existing_draft_delivery_note" in mobile
assert "get_existing_draft_pick_list" in mobile
assert "solua_home.api.stock.make_delivery_note" in home
assert "createDocument(\"solua_home.api.mobile.create_delivery_note\"" in (ROOT / "www" / "mobile" / "index.html").read_text(encoding="utf-8-sig")
print("PASS: desktop/mobile draft reuse and source-order locking contracts are wired")
