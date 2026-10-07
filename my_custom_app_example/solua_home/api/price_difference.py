"""Generate display-only price-difference snapshots for sales documents."""

import html
import json
from collections import OrderedDict

import frappe
from frappe import _
from frappe.utils import flt


SUPPORTED = {"Sales Order": "Sales Order Item", "Sales Invoice": "Sales Invoice Item"}
DEFAULT_PRICE_LIST = "Wholesale Selling"
JSON_FIELD = "custom_price_difference_detail_json"
HTML_FIELD = "custom_price_difference_detail_html"
SUMMARY_FIELD = "custom_price_difference_detail"


def _money(value):

	return f"{flt(value):,.2f}"


def _number(value):

	return flt(value or 0)


def _parse_snapshot(doc):

	raw = doc.get(JSON_FIELD) or ""
	if not raw:
		return {}
	try:
		value = json.loads(raw) if isinstance(raw, str) else raw
	except (TypeError, ValueError):
		return {}
	return value if isinstance(value, dict) else {}


def _validate_price_list(price_list):

	price_list = str(price_list or DEFAULT_PRICE_LIST).strip()
	row = frappe.db.get_value("Price List", price_list, ["name", "selling", "currency"], as_dict=True)
	if not row or not row.selling:
		frappe.throw(_("销售价格表不存在或不是销售价格表：{0}").format(price_list))
	return row


def _source_doc(doc, original_document):

	if not original_document:
		original_document = _parse_snapshot(doc).get("original_document")
	if not original_document or original_document == doc.name:
		return doc, ""
	if not frappe.db.exists(doc.doctype, original_document):
		frappe.throw(_("原单据不存在：{0}").format(original_document))
	source = frappe.get_doc(doc.doctype, original_document)
	if source.customer != doc.customer:
		frappe.throw(_("原单据客户与当前单据不一致，不能生成差价明细"))
	return source, original_document


def _item_price(doc, row, price_list):

	from erpnext.stock.get_item_details import get_item_details

	context = frappe._dict({
		"doctype": doc.doctype,
		"parenttype": doc.doctype,
		"child_doctype": SUPPORTED[doc.doctype],
		"item_code": row.item_code,
		"qty": row.qty,
		"uom": row.uom or row.stock_uom,
		"warehouse": row.warehouse,
		"company": doc.company,
		"customer": doc.customer,
		"transaction_date": doc.get("transaction_date") or doc.get("posting_date"),
		"price_list": price_list,
		"selling_price_list": price_list,
		"currency": doc.currency,
		"price_list_currency": doc.currency,
		"conversion_rate": doc.get("conversion_rate") or 1,
		"plc_conversion_rate": doc.get("plc_conversion_rate") or 1,
		"ignore_pricing_rule": 1,
	})
	try:
		result = get_item_details(context, None, for_validate=False, overwrite_warehouse=False) or {}
		return _number(result.get("price_list_rate") or result.get("rate")), ""
	except Exception as exc:
		return 0, str(exc)[:180]


def _display_info(item_code, item_name):

	try:
		from solua_home.printing.color_card import get_item_color_info

		info = get_item_color_info(item_code) or {}
	except Exception:
		info = {}
	order_code = info.get("order_code") or item_code
	name = info.get("template_name") or item_name or item_code
	color = info.get("color_name") or info.get("color_code") or ""
	return order_code, name, color


def _build_rows(doc, source, price_list):

	groups = OrderedDict()
	warnings = []
	for source_row in source.get("items") or []:
		if not source_row.item_code:
			continue
		old_rate = _number(source_row.rate)
		new_rate, error = _item_price(doc, source_row, price_list)
		if error:
			warnings.append(f"{source_row.item_code}：读取新价格失败，暂按原价；{error}")
		if new_rate <= 0:
			new_rate = old_rate
			if not error:
				warnings.append(f"{source_row.item_code}：价格表中没有有效价格，暂按原价")
		uom = source_row.uom or source_row.stock_uom or ""
		order_code, item_name, color = _display_info(source_row.item_code, source_row.item_name)
		key = (order_code, uom, old_rate, new_rate)
		if key not in groups:
			groups[key] = {
				"item_code": order_code,
				"item_name": item_name,
				"description": "",
				"colors": [],
				"qty": 0,
				"uom": uom,
				"old_rate": old_rate,
				"new_rate": new_rate,
				"unit_difference": old_rate - new_rate,
				"difference_amount": 0,
			}
		group = groups[key]
		group["qty"] += abs(_number(source_row.qty))
		group["difference_amount"] += abs(_number(source_row.qty)) * (old_rate - new_rate)
		if color and color not in group["colors"]:
			group["colors"].append(color)
	rows = []
	for group in groups.values():
		colors = group.pop("colors")
		group["description"] = "颜色：" + "、".join(colors) if colors else ""
		rows.append({key: flt(value) if key in {"qty", "old_rate", "new_rate", "unit_difference", "difference_amount"} else value for key, value in group.items()})
	return rows, warnings


def _detail_html(detail):

	esc = html.escape
	rows = []
	for index, row in enumerate(detail["rows"], 1):
		rows.append(
			"<tr>"
			f"<td>{index}</td><td>{esc(row['item_name'])}<div class='pd-muted'>{esc(row.get('description') or '')}</div></td>"
			f"<td>{esc(row['item_code'])}</td><td class='num'>{row['qty']:g}</td><td>{esc(row['uom'])}</td>"
			f"<td class='num'>{_money(row['old_rate'])}</td><td class='num'>{_money(row['new_rate'])}</td>"
			f"<td class='num'>{_money(row['unit_difference'])}</td><td class='num'>{_money(row['difference_amount'])}</td></tr>"
		)
	refund = detail.get("refund_amount")
	refund_row = f"<tr class='total'><td>实际退款 / Reembolso efetuado</td><td class='num'>{_money(refund)}</td></tr>" if refund is not None else ""
	return (
		"<table class='pd-items'><thead><tr>"
		"<th>序号<br>N.º</th><th>商品<br>Produto</th><th>编码<br>Código</th><th>数量<br>Qtd.</th><th>单位<br>Unid.</th>"
		"<th>原单价<br>Preço ant.</th><th>新单价<br>Preço novo</th><th>单位差价<br>Dif. unit.</th><th>差价合计<br>Dif. total</th>"
		"</tr></thead><tbody>" + "".join(rows) + "</tbody></table>"
		"<table class='pd-summary'>"
		f"<tr><td>旧订单金额 / Valor da encomenda</td><td class='num'>{_money(detail['old_total'])}</td></tr>"
		f"<tr><td>新价格合计 / Total com preço novo</td><td class='num'>{_money(detail['new_total'])}</td></tr>"
		f"<tr class='total'><td>价格差价 / Diferença de preço</td><td class='num'>{_money(detail['difference_total'])}</td></tr>"
		+ (f"<tr><td>差价现金折扣 / Desconto sobre a diferença</td><td class='num'>-{_money(detail['difference_discount'])}</td></tr>" if detail.get("difference_discount") else "")
		+ refund_row + "</table>"
	)


@frappe.whitelist()
def generate_detail(doctype, name, price_list=None, original_document=None):

	if doctype not in SUPPORTED:
		frappe.throw(_("只支持销售订单和销售发票"))
	doc = frappe.get_doc(doctype, name)
	if not frappe.has_permission(doc=doc, ptype="read") or not frappe.has_permission(doc=doc, ptype="write"):
		frappe.throw(_("没有修改该单据打印快照的权限"), frappe.PermissionError)
	price_list_doc = _validate_price_list(price_list)
	source, resolved_original = _source_doc(doc, original_document)
	rows, warnings = _build_rows(doc, source, price_list_doc.name)
	if not rows:
		frappe.throw(_("单据没有可生成的商品明细"))
	difference_total = sum(_number(row["difference_amount"]) for row in rows)
	old_total = abs(_number(source.grand_total))
	previous = _parse_snapshot(doc)
	if doc.name != source.name and not doc.get("is_return"):
		new_total = abs(_number(doc.grand_total))
	else:
		new_total = old_total - difference_total
	refund_amount = previous.get("refund_amount")
	if refund_amount is None and doc.doctype == "Sales Invoice" and doc.get("is_return"):
		refund_amount = abs(_number(doc.grand_total))
	difference_discount = max(difference_total - _number(refund_amount), 0) if refund_amount is not None else 0
	detail = {
		"version": 3,
		"document_type": "差价明细 / Diferença de preço",
		"original_document": resolved_original or source.name,
		"current_document": doc.name,
		"customer": doc.customer,
		"currency": doc.currency,
		"price_list": price_list_doc.name,
		"payment_entry": previous.get("payment_entry") or "",
		"difference_total": difference_total,
		"old_total": old_total,
		"new_total": new_total,
		"difference_discount": difference_discount,
		"refund_amount": refund_amount,
		"warnings": warnings,
		"calculation_note": "包含全部产品；未变价产品保留并显示 0 差价。此快照仅用于打印，不参与会计计算。",
		"rows": rows,
	}
	payload = json.dumps(detail, ensure_ascii=False, separators=(",", ":"))
	doc.db_set(JSON_FIELD, payload, update_modified=True)
	doc.db_set(HTML_FIELD, _detail_html(detail), update_modified=False)
	if doc.doctype == "Sales Invoice" and frappe.get_meta(doc.doctype).has_field(SUMMARY_FIELD):
		doc.db_set(SUMMARY_FIELD, f"旧订单金额 {_money(old_total)}；新价格合计 {_money(new_total)}；差价 {_money(difference_total)}", update_modified=False)
	return {
		"name": doc.name,
		"doctype": doc.doctype,
		"original_document": detail["original_document"],
		"price_list": price_list_doc.name,
		"rows": len(rows),
		"old_total": old_total,
		"new_total": new_total,
		"difference_total": difference_total,
		"refund_amount": refund_amount,
		"warnings": warnings,
	}
