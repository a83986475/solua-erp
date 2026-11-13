"""Password-protected deletion for documents with accounting or stock ledgers."""

import json

import frappe
from frappe import _
from frappe.desk.reportview import delete_bulk as native_delete_bulk
from frappe.desk.reportview import delete_items as native_delete_items
from frappe.utils.password import check_password


LEDGER_LINKS = (
    ("GL Entry", "voucher_type", "voucher_no"),
    ("Stock Ledger Entry", "voucher_type", "voucher_no"),
    ("Payment Ledger Entry", "voucher_type", "voucher_no"),
)


def _has_linked_ledger_entries(doctype, name):
    return any(
        frappe.db.exists(ledger_doctype, {type_field: doctype, name_field: name})
        for ledger_doctype, type_field, name_field in LEDGER_LINKS
    )


def _is_admin():
    return frappe.session.user == "Administrator" or "System Manager" in frappe.get_roles()


def _authorize_linked_delete(doctype, name, password):
    if not _has_linked_ledger_entries(doctype, name):
        return False
    if not _is_admin():
        frappe.throw(_("只有管理员（System Manager）可以删除带账务关联的单据"), frappe.PermissionError)
    if not password:
        frappe.throw(_("删除带账务关联的单据前必须输入当前用户密码"), frappe.AuthenticationError)
    check_password(frappe.session.user, password)
    return True


def _bulk_names(items=None):
    items = items if items is not None else frappe.form_dict.get("items")
    if isinstance(items, str):
        items = json.loads(items)
    return list(items or [])


@frappe.whitelist()
def get_delete_policy(doctype, name):
    doc = frappe.get_doc(doctype, name)
    if not frappe.has_permission(doc=doc, ptype="delete"):
        frappe.throw(_("没有删除此单据的权限"), frappe.PermissionError)
    linked = _has_linked_ledger_entries(doctype, name)
    return {
        "has_linked_ledger_entries": linked,
        "requires_admin_password": linked,
        "can_delete": not linked or _is_admin(),
    }


@frappe.whitelist()
def get_bulk_delete_policy(doctype, names):
    names = _bulk_names(names)
    linked_names = []
    for name in names:
        doc = frappe.get_doc(doctype, name)
        if not frappe.has_permission(doc=doc, ptype="delete"):
            frappe.throw(_("没有删除此单据的权限"), frappe.PermissionError)
        if _has_linked_ledger_entries(doctype, name):
            linked_names.append(name)
    return {
        "linked_names": linked_names,
        "requires_admin_password": bool(linked_names),
        "can_delete": not linked_names or _is_admin(),
    }


@frappe.whitelist(methods=["DELETE", "POST"])
def delete(doctype, name, password=None):
    verified = _authorize_linked_delete(doctype, name, password)
    previous = getattr(frappe.flags, "solua_linked_delete_verified", False)
    frappe.flags.solua_linked_delete_verified = verified
    try:
        return frappe.delete_doc(doctype, name, ignore_missing=False)
    finally:
        frappe.flags.solua_linked_delete_verified = previous


@frappe.whitelist(methods=["POST", "DELETE"])
def delete_items(items=None, doctype=None, password=None):
    names = _bulk_names(items)
    doctype = doctype or frappe.form_dict.get("doctype")
    linked_names = [name for name in names if _has_linked_ledger_entries(doctype, name)]
    verified = False
    if linked_names:
        _authorize_linked_delete(doctype, linked_names[0], password)
        verified = True

    previous = getattr(frappe.flags, "solua_linked_delete_verified", False)
    frappe.flags.solua_linked_delete_verified = verified
    try:
        if linked_names and len(names) > 10:
            return native_delete_bulk(doctype, names)
        return native_delete_items()
    finally:
        frappe.flags.solua_linked_delete_verified = previous


def install():
    """Guard native deletes invoked by any web/API endpoint in this request."""
    if getattr(frappe, "_solua_linked_delete_guard_installed", False):
        return

    native_delete_doc = frappe.delete_doc

    def guarded_delete_doc(doctype=None, name=None, *args, **kwargs):
        depth = getattr(frappe.flags, "solua_delete_guard_depth", 0) or 0
        if depth:
            return native_delete_doc(doctype, name, *args, **kwargs)
        if _has_linked_ledger_entries(doctype, name) and not getattr(
            frappe.flags, "solua_linked_delete_verified", False
        ):
            frappe.throw(_("删除带账务关联的单据必须先通过管理员密码验证"), frappe.AuthenticationError)
        frappe.flags.solua_delete_guard_depth = depth + 1
        try:
            return native_delete_doc(doctype, name, *args, **kwargs)
        finally:
            frappe.flags.solua_delete_guard_depth = depth

    frappe.delete_doc = guarded_delete_doc
    frappe._solua_linked_delete_guard_installed = True
