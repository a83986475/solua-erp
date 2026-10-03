from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
api = (ROOT / "api" / "mobile.py").read_text(encoding="utf-8")
page = (ROOT / "www" / "mobile" / "index.html").read_text(encoding="utf-8")
page_context = (ROOT / "www" / "mobile" / "index.py").read_text(encoding="utf-8")
manifest = (ROOT / "public" / "mobile" / "manifest.json").read_text(encoding="utf-8")

assert "System Manager" in api and "get_sales_order_color_variants" in api
assert "search_sales_order_items" in api and "Wholesale Selling 3" in api
assert "def search_customers" in api and "def get_customer_addresses" in api and "def save_sales_order" in api
assert "solua_home.api.mobile.lookup" in page
assert "批发价 1 级" in page and "批发价 3 级" in page
assert "new URLSearchParams" in page and "async function writeCall" in page
assert "mobile-suggestions" in page and "suggestionTimer" in page
assert "BarcodeDetector" in page and '"start_url": "/mobile"' in manifest
assert "mobile_order" in page_context and "view" in page_context
assert "mobile-order-only" in page and "view=order" in page
print("mobile admin checks passed")
