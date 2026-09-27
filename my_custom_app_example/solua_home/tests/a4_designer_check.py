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
		             "cellPadding": 1.5, "pageMargin": 12, "titleColor": "#99732c", "headBg": "#f5f1e9", "itemBorders": True},
	}


for doctype in api.DOCTYPE_CONFIG:
	clean = api._validate_config(config_for(doctype))
	template = api._template(clean)
	assert template.count("<colgroup>") == template.count("</colgroup>") == 1
	assert template.count("<col data-col=") == sum(clean["visible"].values())
	assert "item.spu" in template
	assert "item.color_code" in template and "item.color or item.color_code" not in template
	assert 'for item in p["items"]' in template
	assert '<div class="qty-total">' in template
	assert 'p.get("total_qty")' in template
	assert template.index("</table>") < template.index('class="qty-total"')
	assert clean["visible"]["spu"] is True
	assert clean["settings"]["itemBorders"] is True
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
assert 'frappe.get_print(doctype, name, print_format=format_doc.name, as_pdf=False)' in api_source
assert '"legacy_preview"' in api_source and '"legacy_importable"' in api_source
assert "company-logo" in api_source and "item_border" in api_source
assert "tbody tr{break-inside:avoid;page-break-inside:avoid}" in api_source

assert "cor" not in api.BASE_COLUMNS and "cor" not in api.COLUMN_LABELS
assert api.COLUMN_LABELS["color_code"] == "Cor"
assert api.COLUMN_LABELS["qty"] == "Qt/数量"
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
assert "<th>Qt/数量</th>" in delivery_template and "item.qty" in delivery_template
assert delivery_template.count("<th>Qt/数量</th>") == 1

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
assert 'legacy-preview' in page and 'import-format' in page and 'sandbox' in page and 'color_code' in page
assert 'cor: "COR"' not in page and '"color_code", "cor"' not in page
assert 'itemBorders' in page and 'Company Logo' in page
assert "tbody tr td{break-inside:avoid;page-break-inside:avoid}" in page
assert '"Delivery Note": ["ordered", "remaining", "qty", "uom"' in page

hooks = (BASE / "hooks.py").read_text(encoding="utf-8")
assert '"a4-print-designer": "public/js/a4_print_designer.js"' in hooks
assert "a4_print_designer.js?v=" not in hooks

known_legacy_html = """{{ get_solua_print_css() }}{% set p = get_wholesale_print_data(doc) %}
<table class="items">{% if doc.get('custom_print_item_name') %}{% endif %}
{% if doc.get('custom_print_color_code') %}{% endif %}{% if doc.get('custom_print_cor') %}{% endif %}
{% if doc.get('payment_schedule') %}{% endif %}{% if doc.get('custom_print_color_qr') %}{{ get_color_card_qr_img('TPL') }}{% endif %}
<div id="footer-html"></div></table>"""
unknown_legacy_html = "<table><tr><td>{{ doc.name }}</td></tr></table>"
assert api._format_mode("Sales Order", known_legacy_html) == "legacy_importable"
assert api._format_mode("Sales Order", unknown_legacy_html) == "legacy_preview"
legacy_format = types.SimpleNamespace(doc_type="Sales Order", html=known_legacy_html)
legacy_config = api._legacy_import_config(legacy_format)
assert legacy_config["version"] == 2
assert legacy_config["visible"]["image"] and legacy_config["visible"]["color_code"] and "cor" not in legacy_config["visible"]
assert abs(sum(legacy_config["widths"][key] for key, enabled in legacy_config["visible"].items() if enabled) - 100) < 0.01
assert legacy_config["features"]["payment_schedule"]
assert legacy_config["features"]["color_qr"] and legacy_config["features"]["footer"]
assert legacy_config["features"]["legacy_controls"]
assert legacy_config["settings"]["itemBorders"] is True
legacy_template = api._template(legacy_config)
from jinja2 import Environment
Environment().parse(legacy_template)
assert "get_color_card_qr_img" in legacy_template
assert "payment-schedule" in legacy_template
assert '<span class="page"></span>' in legacy_template

old_format_payload = json.loads((BASE / "print_format" / "sales_order_wholesale_color" / "sales_order_wholesale_color.json").read_text(encoding="utf-8"))
old_format = types.SimpleNamespace(doc_type=old_format_payload["doc_type"], html=old_format_payload["html"])
assert api._format_mode(old_format.doc_type, old_format.html) == "legacy_importable"
Environment().parse(old_format.html)
old_config = api._legacy_import_config(old_format)
assert old_config["features"]["payment_schedule"] and old_config["features"]["color_qr"] and old_config["features"]["footer"]
assert old_config["control_defaults"]["custom_print_color_images"] is False
assert old_config["control_defaults"]["custom_print_cor"] is False
Environment().parse(api._template(old_config))
old_payload = config_for("Sales Order")
old_payload["visible"]["cor"] = True
old_payload["widths"]["cor"] = 7
old_payload["widths"] = {key: value * 100 / (sum(old_payload["widths"].values())) for key, value in old_payload["widths"].items()}
clean_old_payload = api._validate_config(old_payload)
assert "cor" not in clean_old_payload["visible"] and "cor" not in clean_old_payload["widths"]
assert abs(sum(clean_old_payload["widths"][key] for key, enabled in clean_old_payload["visible"].items() if enabled) - 100) < 0.01
shared_data = {
	"company": {"name": "Solua Home", "nuit": "N", "address": "Company address", "phone": "111", "logo": "/files/company-logo.png"},
	"customer": {"name": "A Customer", "nuit": "C", "store": "Store 1", "address": "Customer street", "contact": "Contact", "phone": "111"},
	"legacy": False,
	"items": [{"item_name": "Curtain", "spu": "SPU-1", "item_code": "STYLE-01", "order_code": "STYLE-01", "color_code": "01", "color": "Red", "barcode": "6901234567892", "description": "Cortina vermelha", "image": "/red.png", "qty": 2, "uom": "条", "rate": 10, "amount": 20, "template_code": "STYLE"}],
	"total_qty": 2, "payment_method": "50/50", "deposit": 10, "balance_due_date": "2026-10-01", "invoice_plan": "签收后开票",
}
def _make_doc(**extra):
    base = {
        "name": "SO-1", "docstatus": 1, "currency": "MZN", "grand_total": 20,
        "posting_date": "2026-09-26", "transaction_date": "2026-09-26",
        "custom_customer_order_no": "CUST-1", "custom_wholesale_snapshot": None,
        "custom_print_color_images": 1, "custom_print_item_name": 1, "custom_print_sku": 1,
        "custom_print_color_code": 1, "custom_print_cor": 1, "custom_print_description": 1,
        "custom_print_color_qr": 1,
        "payment_schedule": [],
    }
    base.update(extra)
    class _Doc(dict):
        def get(self, key, default=None):
            return dict.get(self, key, default)
    return _Doc(base)

shared_doc = _make_doc()
render_env = Environment()
render_env.globals.update(
	get_wholesale_print_data=lambda doc: shared_data,
	get_a4_print_data=lambda doc: shared_data,
	get_solua_print_css=lambda: "",
	format_print_qty=lambda value: str(value or 0),
	format_print_money=lambda value, currency=None, precision=None: f"{value or 0:.0f} {currency or 'MZN'}",
	get_print_total_qty=lambda data: data["total_qty"],
	get_color_card_qr_img=lambda code: "QR_TEST",
)
legacy_rendered = render_env.from_string(old_format.html).render(doc=shared_doc)
imported_rendered = render_env.from_string(api._template(old_config)).render(doc=shared_doc)
for rendered in (legacy_rendered, imported_rendered):
	assert "Curtain" in rendered and "6901234567892" in rendered and "2" in rendered and "20 MZN" in rendered
assert "QR_TEST" in imported_rendered and "<span class=\"page\"></span>" in imported_rendered
assert "company-logo.png" in imported_rendered
border_off = dict(old_config)
border_off["settings"] = {**old_config["settings"], "itemBorders": False}
assert "border:0;" in api._template(api._validate_config(border_off))

server_doc = types.SimpleNamespace(name="SO-1", docstatus=1, get=lambda key, default=None: default)
server_format = types.SimpleNamespace(name="旧格式", doc_type="Sales Order", html=known_legacy_html, disabled=0,
	                                     print_format_type="Jinja", print_format_builder=0, custom_format=1, standard="No",
	                                     get=lambda key, default=None: getattr(server_format, key, default))
fake.get_doc = lambda doctype, name: server_format if doctype == "Print Format" else server_doc
fake.get_print = lambda *args, **kwargs: "<server-rendered-legacy-print>"
fake.db.get_value = lambda *args: known_legacy_html
fake.get_list = lambda *args, **kwargs: [{"name": "旧格式", "doc_type": "Sales Order", "print_format_type": "Jinja", "print_format_builder": 0, "disabled": 0, "custom_format": 1, "standard": "No"}]
listed_formats = api.list_formats("Sales Order")
assert listed_formats[0]["mode"] == "legacy_importable" and listed_formats[0]["print_format_type"] == "Jinja"
legacy_preview = api.get_preview("Sales Order", "SO-1", "旧格式")
assert legacy_preview["mode"] == "legacy_preview"
assert legacy_preview["html"] == "<server-rendered-legacy-print>"
loaded_legacy = api.load_config("旧格式")
assert loaded_legacy["mode"] == "legacy_importable" and loaded_legacy["can_import"]
assert loaded_legacy["config"]["features"]["color_qr"]

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

# --- A4 取数：公司 logo 必须缝在快照之上 -------------------------------
# 已提交单据的打印快照存于 logo 功能之前，company 里没有 logo；设计器模板会隐藏
# 共享 logo，所以这里不补就会打出一张没有公司标识的单子（草稿不走快照，容易漏测）。
sys.path.insert(0, str(BASE.parent))
provider = importlib.import_module("solua_home.printing.a4_designer")
wholesale = importlib.import_module("solua_home.printing.wholesale")

snapshot_company = {"name": "Solua Home, Lda", "nuit": "400", "address": "Av", "phone": "21"}
wholesale.get_wholesale_print_data = lambda doc: {"company": dict(snapshot_company), "items": [{"item_code": "SH1"}]}
wholesale.get_company_print_info = lambda doc: {**snapshot_company, "logo": "http://erp.solua.one/private/files/LOGO.png"}
fake.db.get_value = lambda *args, **kwargs: {"custom_spu_code": "SPU-1", "variant_of": "", "image": "/files/x.png"}

loaded = provider.get_a4_print_data(types.SimpleNamespace(doctype="Sales Order"))
assert loaded["company"]["logo"] == "http://erp.solua.one/private/files/LOGO.png"
assert loaded["company"]["name"] == "Solua Home, Lda" and loaded["company"]["nuit"] == "400"
assert loaded["items"][0]["spu"] == "SPU-1" and loaded["items"][0]["image"] == "/files/x.png"

# 没有 logo 配置时不能凭空造一个，也不能把 company 整个丢掉
wholesale.get_company_print_info = lambda doc: dict(snapshot_company)
fake.db.get_value = lambda doctype, name, fieldname, **kwargs: ""
loaded = provider.get_a4_print_data(types.SimpleNamespace(doctype="Sales Order", get=lambda key, default=None: None))
assert loaded["company"]["name"] == "Solua Home, Lda" and loaded["company"].get("logo") in (None, "")

# 拣货单同样走 get_company_print_info（没有快照）
wholesale.get_pick_list_print_data = lambda doc: {"company": "ignored", "items": [], "total_qty": 0}
wholesale.get_company_print_info = lambda doc: {"name": "Solua Home, Lda", "logo": "http://erp.solua.one/private/files/LOGO.png"}
assert provider.get_a4_print_data(types.SimpleNamespace(doctype="Pick List"))["company"]["logo"].endswith("LOGO.png")

print("A4 designer checks passed: supported doctypes, SPU source, delivery Qt fallback, Jinja structure, empty images, currency, validation, permissions, duplicate names, snapshot company logo")
