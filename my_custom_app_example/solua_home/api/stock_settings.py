"""Keep ERPNext negative-stock policy and POS oversell policy in sync."""

import frappe
from frappe.utils import cint


_SYNC_FLAG = "solua_home_stock_policy_syncing"


def _set_profiles_block_sale(block_sale: int) -> None:
    """Apply the inverse policy to every POS Profile and mark it modified."""
    for name in frappe.get_all("POS Profile", pluck="name"):
        current = cint(frappe.db.get_value("POS Profile", name, "block_sale_beyond_available_qty") or 0)
        if current != block_sale:
            frappe.db.set_value(
                "POS Profile",
                name,
                "block_sale_beyond_available_qty",
                block_sale,
                update_modified=True,
            )
    frappe.clear_cache(doctype="POS Profile")


def _sync(allow_negative_stock: int) -> None:
    if getattr(frappe.flags, _SYNC_FLAG, False):
        return

    setattr(frappe.flags, _SYNC_FLAG, True)
    try:
        _set_profiles_block_sale(0 if allow_negative_stock else 1)
    finally:
        setattr(frappe.flags, _SYNC_FLAG, False)


def sync_from_stock_settings(doc, method=None):
    """When global negative stock changes, update all POS Profiles."""
    _sync(cint(doc.get("allow_negative_stock")))


def sync_from_pos_profile(doc, method=None):
    """When a POS Profile changes, update the global setting and all profiles."""
    if not doc.has_value_changed("block_sale_beyond_available_qty"):
        return
    if getattr(frappe.flags, _SYNC_FLAG, False):
        return

    allow_negative_stock = 0 if cint(doc.get("block_sale_beyond_available_qty")) else 1
    setattr(frappe.flags, _SYNC_FLAG, True)
    try:
        current = cint(frappe.db.get_single_value("Stock Settings", "allow_negative_stock") or 0)
        if current != allow_negative_stock:
            frappe.db.set_single_value("Stock Settings", "allow_negative_stock", allow_negative_stock)
        _set_profiles_block_sale(0 if allow_negative_stock else 1)
    finally:
        setattr(frappe.flags, _SYNC_FLAG, False)


def enable_negative_stock_and_sync():
    """One-time migration/helper: enable negative stock and align POS Profiles."""
    frappe.db.set_single_value("Stock Settings", "allow_negative_stock", 1)
    _sync(1)
    frappe.clear_cache(doctype="Stock Settings")
    frappe.db.commit()
    return get_policy_status()


def get_policy_status():
    """Return the effective values for deployment verification."""
    return {
        "allow_negative_stock": cint(
            frappe.db.get_single_value("Stock Settings", "allow_negative_stock") or 0
        ),
        "pos_profiles": frappe.get_all(
            "POS Profile",
            fields=["name", "block_sale_beyond_available_qty"],
            order_by="name asc",
        ),
    }
