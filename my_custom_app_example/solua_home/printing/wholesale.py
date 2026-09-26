"""Submission snapshots and read-only data for the two wholesale prints."""

import html
import json
import re
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP

import frappe
from frappe import _
from markupsafe import Markup

COMPANY_NAME = "Solua Home, Lda"
COMPANY_ADDRESS_LINE = "AV. DO TRABALHO, n.º 231, Cidade de Maputo"


def _print_setting(name, default):
    """Read one global Solua print setting without making printing fragile."""
    try:
        value = frappe.db.get_single_value("Print Settings", name)
    except Exception:
        value = None
    return value if value not in (None, "") else default


def get_solua_print_css():
    """Shared print CSS; settings are read at render time for preview and PDF."""
    try:
        parsed_font_size = int(float(_print_setting("custom_solua_print_font_size", 10)))
        font_size = 10 if parsed_font_size <= 0 else max(8, min(14, parsed_font_size))
    except (TypeError, ValueError):
        font_size = 10
    density = str(_print_setting("custom_solua_print_density", "紧凑")).strip().lower()
    compact = density not in {"标准", "standard", "normal"}
    line_height = "1.12" if compact else "1.35"
    cell_padding = "3px 4px" if compact else "6px 6px"
    block_margin = "7px" if compact else "12px"
    return Markup("""
<style id="solua-print-shared">
:root {{ --solua-font-size: {font_size}pt; --solua-line-height: {line_height}; --solua-cell-padding: {cell_padding}; --solua-block-margin: {block_margin}; }}
.print-format, .print-format * {{ box-sizing: border-box; }}
.print-format {{ font-size: var(--solua-font-size); line-height: var(--solua-line-height); color: #263238; }}
.print-format h1, .print-format h2, .print-format h3 {{ line-height: 1.15; }}
.print-format table {{ width: 100%; border-collapse: collapse; table-layout: auto; }}
.print-format th, .print-format td {{ padding: var(--solua-cell-padding); vertical-align: top; line-height: var(--solua-line-height); overflow-wrap: normal; word-break: normal; }}
.print-format th {{ white-space: normal; }}
.print-format .num {{ text-align: right; white-space: nowrap; }}
.print-format .col-sku, .print-format .col-barcode, .print-format .col-uom,
.print-format .col-qty, .print-format .col-rate, .print-format .col-amount,
.print-format .col-traceability {{ white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }}
.print-format .col-sku {{ min-width: 24mm; width: 24mm; }}
.print-format .col-barcode {{ min-width: 30mm; width: 30mm; }}
.print-format .col-qty {{ min-width: 17mm; width: 17mm; }}
.print-format .col-uom {{ min-width: 10mm; width: 10mm; }}
.print-format .col-rate, .print-format .col-amount {{ min-width: 22mm; width: 22mm; }}
.print-format .col-description {{ min-width: 42mm; white-space: normal; overflow-wrap: break-word; word-break: normal; }}
.print-format .col-traceability {{ min-width: 20mm; width: 20mm; }}
.print-format .photo {{ max-width: 45px; max-height: 45px; object-fit: contain; }}
.print-format .block {{ page-break-inside: avoid; margin-top: var(--solua-block-margin); }}
@media print {{ .print-format {{ font-size: var(--solua-font-size); }} }}
</style>
""".format(font_size=font_size, line_height=line_height, cell_padding=cell_padding, block_margin=block_margin))


def validate_print_settings(doc, method=None):
    """Keep the global print controls inside the supported range."""
    if doc.doctype != "Print Settings":
        return
    try:
        font_size = int(float(doc.get("custom_solua_print_font_size") or 10))
    except (TypeError, ValueError):
        frappe.throw(_("打印基础字号必须是 8 到 14 pt 的整数"))
    if not 8 <= font_size <= 14:
        frappe.throw(_("打印基础字号必须在 8 到 14 pt 之间"))
    if doc.get("custom_solua_print_density") not in (None, "", "紧凑", "标准", "compact", "standard"):
        frappe.throw(_("打印密度只能选择紧凑或标准"))


def _clean_item_text(value):
    """Return one readable line without HTML or duplicated source fields."""
    if not value:
        return ""
    text = re.sub(r"<br\s*/?>", "\n", str(value), flags=re.IGNORECASE)
    text = re.sub(r"<[^>]+>", " ", text)
    return " ".join(html.unescape(text).split())


def _usable_barcode(value, item_code):
    value = str(value or "").strip()
    return value if value and value != str(item_code or "").strip() else ""


def _item_master(item_code):
    if not item_code:
        return {}
    fields = ["variant_of", "description"]
    meta = frappe.get_meta("Item")
    for field in ("custom_item_description_pt", "custom_label_barcode"):
        if meta.has_field(field):
            fields.append(field)
    data = frappe.db.get_value("Item", item_code, fields, as_dict=True) or {}
    return data if hasattr(data, "get") else {}


def _item_barcodes(item_code):
    rows = frappe.get_all(
        "Item Barcode",
        filters={"parent": item_code},
        fields=["barcode", "barcode_type"],
        order_by="idx asc",
        limit_page_length=20,
    )
    return rows or []


def get_item_sales_display(item_code, row_description=""):
    """Resolve the real barcode and the single best sales description.

    Variant item codes are never used as barcodes. A variant may use its own
    native Item Barcode, otherwise its inherited custom label barcode or the
    template's native barcode is used.
    """
    item = _item_master(item_code)
    barcode = ""
    barcode_type = ""
    for row in _item_barcodes(item_code):
        barcode = _usable_barcode(row.get("barcode"), item_code)
        if barcode:
            barcode_type = row.get("barcode_type") or ""
            break
    if not barcode:
        barcode = _usable_barcode(item.get("custom_label_barcode"), item_code)
        barcode_type = "code128" if barcode else ""
    if not barcode and item.get("variant_of"):
        template_code = item.get("variant_of")
        template = _item_master(template_code)
        for row in _item_barcodes(template_code):
            barcode = _usable_barcode(row.get("barcode"), template_code)
            if barcode:
                barcode_type = row.get("barcode_type") or ""
                break
        if not barcode:
            barcode = _usable_barcode(template.get("custom_label_barcode"), template_code)
            barcode_type = "code128" if barcode else ""

    description = _clean_item_text(item.get("custom_item_description_pt"))
    if not description:
        description = _clean_item_text(item.get("description"))
    if not description:
        description = _clean_item_text(row_description)
    return {"barcode": barcode, "barcode_type": barcode_type, "description": description}


def _value(doctype, name, field):
    if name and frappe.get_meta(doctype).has_field(field):
        return frappe.db.get_value(doctype, name, field) or ""
    return ""


def _snapshot(doc):
    raw = doc.get("custom_wholesale_snapshot")
    if not raw:
        return None
    data = json.loads(raw)
    if data.get("version") != 1:
        frappe.throw(_("不支持的批发打印快照版本"))
    return data


def get_company_print_info(doc):
    frozen = _snapshot(doc)
    if frozen:
        return frozen["company"]
    company = doc.get("company") or ""
    own = company == COMPANY_NAME
    return {
        "name": company,
        "nuit": _value("Company", company, "tax_id") or ("402216468" if own else ""),
        "address": doc.get("company_address_display") or (COMPANY_ADDRESS_LINE if own else ""),
        "phone": _value("Company", company, "phone_no") or ("860515423" if own else ""),
    }


def get_customer_print_info(doc):
    frozen = _snapshot(doc)
    if frozen:
        return frozen["customer"]
    # shipping_address is rendered HTML; shipping_address_name is the Link.
    return {
        "name": doc.get("customer_name") or doc.get("customer") or "",
        "nuit": doc.get("tax_id") or "",
        "address": doc.get("shipping_address") or "",
        "address_name": doc.get("shipping_address_name") or "",
        "store": doc.get("custom_store_name") or "",
        "contact": doc.get("contact_display") or "",
        "phone": doc.get("custom_store_phone") or doc.get("contact_mobile") or doc.get("contact_phone") or "",
    }


def get_driver_phone(doc):
    frozen = _snapshot(doc)
    if frozen:
        return frozen["transport"]["driver_phone"]
    return doc.get("custom_driver_phone") or _value("Driver", doc.get("driver"), "cell_number")


def get_delivery_order_info(doc):
    frozen = _snapshot(doc)
    if frozen:
        return frozen["order"]
    names = sorted({r.get("against_sales_order") for r in doc.get("items", []) if r.get("against_sales_order")})
    return {"name": ", ".join(names)}


def get_delivery_invoice_names(delivery_note):
    # Invoice associations can legitimately appear after delivery submission.
    note = frappe.get_doc("Delivery Note", delivery_note)
    note.check_permission("print")
    if not frappe.has_permission("Sales Invoice", ptype="read"):
        return []
    parents = frappe.get_all("Sales Invoice Item", filters={"delivery_note": delivery_note}, pluck="parent")
    if not parents:
        return []
    return frappe.get_list("Sales Invoice", filters={"name": ["in", parents], "docstatus": 1},
                           pluck="name", limit_page_length=0)


def _sum_qty(rows, key):
    """空值安全的数量求和；整数就不带小数点，方便直接打在纸上。"""
    total = 0.0
    for row in rows or []:
        try:
            total += float(row.get(key) or 0)
        except (TypeError, ValueError):
            continue
    return int(total) if float(total).is_integer() else round(total, 6)


def format_print_qty(value):
    """Render document quantities as whole units; source data remains unchanged."""
    try:
        amount = Decimal(str(value if value not in (None, "") else 0))
    except (InvalidOperation, TypeError, ValueError):
        return "0"
    return format(amount.quantize(Decimal("1"), rounding=ROUND_HALF_UP), "f")


def format_print_money(value, currency=None):
    """Render document money with zero decimals while retaining ERP currency formatting."""
    return frappe.utils.fmt_money(value or 0, currency=currency, precision=0)


def get_print_total_qty(data):
    """打印表格底部的总数量；快照与实时数据都适用。"""
    return _sum_qty((data or {}).get("items") or [], "qty")


def get_pick_list_rows(doc):
    """拣货单的明细在 locations 子表（Pick List Item），并补上色号/条码/描述。"""
    from solua_home.printing.color_card import get_item_color_info

    rows = []
    for row in doc.get("locations") or []:
        item_code = row.get("item_code")
        color = get_item_color_info(item_code) or {}
        display = get_item_sales_display(item_code, row.get("description"))
        rows.append({
            "item_code": item_code,
            "item_name": row.get("item_name") or item_code,
            "order_code": color.get("order_code") or item_code,
            "color_code": color.get("color_code") or "",
            "color": color.get("color_name") or "",
            "barcode": display.get("barcode") or "",
            "description": display.get("description") or "",
            "image": color.get("image") or "",
            "template_code": color.get("template_code") or "",
            "qty": row.get("qty"),
            "picked_qty": row.get("picked_qty"),
            "uom": row.get("uom") or row.get("stock_uom") or "",
            "warehouse": row.get("warehouse") or "",
            "sales_order": row.get("sales_order") or "",
        })
    return rows


def get_pick_list_print_data(doc):
    """拣货单打印数据：行 + 需求数量/已拣数量合计。"""
    rows = get_pick_list_rows(doc)
    return {
        "items": rows,
        "total_qty": _sum_qty(rows, "qty"),
        "total_picked": _sum_qty(rows, "picked_qty"),
        "company": doc.get("company") or "",
        "purpose": doc.get("purpose") or "",
        "customer": doc.get("customer_name") or doc.get("customer") or "",
        "source": doc.get("work_order") or doc.get("material_request") or "",
    }


def _collect(doc):
    from solua_home.printing.color_card import get_item_color_info

    items = []
    for row in doc.get("items", []):
        color = get_item_color_info(row.item_code)
        sales_display = get_item_sales_display(row.item_code, row.get("description"))
        items.append({
            "item_code": row.item_code, "item_name": row.get("item_name") or row.item_code,
            "order_code": color.get("order_code") or row.item_code,
            "color_code": color.get("color_code") or "", "color": color.get("color_name") or "",
            "barcode": sales_display["barcode"], "description": sales_display["description"],
            "image": color.get("image") or "", "template_code": color.get("template_code") or "",
            "uom": row.get("uom") or row.get("stock_uom") or "",
            "qty": row.get("qty"), "rate": row.get("rate"), "amount": row.get("amount"),
            "ordered_qty": row.get("custom_ordered_qty") if row.get("so_detail") and not doc.get("is_return") else None,
            "delivered_before_qty": row.get("custom_delivered_before_qty") if row.get("so_detail") and not doc.get("is_return") else None,
            "remaining_qty": row.get("custom_remaining_qty") if row.get("so_detail") and not doc.get("is_return") else None,
            "batch_no": row.get("batch_no") or "", "serial_no": row.get("serial_no") or "",
            "serial_and_batch_bundle": row.get("serial_and_batch_bundle") or "",
            "warehouse": row.get("warehouse") or "",
        })
    return {
        "version": 1, "company": get_company_print_info(doc), "customer": get_customer_print_info(doc),
        "order": get_delivery_order_info(doc), "items": items, "total_qty": _sum_qty(items, "qty"),
        "transport": {
            "driver_name": doc.get("driver_name") or _value("Driver", doc.get("driver"), "full_name"),
            "vehicle_no": doc.get("vehicle_no") or "", "driver_phone": get_driver_phone(doc),
            "departure_time": str(doc.get("custom_departure_time") or ""),
            "source_address": doc.get("custom_source_warehouse_address") or "",
        },
        "invoice_plan": doc.get("custom_invoice_plan") or "",
        "payment_method": doc.get("custom_payment_method") or "",
        "deposit": doc.get("custom_deposit_amount") or 0,
        "balance_due_date": str(doc.get("custom_balance_due_date") or ""),
    }


def _recover_sales_order_item_display(doc, data):
    """Fill only missing legacy snapshot display values without writing back."""
    if doc.doctype != "Sales Order":
        return
    for index, row in enumerate(doc.get("items") or []):
        if index >= len(data.get("items", [])):
            break
        item = data["items"][index]
        display = get_item_sales_display(row.item_code, row.get("description"))
        if not item.get("barcode"):
            item["barcode"] = display["barcode"]
        if not item.get("description"):
            item["description"] = display["description"]


def prepare_print_snapshot(doc, method=None):
    """before_submit: validate Guia, set JSON on the document; no DB writes."""
    if doc.doctype not in ("Sales Order", "Delivery Note"):
        return
    address_name = doc.get("shipping_address_name")
    contact_name = doc.get("contact_person")
    for doctype, name in (("Address", address_name), ("Contact", contact_name)):
        if name and not frappe.db.exists("Dynamic Link", {
            "parenttype": doctype, "parent": name, "link_doctype": "Customer",
            "link_name": doc.get("customer"),
        }):
            frappe.throw(_("所选收货地址/联系人不属于当前客户"))
    if contact_name and address_name:
        contact_address = _value("Contact", contact_name, "address")
        if contact_address and contact_address != address_name:
            frappe.throw(_("联系人绑定的地址与当前门店不一致"))
    # Amendments can inherit the old field; always collect fresh on new submit.
    doc.custom_wholesale_snapshot = None
    data = _collect(doc)
    if doc.doctype == "Delivery Note":
        customer, company, transport = data["customer"], data["company"], data["transport"]
        required = {
            "公司名称": company["name"], "公司NUIT": company["nuit"], "公司地址": company["address"],
            "客户名称": customer["name"], "客户门店": customer["store"],
            "客户收货地址": customer["address"], "客户收货地址记录": customer["address_name"],
            "门店联系人": customer["contact"], "门店电话": customer["phone"],
            "门店联系人记录": contact_name, "司机主档": doc.get("driver"),
            "车牌": transport["vehicle_no"], "司机姓名": transport["driver_name"], "司机电话": transport["driver_phone"],
        }
        missing = [label for label, value in required.items() if not str(value or "").strip()]
        if missing:
            frappe.throw(_("Guia 提交前请填写：") + "、".join(missing))
        names = sorted({r.get("against_sales_order") for r in doc.get("items", []) if r.get("against_sales_order")})
        if not names:
            frappe.throw(_("Guia 必须关联销售订单"))
    doc.custom_wholesale_snapshot = json.dumps(data, ensure_ascii=False, default=str)
    return data


def _has_nonzero(value):
    try:
        return abs(float(value or 0)) > 0.000001
    except (TypeError, ValueError):
        return False


def _recover_delivery_quantities(doc, data):
    """Read-only compatibility for old/draft delivery notes with zero fields."""
    if doc.get("is_return"):
        data["has_order_linkage"] = False
        data["has_ordered_before"] = False
        return
    rows = doc.get("items") or []
    references = [bool(row.get("against_sales_order") or row.get("so_detail")) for row in rows]
    data["has_order_linkage"] = any(references)
    data["has_ordered_before"] = any(
        index < len(data.get("items", [])) and references[index] and (
            _has_nonzero(data["items"][index].get("ordered_qty"))
            or _has_nonzero(data["items"][index].get("delivered_before_qty"))
        )
        for index in range(len(rows))
    )
    errors = []
    # A fully populated snapshot is authoritative. Only all-zero linked rows
    # take the read-only recovery path for legacy/draft documents.
    stale = data["has_order_linkage"] and not data["has_ordered_before"]
    incomplete = []
    for index, row in enumerate(rows):
        if references[index] and (not row.get("against_sales_order") or not row.get("so_detail")):
            incomplete.append(index)
    if stale:
        from solua_home.api.stock import get_delivery_snapshot_quantities

        resolved = get_delivery_snapshot_quantities(doc, lock=False, strict=False)
        by_index = {result["index"]: result for result in resolved}
        for index, item in enumerate(data.get("items", [])):
            result = by_index.get(index)
            if result and "error" not in result:
                item.update({key: result[key] for key in ("ordered_qty", "delivered_before_qty", "remaining_qty")})
            elif index < len(references) and references[index]:
                item.update({"ordered_qty": None, "delivered_before_qty": None, "remaining_qty": None})
                errors.append(rows[index].get("item_code") or "第 {} 行".format(index + 1))
    for index in incomplete:
        if index < len(data.get("items", [])):
            data["items"][index].update({"ordered_qty": None, "delivered_before_qty": None, "remaining_qty": None})
            errors.append(rows[index].get("item_code") or "第 {} 行".format(index + 1))
    if data["has_order_linkage"]:
        for index, linked in enumerate(references):
            if not linked and index < len(data.get("items", [])):
                data["items"][index].update({"ordered_qty": None, "delivered_before_qty": None, "remaining_qty": None})
                errors.append(rows[index].get("item_code") or "第 {} 行".format(index + 1))
    if errors:
        data["delivery_quantity_error"] = "以下行缺少完整销售订单关联，订购/此前已交付无法可靠恢复：" + "、".join(dict.fromkeys(errors))
    data["has_ordered_before"] = any(
        index < len(data.get("items", [])) and references[index] and (
            _has_nonzero(data["items"][index].get("ordered_qty"))
            or _has_nonzero(data["items"][index].get("delivered_before_qty"))
        )
        for index in range(len(rows))
    )


def get_wholesale_print_data(doc):
    frozen = _snapshot(doc)
    # Legacy prints are visibly identified; never write/backfill while printing.
    data = frozen or _collect(doc)
    if frozen and doc.doctype == "Sales Order":
        live_rows = doc.get("items") or []
        snapshot_rows = data.get("items") or []
        same_rows = len(live_rows) == len(snapshot_rows) and all(
            live.get("item_code") == saved.get("item_code")
            for live, saved in zip(live_rows, snapshot_rows)
        )
        if live_rows and same_rows:
            # Snapshot keeps stable display data; transaction values must follow the edited order.
            for live, saved in zip(live_rows, snapshot_rows):
                for key in ("uom", "qty", "rate", "amount", "warehouse"):
                    saved[key] = live.get(key)
            data["total_qty"] = _sum_qty(snapshot_rows, "qty")
        elif live_rows:
            data = _collect(doc)
    _recover_sales_order_item_display(doc, data)
    if doc.doctype == "Delivery Note":
        _recover_delivery_quantities(doc, data)
        data["has_traceability"] = any(
            str(item.get(key) or "").strip()
            for item in data.get("items", [])
            for key in ("batch_no", "serial_no", "serial_and_batch_bundle")
        )
    data["total_qty"] = _sum_qty(data.get("items") or [], "qty")
    if not frozen:
        data["legacy"] = doc.get("docstatus") != 0
    return data
