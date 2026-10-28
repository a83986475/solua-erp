from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
api = (ROOT / "api" / "assistant.py").read_text(encoding="utf-8")

assert "@frappe.whitelist()" in api
assert "@frappe.read_only()" in api
assert "allow_guest=True" not in api
assert "frappe.get_list" in api
assert "frappe.get_doc" in api and 'doc.check_permission("read")' in api
assert '"Item Barcode"' in api and 'filters={"barcode": query}' in api
assert '"Bin"' in api and "available_qty" in api
assert '"Sales Order"' in api and '"Delivery Note Item"' in api
assert '"Pick List Item"' in api and '"Sales Invoice Item"' in api
assert "get_capabilities" in api
assert "def search_items" in api
assert "def get_stock" in api
assert "def search_customers" in api
assert "def list_sales_orders" in api
assert "def get_sales_order" in api
assert "def get_sales_order_chain" in api
assert "frappe.db.sql" not in api
assert "execute" not in api
print("assistant API checks passed")
