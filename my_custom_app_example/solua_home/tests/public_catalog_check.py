"""Static guard for the guest catalog contract."""
from pathlib import Path


SOURCE = Path(__file__).resolve().parents[1] / "api" / "color_card.py"
text = SOURCE.read_text(encoding="utf-8")

assert "def get_public_catalog(" in text
assert '"custom_color_card_published": 1' in text
assert '"logo": "/files/solua-logo.jpg"' in text
assert 'frappe.conf.get("public_site_url")' in text
catalog = text[text.index("def get_public_catalog("):]
assert "standard_rate" not in catalog
assert "price_list_rate" not in catalog
assert "valuation_rate" not in catalog
print("PASS: public catalog is publication-gated and price-free")
