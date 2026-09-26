"""Site-free security and template checks for the A4 designer API."""

import importlib.util
import json
import pathlib
import sys
import types


BASE = pathlib.Path(__file__).resolve().parents[1]
api_source = (BASE / "api" / "a4_designer.py").read_text(encoding="utf-8")
fake = types.ModuleType("frappe")
fake.PermissionError = type("PermissionError", (Exception,), {})
fake._ = lambda text: text
fake.throw = lambda text, exc=None: (_ for _ in ()).throw((exc or ValueError)(text))
fake.parse_json = json.loads
fake.has_permission = lambda *args, **kwargs: True
fake.db = types.SimpleNamespace(exists=lambda *args: False, rollback=lambda: None)
fake.get_doc = lambda value, *args: types.SimpleNamespace(**value)
fake.get_print = lambda *args, **kwargs: '<table><colgroup><col ></colgroup></table>'
fake.get_list = lambda *args, **kwargs: []
fake.whitelist = lambda *args, **kwargs: lambda fn: fn
sys.modules["frappe"] = fake
spec = importlib.util.spec_from_file_location("a4_designer", BASE / "api" / "a4_designer.py")
api = importlib.util.module_from_spec(spec)
spec.loader.exec_module(api)


def config_for(doctype):
	keys = api.BASE_COLUMNS + api.DOCTYPE_CONFIG[doctype]
	visible = {key: key != "image" and not (doctype == "Delivery Note" and key == "qty") for key in keys}
	visible_count = sum(visible.values())
	return {
		"doctype": doctype,
		"visible": visible,
		"widths": {key: 100 / visible_count if visible[key] else 1 for key in keys},
		"settings": {"fontSize": 9, "titleSize": 18, "headSize": 9, "lineHeight": 1.35,
		             "cellPadding": 1.5, "pageMargin": 12, "titleColor": "#99732c", "headBg": "#f5f1e9"},
	}


for doctype in api.DOCTYPE_CONFIG:
	clean = api._validate_config(config_for(doctype))
	template = api._template(clean)
	assert template.count("<colgroup>") == template.count("</colgroup>") == 1
	assert template.count("<col data-col=") == sum(clean["visible"].values())
	assert "item.spu" in template
	assert "item.color_code or item.color or \"—\"" in template
	assert 'for item in p["items"]' in template
	assert '<div class="qty-total">' in template
	assert 'p.get("total_qty")' in template
	assert template.index("</table>") < template.index('class="qty-total"')
	assert clean["visible"]["spu"] is True
	if doctype != "Pick List":
		assert "format_print_money(item.rate)" in template
		assert "format_print_money(item.amount)" in template
		if doctype in ("Sales Order", "Sales Invoice"):
			assert "format_print_money(doc.grand_total, currency=doc.currency)" in template
			assert "{{ doc.currency }}" in template
			assert template.index('class="qty-total"') < template.index('class="total"')
	assert "MZN" not in template
	from jinja2 import Environment
	Environment().parse(template)
	if doctype == "Delivery Note":
		assert clean["visible"]["qty"] is False and "<th>Qt</th>" not in template

assert "A4_DESIGNER:v1:([A-Za-z0-9_-]+=*)" in api_source
assert '"total_qty": source.get("total_qty")' in api_source
assert '"sender": source.get("company")' in api_source
assert '"receiver": source.get("customer")' in api_source

assert api.COLUMN_LABELS["cor"] == "COR"
assert api.COLUMN_LABELS["qty"] == "Qt"
assert api.COLUMN_LABELS["rate"] == "Prc"

with_image = config_for("Sales Order")
with_image["visible"]["image"] = True
shown = [key for key, enabled in with_image["visible"].items() if enabled]
with_image["widths"] = {key: 100 / len(shown) if key in shown else 1 for key in with_image["widths"]}
assert "{% if item.image %}<img" in api._template(api._validate_config(with_image))

delivery = config_for("Delivery Note")
delivery["visible"].update(ordered=False, remaining=False)
visible = [key for key in api.BASE_COLUMNS + api.DOCTYPE_CONFIG["Delivery Note"] if delivery["visible"].get(key)]
visible.append("qty")
delivery["widths"] = {key: 100 / len(visible) if key in visible else 1 for key in delivery["widths"]}
delivery_template = api._template(api._validate_config(delivery))
assert "<th>Qt</th>" in delivery_template and "item.qty" in delivery_template
assert delivery_template.count("<th>Qt</th>") == 1

try:
	bad = config_for("Sales Order")
	bad["doctype"] = "Quotation"
	api._validate_config(bad)
	assert False, "unsupported doctype was accepted"
except ValueError:
	pass

try:
	bad = config_for("Sales Order")
	bad["settings"]["titleColor"] = "red; background:url(x)"
	api._validate_config(bad)
	assert False, "unsafe color was accepted"
except ValueError:
	pass

source = (BASE / "printing" / "a4_designer.py").read_text(encoding="utf-8")
assert '"custom_spu_code"' in source and '"variant_of"' in source
page = (BASE / "public" / "js" / "a4_print_designer.js").read_text(encoding="utf-8")
assert 'a4d-mock' in page and '"Delivery Note"' in page and '"Pick List"' in page

fake.has_permission = lambda *args, **kwargs: False
try:
	api.save_format("test", config_for("Sales Order"), "SO-1")
	assert False, "unauthorized creation was accepted"
except fake.PermissionError:
	pass

fake.has_permission = lambda *args, **kwargs: True
fake.db.exists = lambda *args: True
try:
	api.save_format("test", config_for("Sales Order"), "SO-1")
	assert False, "duplicate format name was accepted"
except ValueError:
	pass

print("A4 designer checks passed: supported doctypes, SPU source, delivery Qt fallback, Jinja structure, empty images, currency, validation, permissions, duplicate names")
