"""Submission snapshots and read-only data for the two wholesale prints."""

import html
import json
import re

import frappe
from frappe import _

COMPANY_NAME = "Solua Home, Lda"
COMPANY_ADDRESS_LINE = "AV. DO TRABALHO, n.º 231, Cidade de Maputo"


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
        "phone": doc.get("contact_mobile") or doc.get("contact_phone") or "",
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
        "order": get_delivery_order_info(doc), "items": items,
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
            "门店联系人记录": contact_name,
            "起运时间": transport["departure_time"], "仓库具体地址": transport["source_address"],
            "车牌": transport["vehicle_no"], "司机姓名": transport["driver_name"], "司机电话": transport["driver_phone"],
        }
        missing = [label for label, value in required.items() if not str(value or "").strip()]
        if missing:
            frappe.throw(_("Guia 提交前请填写：") + "、".join(missing))
        names = sorted({r.get("against_sales_order") for r in doc.get("items", []) if r.get("against_sales_order")})
        if not names:
            frappe.throw(_("Guia 必须关联销售订单"))
        for name in names:
            order = frappe.get_doc("Sales Order", name)
            if (order.customer != doc.customer or order.get("shipping_address_name") != customer["address_name"]
                    or order.get("custom_store_name") != customer["store"]):
                frappe.throw(_("关联订单客户/门店/收货地址不一致，请拆分送货单"))
            if order.get("contact_person") != contact_name:
                frappe.throw(_("送货联系人与所选门店订单不一致"))
        linked_invoices = frappe.get_all("Sales Invoice Item", filters={"delivery_note": doc.name}, pluck="parent")
        has_invoice = bool(linked_invoices and frappe.db.exists(
            "Sales Invoice", {"name": ["in", linked_invoices], "docstatus": 1}))
        if not has_invoice:
            plan = data["invoice_plan"].strip()
            if len(plan) < 8 or plan in ("按订单维护", "各订单分别维护", "请按后续安排开票", "后续开票", "未维护"):
                frappe.throw(_("尚未开票，请填写具体开票时间或触发条件及对应订单安排"))
    doc.custom_wholesale_snapshot = json.dumps(data, ensure_ascii=False, default=str)
    return data


def get_wholesale_print_data(doc):
    frozen = _snapshot(doc)
    if frozen:
        return frozen
    # Legacy prints are visibly identified; never write/backfill while printing.
    data = _collect(doc)
    data["legacy"] = doc.get("docstatus") != 0
    return data
