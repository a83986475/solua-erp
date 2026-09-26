"""Restricted data and native Print Format persistence for the A4 designer."""

import base64
import json
import re

import frappe
from frappe import _


DOCTYPE_CONFIG = {
    "Sales Order": ["qty", "uom", "rate", "amount"],
    "Sales Invoice": ["qty", "uom", "rate", "amount"],
    "Delivery Note": ["ordered", "remaining", "qty", "uom", "rate", "amount", "trace"],
    "Pick List": ["qty", "picked", "uom", "warehouse", "order"],
}
BASE_COLUMNS = ["image", "name", "spu", "sku", "color_code", "cor", "barcode", "description"]
COLUMN_LABELS = {
    "image": "FOTO", "name": "Artigo / 商品", "spu": "SPU", "sku": "SKU / 货号",
    "color_code": "Código de cor fixo / 固定色号",
    "cor": "COR", "barcode": "EAN / 条码", "description": "Descrição / 描述",
    "ordered": "Qt. pedido / 已订购", "remaining": "Qt. restante / 剩余",
    "qty": "Qt", "picked": "Qt separado / 已拣", "uom": "Un.", "rate": "Prc",
    "amount": "Valor / 金额", "trace": "Rastreabilidade / 追溯",
    "warehouse": "Armazém / 仓库", "order": "S.O. / 订单",
}
FORMAT_META = "<!--SOLUA_A4_DESIGNER:v1:{}-->"
NAME_RE = re.compile(r"^[^/\\\x00-\x1f]{1,140}$")
HEX_RE = re.compile(r"^#[0-9a-fA-F]{6}$")
FORMAT_META_RE = re.compile(r"<!--SOLUA_A4_DESIGNER:v1:([A-Za-z0-9_-]+=*)-->")
FEATURE_DEFAULTS = {
	"payment_schedule": False,
	"color_qr": False,
	"footer": True,
	"legacy_warning": False,
	"legacy_controls": False,
}
CONTROL_DEFAULTS = {
	"custom_print_color_images": True,
	"custom_print_item_name": True,
	"custom_print_sku": True,
	"custom_print_color_code": True,
	"custom_print_cor": True,
	"custom_print_description": True,
}
LEGACY_IMPORT_MARKERS = (
	"get_wholesale_print_data(doc)",
	"custom_print_item_name",
	"custom_print_color_code",
)
LEGACY_ITEMS_RE = re.compile(r"<table\b[^>]*\bclass\s*=\s*['\"][^'\"]*\bitems\b", re.IGNORECASE)


def _allowed_doctype(doctype):
	if doctype not in DOCTYPE_CONFIG:
		frappe.throw(_("Unsupported document type"))


def _can_save():
	return frappe.has_permission("Print Format", ptype="create")


def _items_for(doc):
	from solua_home.printing.a4_designer import get_a4_print_data
	return get_a4_print_data(doc).get("items", [])


def _is_known_legacy_format(doctype, html):
	return doctype == "Sales Order" and all(marker in (html or "") for marker in LEGACY_IMPORT_MARKERS) and LEGACY_ITEMS_RE.search(html or "")


def _format_mode(doctype, html):
	if FORMAT_META_RE.search(html or ""):
		return "designer"
	if _is_known_legacy_format(doctype, html):
		return "legacy_importable"
	return "legacy_preview"


def _legacy_unsupported_features(doctype, html):
	"""Return only features that the compatibility template really cannot preserve."""
	text = html or ""
	unsupported = []
	if doctype != "Sales Order" and "get_wholesale_print_data(doc)" in text:
		unsupported.append("非销售订单的 Wholesale 专用逻辑")
	return unsupported


def _format_summary(row, html=""):
	doctype = row.get("doc_type") or row.get("doctype") or ""
	mode = _format_mode(doctype, html)
	return {
		"name": row.get("name"),
		"doctype": doctype,
		"mode": mode,
		"print_format_type": row.get("print_format_type") or "Jinja",
		"print_format_builder": row.get("print_format_builder") or 0,
		"disabled": int(row.get("disabled") or 0),
		"custom_format": int(row.get("custom_format") or 0),
		"standard": row.get("standard") or "No",
		"can_import": mode == "legacy_importable",
		"unsupported_features": _legacy_unsupported_features(doctype, html),
	}


@frappe.whitelist()
def get_access():
	return {"can_save": bool(_can_save()), "doctypes": list(DOCTYPE_CONFIG)}


@frappe.whitelist()
def get_documents(doctype):
	_allowed_doctype(doctype)
	if not frappe.has_permission(doctype, ptype="read"):
		frappe.throw(_("Not permitted"), frappe.PermissionError)
	return frappe.get_list(doctype, fields=["name"], order_by="modified desc", page_length=50)


def _get_print_format(name, doctype):
	if not frappe.has_permission("Print Format", ptype="read"):
		frappe.throw(_("Print Format read permission is required"), frappe.PermissionError)
	print_format = frappe.get_doc("Print Format", name)
	if print_format.doc_type != doctype:
		frappe.throw(_("Print Format does not belong to this document type"))
	if print_format.disabled:
		frappe.throw(_("This Print Format is disabled"))
	return print_format


@frappe.whitelist()
def get_preview(doctype, name, print_format=None):
	_allowed_doctype(doctype)
	doc = frappe.get_doc(doctype, name)
	if not frappe.has_permission(doc=doc, ptype="read"):
		frappe.throw(_("Not permitted"), frappe.PermissionError)
	if not frappe.has_permission("Item", ptype="read"):
		frappe.throw(_("Item read permission is required"), frappe.PermissionError)
	if print_format:
		format_doc = _get_print_format(print_format, doctype)
		try:
			rendered = frappe.get_print(doctype, name, print_format=format_doc.name, as_pdf=False)
		except Exception as exc:
			frappe.throw(_("Legacy Print Format preview failed: {0}").format(str(exc)))
		return {
			"mode": "legacy_preview",
			"name": name,
			"doctype": doctype,
			"print_format": _format_summary(format_doc, format_doc.html or ""),
			"html": rendered,
		}
	from solua_home.printing.a4_designer import get_a4_print_data
	source = get_a4_print_data(doc)
	data = []
	qr_items = []
	seen_qr = set()
	for row in source.get("items", []):
		item_code = row.get("item_code")
		item = frappe.db.get_value("Item", item_code, ["custom_spu_code", "variant_of", "image"], as_dict=True) or {}
		spu = item.get("custom_spu_code")
		if not spu and item.get("variant_of"):
			spu = frappe.db.get_value("Item", item.variant_of, "custom_spu_code")
		out = dict(row)
		out["spu"] = spu or ""
		image = out.get("image") or item.get("image") or ""
		out["image"] = image if image.startswith(("/files/", "/private/files/")) else ""
		out["trace"] = row.get("batch_no") or row.get("serial_no") or row.get("serial_and_batch_bundle") or ""
		out["ordered"] = row.get("ordered_qty") or ""
		out["remaining"] = row.get("remaining_qty") or ""
		out["picked"] = row.get("picked_qty") or ""
		out["order"] = row.get("sales_order") or doc.get("sales_order") or ""
		data.append(out)
		template_code = row.get("template_code") or ""
		if template_code and template_code not in seen_qr:
			seen_qr.add(template_code)
			from solua_home.printing.color_card import get_color_card_qr_img
			qr = get_color_card_qr_img(template_code)
			if qr:
				qr_items.append({"template_code": template_code, "image": qr})
	return {
		"mode": "designer", "doctype": doctype, "name": doc.name, "title": doc.get("customer_name") or doc.get("customer") or doc.name,
		"date": str(doc.get("posting_date") or doc.get("transaction_date") or doc.get("posting_date")),
		"currency": doc.get("currency") or "", "total": doc.get("grand_total") or "",
		"total_qty": source.get("total_qty") or sum(row.get("qty") or 0 for row in data),
		"sender": source.get("company") or {}, "receiver": source.get("customer") or {},
		"docstatus": doc.get("docstatus") or 0, "customer_order_no": doc.get("custom_customer_order_no") or "",
		"delivery_date": doc.get("delivery_date") or "", "payment_method": source.get("payment_method") or "",
		"deposit": source.get("deposit") or 0, "balance_due_date": source.get("balance_due_date") or "",
		"invoice_plan": source.get("invoice_plan") or "",
		"payment_schedule": [{"payment_term": row.get("payment_term") or "", "due_date": row.get("due_date") or "", "payment_amount": row.get("payment_amount") or 0} for row in doc.get("payment_schedule") or []],
		"qr_items": qr_items,
		"items": data,
	}


def _validate_config(config):
	if isinstance(config, str):
		config = frappe.parse_json(config)
	if not isinstance(config, dict):
		frappe.throw(_("Invalid design configuration"))
	doctype = config.get("doctype")
	_allowed_doctype(doctype)
	allowed = set(BASE_COLUMNS + DOCTYPE_CONFIG[doctype])
	visible = config.get("visible")
	widths = config.get("widths")
	if not isinstance(visible, dict) or not isinstance(widths, dict):
		frappe.throw(_("Invalid columns"))
	if set(visible) - allowed or set(widths) - allowed:
		frappe.throw(_("Unknown column"))
	if any(key in visible and not isinstance(visible[key], bool) for key in allowed):
		frappe.throw(_("Invalid column toggle"))
	clean_visible = {
		key: visible.get(key, key not in ("image", "color_code") and not (doctype == "Delivery Note" and key == "qty"))
		for key in allowed
	}
	clean_widths = {}
	for key in allowed:
		value = widths.get(key, 10)
		if isinstance(value, bool) or not isinstance(value, (int, float)) or not 0 < value <= 100:
			frappe.throw(_("Invalid column width"))
		clean_widths[key] = float(value)
	settings = config.get("settings")
	if not isinstance(settings, dict):
		frappe.throw(_("Invalid layout settings"))
	clean_settings = {}
	for key, low, high in (("fontSize", 7, 13), ("titleSize", 12, 26), ("headSize", 6, 14),
	                       ("lineHeight", 1, 2), ("cellPadding", 0.5, 3), ("pageMargin", 5, 20)):
		value = settings.get(key)
		if isinstance(value, bool) or not isinstance(value, (int, float)) or not low <= value <= high:
			frappe.throw(_("Invalid layout setting: {0}").format(key))
		clean_settings[key] = float(value)
	for key in ("titleColor", "headBg"):
		value = settings.get(key)
		if not isinstance(value, str) or not HEX_RE.fullmatch(value):
			frappe.throw(_("Invalid color"))
		clean_settings[key] = value.lower()
	item_borders = settings.get("itemBorders", True)
	if not isinstance(item_borders, bool):
		frappe.throw(_("Invalid layout setting: itemBorders"))
	clean_settings["itemBorders"] = item_borders
	features = config.get("features") or {}
	if not isinstance(features, dict) or set(features) - set(FEATURE_DEFAULTS):
		frappe.throw(_("Unknown feature"))
	if any(not isinstance(features.get(key, default), bool) for key, default in FEATURE_DEFAULTS.items()):
		frappe.throw(_("Invalid feature toggle"))
	clean_features = {key: bool(features.get(key, default)) for key, default in FEATURE_DEFAULTS.items()}
	control_defaults = config.get("control_defaults") or {}
	if not isinstance(control_defaults, dict) or set(control_defaults) - set(CONTROL_DEFAULTS):
		frappe.throw(_("Unknown print control"))
	if any(not isinstance(control_defaults.get(key, default), bool) for key, default in CONTROL_DEFAULTS.items()):
		frappe.throw(_("Invalid print control"))
	clean_control_defaults = {key: bool(control_defaults.get(key, default)) for key, default in CONTROL_DEFAULTS.items()}
	version = config.get("version") or 1
	if isinstance(version, bool) or not isinstance(version, int) or version not in (1, 2):
		frappe.throw(_("Invalid design configuration version"))
	return {"version": max(version, 2 if features else 1), "doctype": doctype, "visible": clean_visible,
			"widths": clean_widths, "settings": clean_settings, "features": clean_features,
			"control_defaults": clean_control_defaults}


def _template(config):
	doctype = config["doctype"]
	features = config.get("features") or {}
	legacy_controls = bool(features.get("legacy_controls"))
	keys = [key for key in BASE_COLUMNS + DOCTYPE_CONFIG[doctype] if config["visible"].get(key)]
	if doctype == "Delivery Note" and not any(key in keys for key in ("ordered", "remaining")) and "qty" not in keys:
		keys.append("qty")
	if not keys:
		frappe.throw(_("At least one column must be visible"))
	if abs(sum(config["widths"][key] for key in keys) - 100) > 0.15:
		frappe.throw(_("Visible column widths must total 100%"))
	meta = base64.urlsafe_b64encode(json.dumps(config, separators=(",", ":")).encode()).decode()
	labels = {key: COLUMN_LABELS[key] for key in keys}
	widths = config["widths"]
	conditional_fields = {
		"image": "show_images", "name": "show_item_name", "sku": "show_sku",
		"color_code": "show_color_code", "cor": "show_cor", "description": "show_description",
	}
	def conditional(key, fragment):
		field = conditional_fields.get(key)
		return f"{{% if {field} %}}{fragment}{{% endif %}}" if legacy_controls and field else fragment
	cols = "".join(conditional(key, f'<col data-col="{key}" style="width:{widths[key]:.3f}%">') for key in keys)
	headers = "".join(conditional(key, f'<th>{labels[key]}</th>') for key in keys)
	cell_map = {
		"image": '<td>{% if item.image %}<img class="photo" src="{{ item.image | e }}">{% endif %}</td>',
		"name": '<td>{{ (item.item_name or "—") | e }}</td>', "spu": '<td>{{ (item.spu or "—") | e }}</td>',
		"sku": '<td>{{ (item.order_code or item.item_code or "—") | e }}</td>',
		"color_code": '<td>{{ (item.color_code or "—") | e }}</td>', "cor": '<td>{{ (item.color or item.color_code or "—") | e }}</td>',
		"barcode": '<td>{{ item.barcode | e }}</td>', "description": '<td>{{ item.description | e }}</td>',
		"ordered": '<td>{{ item.ordered_qty or "—" }}</td>', "remaining": '<td>{{ item.remaining_qty or "—" }}</td>',
		"qty": '<td>{{ format_print_qty(item.qty) }}</td>', "picked": '<td>{{ format_print_qty(item.picked_qty) }}</td>',
		"uom": '<td>{{ item.uom | e }}</td>', "rate": '<td>{{ format_print_money(item.rate) }}</td>',
		"amount": '<td>{{ format_print_money(item.amount) }}</td>',
		"trace": '<td>{{ (item.batch_no or item.serial_no or item.serial_and_batch_bundle or "—") | e }}</td>',
		"warehouse": '<td>{{ item.warehouse | e }}</td>', "order": '<td>{{ item.sales_order | e }}</td>',
	}
	cells = "".join(conditional(key, cell_map[key]) for key in keys)
	provider = "get_a4_print_data(doc)"
	items = 'p["items"]'
	title = {"Sales Order": "Confirmação de Encomenda / 订单确认单", "Sales Invoice": "Venda / 销售单",
	         "Delivery Note": "Guia de Remessa / 送货单", "Pick List": "Lista de Separação / 拣货单"}[doctype]
	settings = config["settings"]
	item_border = "1px solid #aeb8be" if settings.get("itemBorders", True) else "0"
	css = (f'@page{{size:A4;margin:0}} .print-format{{width:210mm;min-height:297mm;padding:{settings["pageMargin"]}mm;box-sizing:border-box;color:#25313a;font-size:{settings["fontSize"]}pt;overflow-wrap:anywhere}}'
	       f'h1{{font-size:{settings["titleSize"]}pt;color:{settings["titleColor"]}}}.items{{width:100%;table-layout:fixed;border-collapse:collapse;font-size:{settings["fontSize"]}pt;line-height:{settings["lineHeight"]}}}'
	       f'.items th{{font-size:{settings["headSize"]}pt;background:{settings["headBg"]}}}.items th,.items td{{padding:{settings["cellPadding"]}mm;border:{item_border};vertical-align:top;overflow-wrap:anywhere}}'
	       '.items thead{display:table-header-group}.items tr{break-inside:avoid}.photo{display:block;width:min(12mm,100%);aspect-ratio:1;object-fit:cover}.company-header{position:relative;min-height:18mm;padding-left:30mm}.company-logo{position:absolute;left:0;top:0;width:25mm;max-height:16mm;object-fit:contain}.company-header h2{margin:0;text-align:center}.parties{width:100%;border-collapse:collapse;margin:10px 0}.parties td{width:50%;padding:2mm;border:1px solid #aeb8be;vertical-align:top}.warning{color:#a35c00;margin:3mm 0}.block{page-break-inside:avoid;margin-top:12px}.qty-total,.total{width:100%;display:block;clear:both;box-sizing:border-box;text-align:right;font-weight:700;margin-top:3mm}.total{font-size:10pt}.footer{text-align:center;margin-top:8mm;color:#52606a}.payment-schedule th,.payment-schedule td{padding:1.5mm;border:1px solid #aeb8be}.color-qr{display:flex;gap:6mm;flex-wrap:wrap}.color-qr img{height:18mm;width:18mm}')
	css += '.solua-global-logo{display:none!important}.print-format table.items th,.print-format table.items td{border:' + item_border + ' !important;}'
	controls = ""
	if legacy_controls:
		control_defaults = config.get("control_defaults") or CONTROL_DEFAULTS
		controls = (f"{{% set show_images = doc.get('custom_print_color_images') if doc.get('custom_print_color_images') is not none else {int(control_defaults['custom_print_color_images'])} %}}"
			f"{{% set show_item_name = doc.get('custom_print_item_name') if doc.get('custom_print_item_name') is not none else {int(control_defaults['custom_print_item_name'])} %}}"
			f"{{% set show_sku = doc.get('custom_print_sku') if doc.get('custom_print_sku') is not none else {int(control_defaults['custom_print_sku'])} %}}"
			f"{{% set show_color_code = doc.get('custom_print_color_code') if doc.get('custom_print_color_code') is not none else {int(control_defaults['custom_print_color_code'])} %}}"
			f"{{% set show_cor = doc.get('custom_print_cor') if doc.get('custom_print_cor') is not none else {int(control_defaults['custom_print_cor'])} %}}"
			f"{{% set show_description = doc.get('custom_print_description') if doc.get('custom_print_description') is not none else {int(control_defaults['custom_print_description'])} %}}")
	warning = "{% if p.get('legacy') %}<div class=\"warning\">历史单据未保存打印快照；补充资料来自当前主档。</div>{% endif %}" if features.get("legacy_warning") else ""
	payment = '<div class="block">Plano de pagamento / 付款安排: {{ p.get("payment_method") or "未维护" | e }} · Depósito / 定金: {{ format_print_money(p.get("deposit"), currency=doc.currency) }} · Vencimento do saldo / 尾款到期: {{ p.get("balance_due_date") or "—" | e }}<br>Plano de faturação / 开票安排: {{ p.get("invoice_plan") or "未维护" | e }}</div>'
	if features.get("payment_schedule"):
		payment += '<table class="payment-schedule"><thead><tr><th>Condições de pagamento / 付款条件</th><th>Data de vencimento / 到期日</th><th>Valor / 金额</th></tr></thead><tbody>{% for row in doc.get("payment_schedule") or [] %}<tr><td>{{ row.payment_term or "" | e }}</td><td>{{ row.due_date or "" }}</td><td>{{ format_print_money(row.payment_amount, currency=doc.currency) }}</td></tr>{% endfor %}</tbody></table>'
	qr = ""
	if features.get("color_qr"):
		qr_condition = "doc.get('custom_print_color_qr')" if legacy_controls else "true"
		qr = ('{% if ' + qr_condition + ' %}{% set seen = [] %}<div class="block color-qr">'
			"{% for item in p['items'] %}{% if item.template_code and item.template_code not in seen %}{% set unused = seen.append(item.template_code) %}"
			'{% set qr = get_color_card_qr_img(item.template_code) %}{% if qr %}<div><img src="{{ qr | e }}"><br>{{ item.template_code | e }}</div>{% endif %}{% endif %}{% endfor %}</div>{% endif %}')
	footer = '<div id="footer-html" class="visible-pdf"><div class="text-center">{{ doc.name | e }} · <span class="page"></span> / <span class="topage"></span></div></div>' if features.get("footer") else ""
	return (FORMAT_META.format(meta) + "{{ get_solua_print_css() }}<style>" + css + "</style>" + controls
	        + f"{{% set p = {provider} %}}{{% set company = p.get('company') or {{}} %}}{{% set customer = p.get('customer') or {{}} %}}"
	        + '<div class="company-header">{% if company.get("logo") %}<img class="company-logo" src="{{ company.logo | e }}" alt="Company Logo">{% endif %}<h2>' + title + '</h2></div>'
	        + "{% if doc.docstatus != 1 %}<div class=\"warning\">{{ 'RASCUNHO / 草稿' if doc.docstatus == 0 else 'CANCELADO / 已取消' }} — Documento não oficial / 非正式凭证</div>{% endif %}" + warning
	        + "<table class=\"parties\"><tr><td><b>{{ company.name | e }}</b><br>NUIT: {{ company.nuit | e }}<br>{{ company.address }}<br>Tel: {{ company.phone | e }}</td><td><b>Cliente / 客户: {{ customer.name | e }}</b><br>NUIT: {{ customer.nuit or 'Não informado / 未提供' | e }}<br>Loja / 门店: {{ customer.store | e }}<br>{{ customer.address }}<br>{{ customer.contact }} · {{ customer.phone | e }}</td></tr><tr><td>N.º / 编号: {{ doc.name | e }}<br>N.º encomenda cliente / 客户订单号: {{ doc.get('custom_customer_order_no') or '—' | e }}</td><td>Data / 日期: {{ doc.get('posting_date') or doc.get('transaction_date') }}<br>Prazo de entrega / 交期: {{ doc.get('delivery_date') or '—' }}</td></tr></table>"
	        + f'<table class="items"><colgroup>{cols}</colgroup><thead><tr><th colspan="{len(keys)}">{{{{ doc.name | e }}}} · 订购 / Encomenda</th></tr><tr>{headers}</tr></thead><tbody>{{% for item in {items} %}}<tr>{cells}</tr>{{% endfor %}}</tbody></table>'
	        + '<div class="qty-total">Total Qty / 总数量: {{ format_print_qty(p.get("total_qty") or 0) }}</div>'
	        + ("<div class=\"total\">Total / 含税合计: {{ format_print_money(doc.grand_total, currency=doc.currency) }} {{ doc.currency }}</div>" if doctype in ("Sales Order", "Sales Invoice") else "")
	        + payment + qr + footer)


def _legacy_import_config(print_format):
	doctype = print_format.doc_type
	html = print_format.html or ""
	if not _is_known_legacy_format(doctype, html):
		return None
	def control_default(field, fallback):
		match = re.search(rf"custom_print_{re.escape(field)}[^}}\n]*?else\s+([01])", html)
		return bool(int(match.group(1))) if match else fallback
	config = {
		"version": 2,
		"doctype": doctype,
		"visible": {key: True for key in BASE_COLUMNS + DOCTYPE_CONFIG[doctype]},
		"widths": {
			"image": 7, "name": 12, "spu": 8, "sku": 12, "color_code": 8, "cor": 7,
			"barcode": 11, "description": 16, "qty": 5, "uom": 5, "rate": 4, "amount": 5,
		},
		"settings": {
			"fontSize": 9, "titleSize": 18, "headSize": 9, "lineHeight": 1.35,
			"cellPadding": 1.5, "pageMargin": 12, "titleColor": "#99732c", "headBg": "#f5f1e9", "itemBorders": True,
		},
		"features": {
			"payment_schedule": "payment_schedule" in html,
			"color_qr": "get_color_card_qr_img" in html,
			"footer": "footer-html" in html,
			"legacy_warning": "p.get('legacy')" in html or 'p.get("legacy")' in html,
			"legacy_controls": "custom_print_" in html,
		},
		"control_defaults": {
			"custom_print_color_images": control_default("color_images", False),
			"custom_print_item_name": control_default("item_name", True),
			"custom_print_sku": control_default("sku", True),
			"custom_print_color_code": control_default("color_code", True),
			"custom_print_cor": control_default("cor", False),
			"custom_print_description": control_default("description", True),
		},
	}
	return _validate_config(config)


def _legacy_load_payload(print_format):
	base = _format_summary(print_format, print_format.html or "")
	base["name"] = print_format.name
	base["doctype"] = print_format.doc_type
	if base["mode"] == "legacy_importable":
		config = _legacy_import_config(print_format)
		return {**base, "can_import": True, "config": config, "warning": ""}
	return {
		**base,
		"can_import": False,
		"warning": "这是旧版 Jinja 格式，可以预览，但尚未转换为可视化格式。",
	}


@frappe.whitelist()
def list_formats(doctype):
	_allowed_doctype(doctype)
	if not frappe.has_permission("Print Format", ptype="read"):
		return []
	rows = frappe.get_list("Print Format", filters={"doc_type": doctype},
	                      fields=["name", "doc_type", "print_format_type", "print_format_builder", "disabled", "custom_format", "standard"],
	                      order_by="modified desc", page_length=100)
	result = []
	for row in rows:
		html = frappe.db.get_value("Print Format", row.get("name"), "html") or ""
		result.append(_format_summary(row, html))
	return result


@frappe.whitelist()
def load_config(name):
	doc = frappe.get_doc("Print Format", name)
	if not frappe.has_permission(doc=doc, ptype="read"):
		frappe.throw(_("Not permitted"), frappe.PermissionError)
	_allowed_doctype(doc.doc_type)
	mode = _format_mode(doc.doc_type, doc.html or "")
	if mode != "designer":
		return _legacy_load_payload(doc)
	match = FORMAT_META_RE.search(doc.html or "")
	if not match:
		frappe.throw(_("Saved design metadata is invalid"))
	try:
		return _validate_config(base64.urlsafe_b64decode(match.group(1)).decode())
	except (ValueError, TypeError, UnicodeError):
		frappe.throw(_("Saved design configuration is invalid"))


@frappe.whitelist()
def save_format(name, config, sample_name):
	if not _can_save():
		frappe.throw(_("Print Format create permission is required"), frappe.PermissionError)
	config = _validate_config(config)
	name = (name or "").strip()
	if not NAME_RE.fullmatch(name):
		frappe.throw(_("Invalid Print Format name"))
	if frappe.db.exists("Print Format", name):
		frappe.throw(_("A Print Format with this name already exists"))
	doctype = config["doctype"]
	sample = frappe.get_doc(doctype, sample_name)
	if not frappe.has_permission(doc=sample, ptype="read"):
		frappe.throw(_("Not permitted"), frappe.PermissionError)
	if not frappe.has_permission("Item", ptype="read"):
		frappe.throw(_("Item read permission is required"), frappe.PermissionError)
	content = _template(config)
	from jinja2 import Environment
	Environment().parse(content)
	try:
		doc = frappe.get_doc({"doctype": "Print Format", "name": name, "doc_type": doctype,
		                      "module": "Solua Wholesale", "custom_format": 1, "standard": "No",
		                      "disabled": 0, "print_format_type": "Jinja", "html": content, "css": ""})
		doc.insert()
		stored = frappe.get_doc("Print Format", name)
		if stored.html != content:
			frappe.throw(_("Print Format readback did not match"))
		rendered = frappe.get_print(doctype, sample_name, print_format=name, as_pdf=False)
		expected_keys = [key for key in BASE_COLUMNS + DOCTYPE_CONFIG[doctype] if config["visible"].get(key)]
		if config["features"].get("legacy_controls"):
			control_fields = {"image": "custom_print_color_images", "name": "custom_print_item_name", "sku": "custom_print_sku",
				"color_code": "custom_print_color_code", "cor": "custom_print_cor", "description": "custom_print_description"}
			expected_keys = [key for key in expected_keys if key not in control_fields or bool(sample.get(control_fields[key]) if sample.get(control_fields[key]) is not None else 1)]
		if doctype == "Delivery Note" and not any(key in expected_keys for key in ("ordered", "remaining", "qty")):
			expected_keys.append("qty")
		if (not rendered or rendered.count("<colgroup>") != 1 or rendered.count("</colgroup>") != 1
				or rendered.count("<col ") != len(expected_keys)):
			frappe.throw(_("Rendered print output is invalid"))
		return {"name": name, "doctype": doctype}
	except Exception:
		frappe.db.rollback()
		raise
