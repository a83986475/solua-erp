from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
api = (ROOT / "api" / "mobile.py").read_text(encoding="utf-8")
page = (ROOT / "www" / "mobile" / "index.html").read_text(encoding="utf-8")
manifest = (ROOT / "public" / "mobile" / "manifest.json").read_text(encoding="utf-8")

assert "System Manager" in api and "get_sales_order_color_variants" in api
assert "search_sales_order_items" in api and "Wholesale Selling 3" in api
assert "solua_home.api.mobile.lookup" in page
assert "批发价 1 级" in page and "批发价 3 级" in page
assert "BarcodeDetector" in page and '"start_url": "/mobile"' in manifest
print("mobile admin checks passed")
