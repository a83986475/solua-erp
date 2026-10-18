"""Exact formats approved for retirement in the 2026-10-18 print review."""

import frappe

RETIRED_FORMATS = {
    "Sales Order": (
        "A4-Designer-Deploy-20260926-v7",
        "A4-Designer-Deploy-20260926-v8",
        "A4-Designer-Deploy-20260927-v9-SalesOrder",
        "A4-Designer-Deploy-20260927-v9-SalesOrder-Final",
        "PRINT DESIGN 销售订单",
        "Sales Order DIY",
        "Sales Order PD v2",
        "Sales Order Standard",
        "客户订单确认单（A4新版）",
        "客户订单确认单（公司抬头-新）",
        "客户订单确认单（颜色版）-紧凑无边框版",
        "差价退款 A4 可编辑版 - 销售订单 v2",
        "窗帘销售单带图",
        "销售单带补充说明",
        "销售单无图",
    ),
    "Pick List": (
        "A4-Designer-Deploy-20260927-v9-PickList",
        "Pick List",
        "拣货单（颜色版）",
    ),
    "Delivery Note": (
        "A4-Designer-Deploy-20260927-v10-DeliveryNote-Signature",
        "A4-Designer-Deploy-20260927-v9-DeliveryNote",
        "Delivery Note Standard",
        "Delivery Note with Item Image",
    ),
    "Sales Invoice": (
        "Detailed Tax Invoice",
        "FACTURA A4",
        "FACTURA A4 1",
        "FACTURA A4（8mm边距）",
        "FACTURA A4（8mm边距） v2",
        "Sales Invoice PD Format v2",
        "Sales Invoice Return",
        "Sales Invoice Standard",
        "Sales Invoice with Item Image",
        "Sales Invoice with Item Image（现金折扣版）",
        "Simplified Tax Invoice",
        "Tax Invoice",
        "批发销售单（颜色版）",
    ),
}

MARGIN_FORMATS = frozenset({
    "客户订单确认单（颜色版）-紧凑版",
    "差价明细 A4 - 销售订单",
    "差价明细 A4 - 销售发票",
    "差价退款 A4 可编辑版 - 销售发票 v2",
})
MARGIN_CSS = (
    "/* SOLUA_REVIEWED_MARGINS_20261018 */"
    "@page{size:A4!important;margin:8mm 8mm 10mm!important;}"
    ".print-format.print-format{width:100%!important;max-width:none!important;"
    "min-height:0!important;margin:0!important;padding:0 0 2mm!important;"
    "box-sizing:border-box!important;zoom:1!important;}"
)


def is_retired_format(name):
    return any(name in names for names in RETIRED_FORMATS.values())


def get_reviewed_margin_css():
    form_dict = getattr(frappe, "form_dict", None) or {}
    name = form_dict.get("format") or form_dict.get("print_format")
    return MARGIN_CSS if name in MARGIN_FORMATS else ""


def apply_reviewed_retirements():
    """Delete only reviewed names; retain normal link checks and the caller's transaction."""
    defaults = {}
    for doctype in RETIRED_FORMATS:
        name = frappe.get_meta(doctype).default_print_format
        if is_retired_format(name) or frappe.db.get_value("Print Format", name, "doc_type") != doctype:
            raise RuntimeError("Reviewed default Print Format is unavailable: " + doctype)
        defaults[doctype] = name

    if frappe.get_meta("POS Profile").has_field("default_print_format"):
        for name in frappe.get_all("POS Profile", filters={
            "default_print_format": ["in", RETIRED_FORMATS["Sales Invoice"]],
        }, pluck="name"):
            frappe.db.set_value("POS Profile", name, "default_print_format", defaults["Sales Invoice"])

    if frappe.db.get_value("Print Format", "Sales Auditing Voucher", "disabled"):
        frappe.db.set_value("Print Format", "Sales Auditing Voucher", "disabled", 0)

    deleted = []
    for doctype, names in RETIRED_FORMATS.items():
        for name in names:
            if not frappe.db.exists("Print Format", name):
                continue
            doc = frappe.get_doc("Print Format", name)
            if doc.doc_type != doctype:
                raise RuntimeError("Unexpected Print Format document type: " + name)
            frappe.delete_doc("Print Format", name, ignore_permissions=True)
            deleted.append(name)
        frappe.clear_cache(doctype=doctype)
    return deleted
