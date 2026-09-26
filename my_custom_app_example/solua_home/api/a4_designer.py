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
BASE_COLUMNS = ["image", "name", "spu", "sku", "cor", "barcode", "description"]
COLUMN_LABELS = {
    "image": "FOTO", "name": "Artigo / 商品", "spu": "SPU", "sku": "SKU / 货号",
    "cor": "COR", "barcode": "EAN / 条码", "description": "Descrição / 描述",
    "ordered": "Qt. pedido / 已订购", "remaining": "Qt. restante / 剩余",
    "qty": "Qt", "picked": "Qt separado / 已拣", "uom": "Un.", "rate": "Prc",
    "amount": "Valor / 金额", "trace": "Rastreabilidade / 追溯",
    "warehouse": "Armazém / 仓库", "order": "S.O. / 订单",
}
FORMAT_META = "<!--SOLUA_A4_DESIGNER:v1:{}-->"
NAME_RE = re.compile(r"^[^/\\\x00-\x1f]{1,140}$")
HEX_RE = re.compile(r"^#[0-9a-fA-F]{6}$")


def _allowed_doctype(doctype):
	if doctype not in DOCTYPE_CONFIG:
		frappe.throw(_("Unsupported document type"))


def _can_save():
	return frappe.has_permission("Print Format", ptype="create")


def _items_for(doc):
	from solua_home.printing.a4_designer import get_a4_print_data
	return get_a4_print_data(doc).get("items", [])


@frappe.whitelist()
def get_access():
	return {"can_save": bool(_can_save()), "doctypes": list(DOCTYPE_CONFIG)}


@frappe.whitelist()
def get_documents(doctype):
	_allowed_doctype(doctype)
	if not frappe.has_permission(doctype, ptype="read"):
		frappe.throw(_("Not permitted"), frappe.PermissionError)
	return frappe.get_list(doctype, fields=["name"], order_by="modified desc", page_length=50)


@frappe.whitelist()
def get_preview(doctype, name):
	_allowed_doctype(doctype)
	doc = frappe.get_doc(doctype, name)
	if not frappe.has_permission(doc=doc, ptype="read"):
		frappe.throw(_("Not permitted"), frappe.PermissionError)
	if not frappe.has_permission("Item", ptype="read"):
		frappe.throw(_("Item read permission is required"), frappe.PermissionError)
	from solua_home.printing.a4_designer import get_a4_print_data
	source = get_a4_print_data(doc)
	data = []
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
	return {
		"doctype": doctype, "name": doc.name, "title": doc.get("customer_name") or doc.get("customer") or doc.name,
		"date": str(doc.get("posting_date") or doc.get("transaction_date") or doc.get("posting_date")),
		"currency": doc.get("currency") or "", "total": doc.get("grand_total") or "",
		"total_qty": source.get("total_qty") or sum(row.get("qty") or 0 for row in data),
		"sender": source.get("company") or {}, "receiver": source.get("customer") or {},
		"docstatus": doc.get("docstatus") or 0, "customer_order_no": doc.get("custom_customer_order_no") or "",
		"delivery_date": doc.get("delivery_date") or "", "payment_method": source.get("payment_method") or "",
		"deposit": source.get("deposit") or 0, "balance_due_date": source.get("balance_due_date") or "",
		"invoice_plan": source.get("invoice_plan") or "",
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
	clean_visible = {key: visible.get(key, key != "image" and not (doctype == "Delivery Note" and key == "qty")) for key in allowed}
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
	return {"version": 1, "doctype": doctype, "visible": clean_visible, "widths": clean_widths, "settings": clean_settings}


def _template(config):
	doctype = config["doctype"]
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
	cols = "".join(f'<col data-col="{key}" style="width:{widths[key]:.3f}%">' for key in keys)
	headers = "".join(f'<th>{labels[key]}</th>' for key in keys)
	cell_map = {
		"image": '<td>{% if item.image %}<img class="photo" src="{{ item.image | e }}">{% endif %}</td>',
		"name": '<td>{{ (item.item_name or "—") | e }}</td>', "spu": '<td>{{ (item.spu or "—") | e }}</td>',
		"sku": '<td>{{ (item.order_code or item.item_code or "—") | e }}</td>', "cor": '<td>{{ (item.color_code or item.color or "—") | e }}</td>',
		"barcode": '<td>{{ item.barcode | e }}</td>', "description": '<td>{{ item.description | e }}</td>',
		"ordered": '<td>{{ item.ordered_qty or "—" }}</td>', "remaining": '<td>{{ item.remaining_qty or "—" }}</td>',
		"qty": '<td>{{ format_print_qty(item.qty) }}</td>', "picked": '<td>{{ format_print_qty(item.picked_qty) }}</td>',
		"uom": '<td>{{ item.uom | e }}</td>', "rate": '<td>{{ format_print_money(item.rate) }}</td>',
		"amount": '<td>{{ format_print_money(item.amount) }}</td>',
		"trace": '<td>{{ (item.batch_no or item.serial_no or item.serial_and_batch_bundle or "—") | e }}</td>',
		"warehouse": '<td>{{ item.warehouse | e }}</td>', "order": '<td>{{ item.sales_order | e }}</td>',
	}
	provider = "get_a4_print_data(doc)"
	items = 'p["items"]'
	title = {"Sales Order": "Confirmação de Encomenda / 订单确认单", "Sales Invoice": "Venda / 销售单",
	         "Delivery Note": "Guia de Remessa / 送货单", "Pick List": "Lista de Separação / 拣货单"}[doctype]
	settings = config["settings"]
	css = (f'@page{{size:A4;margin:0}} .print-format{{width:210mm;min-height:297mm;padding:{settings["pageMargin"]}mm;box-sizing:border-box;color:#25313a;font-size:{settings["fontSize"]}pt;overflow-wrap:anywhere}}'
	       f'h1{{font-size:{settings["titleSize"]}pt;color:{settings["titleColor"]}}}.items{{width:100%;table-layout:fixed;border-collapse:collapse;font-size:{settings["fontSize"]}pt;line-height:{settings["lineHeight"]}}}'
	       f'.items th{{font-size:{settings["headSize"]}pt;background:{settings["headBg"]}}}.items th,.items td{{padding:{settings["cellPadding"]}mm;border:1px solid #aeb8be;vertical-align:top;overflow-wrap:anywhere}}'
	       '.items thead{display:table-header-group}.items tr{break-inside:avoid}.photo{display:block;width:min(12mm,100%);aspect-ratio:1;object-fit:cover}.parties{width:100%;border-collapse:collapse;margin:10px 0}.parties td{width:50%;padding:2mm;border:1px solid #aeb8be;vertical-align:top}.warning{color:#a35c00;margin:3mm 0}.block{page-break-inside:avoid;margin-top:12px}.qty-total,.total{width:100%;display:block;clear:both;box-sizing:border-box;text-align:right;font-weight:700;margin-top:3mm}.total{font-size:10pt}.footer{text-align:center;margin-top:8mm;color:#52606a}')
	return (FORMAT_META.format(meta) + "{{ get_solua_print_css() }}<style>" + css + "</style>"
	        + f"{{% set p = {provider} %}}{{% set company = p.get('company') or {{}} %}}{{% set customer = p.get('customer') or {{}} %}}<h2>{title}</h2>{{% if doc.docstatus != 1 %}}<div class=\"warning\">{{{{ 'RASCUNHO / 草稿' if doc.docstatus == 0 else 'CANCELADO / 已取消' }}}} — Documento não oficial / 非正式凭证</div>{{% endif %}}"
	        + "<table class=\"parties\"><tr><td><b>{{ company.name | e }}</b><br>NUIT: {{ company.nuit | e }}<br>{{ company.address }}<br>Tel: {{ company.phone | e }}</td><td><b>Cliente / 客户: {{ customer.name | e }}</b><br>NUIT: {{ customer.nuit or 'Não informado / 未提供' | e }}<br>Loja / 门店: {{ customer.store | e }}<br>{{ customer.address }}<br>{{ customer.contact }} · {{ customer.phone | e }}</td></tr><tr><td>N.º / 编号: {{ doc.name | e }}<br>N.º encomenda cliente / 客户订单号: {{ doc.get('custom_customer_order_no') or '—' | e }}</td><td>Data / 日期: {{ doc.get('posting_date') or doc.get('transaction_date') }}<br>Prazo de entrega / 交期: {{ doc.get('delivery_date') or '—' }}</td></tr></table>"
	        + f'<table class="items"><colgroup>{cols}</colgroup><thead><tr><th colspan="{len(keys)}">{{{{ doc.name | e }}}} · 订购 / Encomenda</th></tr><tr>{headers}</tr></thead><tbody>{{% for item in {items} %}}<tr>'
	        + "".join(cell_map[key] for key in keys) + "</tr>{% endfor %}</tbody></table>"
	        + '<div class="qty-total">Total Qty / 总数量: {{ format_print_qty(p.get("total_qty") or 0) }}</div>'
	        + ("<div class=\"total\">Total / 含税合计: {{ format_print_money(doc.grand_total, currency=doc.currency) }} {{ doc.currency }}</div>" if doctype in ("Sales Order", "Sales Invoice") else "")
	        + '<div class="block">Plano de pagamento / 付款安排: {{ p.get("payment_method") or "未维护" | e }} · Depósito / 定金: {{ format_print_money(p.get("deposit"), currency=doc.currency) }} · Vencimento do saldo / 尾款到期: {{ p.get("balance_due_date") or "—" | e }}<br>Plano de faturação / 开票安排: {{ p.get("invoice_plan") or "未维护" | e }}</div><div class="footer">{{ doc.name | e }} · Página 1 / 1</div>')


@frappe.whitelist()
def list_formats(doctype):
	_allowed_doctype(doctype)
	if not frappe.has_permission("Print Format", ptype="read"):
		return []
	return frappe.get_list("Print Format", filters={"doc_type": doctype, "custom_format": 1, "standard": "No"},
	                       fields=["name"], order_by="modified desc", page_length=100)


@frappe.whitelist()
def load_config(name):
	doc = frappe.get_doc("Print Format", name)
	if not frappe.has_permission(doc=doc, ptype="read"):
		frappe.throw(_("Not permitted"), frappe.PermissionError)
	match = re.search(r"<!--SOLUA_A4_DESIGNER:v1:([A-Za-z0-9_-]+=*)-->", doc.html or "")
	if not match:
		frappe.throw(_("This format was not created by the A4 designer"))
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
		if (not rendered or rendered.count("<colgroup>") != 1 or rendered.count("</colgroup>") != 1
				or rendered.count("<col ") != len([key for key in BASE_COLUMNS + DOCTYPE_CONFIG[doctype]
												 if config["visible"].get(key)]) + int(doctype == "Delivery Note"
													 and not config["visible"].get("ordered")
													 and not config["visible"].get("remaining")
													 and not config["visible"].get("qty"))):
			frappe.throw(_("Rendered print output is invalid"))
		return {"name": name, "doctype": doctype}
	except Exception:
		frappe.db.rollback()
		raise
