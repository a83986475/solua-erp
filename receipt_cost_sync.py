# -*- coding: utf-8 -*-
"""Keep Standard Buying aligned with the newest submitted Material Receipt."""

import json

import frappe
from frappe.utils import flt, getdate, nowdate
from frappe import _

FIELD = "custom_receipt_cost_sync"
PRICE_LIST = "Standard Buying"


def ensure_field():
    """Create only the one Item field this feature needs."""
    if frappe.db.exists("Custom Field", {"dt": "Item", "fieldname": FIELD}):
        return
    frappe.get_doc({
        "doctype": "Custom Field",
        "dt": "Item",
        "fieldname": FIELD,
        "label": "入库成本同步记录",
        "fieldtype": "Long Text",
        "hidden": 1,
        "read_only": 1,
        "no_copy": 1,
        "insert_after": "custom_rate_cost",
    }).insert(ignore_permissions=True)


def _lock_items(item_codes):
    for item_code in sorted(set(item_codes)):
        frappe.db.sql("select name from `tabItem` where name = %s for update", item_code)


def _voucher_key(parent):
    get = parent.get if hasattr(parent, "get") else lambda key, default=None: getattr(parent, key, default)
    raw_time = get("posting_time") or "00:00:00"
    if hasattr(raw_time, "hour"):
        hour, minute, second = raw_time.hour, raw_time.minute, raw_time.second
        micros = getattr(raw_time, "microsecond", 0)
    else:
        parts = str(raw_time).split(":")
        hour, minute = int(parts[0]), int(parts[1])
        seconds = parts[2].split(".") if len(parts) > 2 else ["0"]
        second = int(seconds[0])
        micros = int((seconds[1] if len(seconds) > 1 else "0")[:6].ljust(6, "0"))
    return (str(get("posting_date")), int(hour), int(minute), int(second), int(micros),
            str(get("creation") or ""), str(get("name")))


def _entry_costs(stock_entry):
    if stock_entry.get("purpose") != "Material Receipt" or stock_entry.get("docstatus") != 1:
        return {}
    rows = frappe.get_all(
        "Stock Entry Detail",
        filters={"parent": stock_entry.name, "parenttype": "Stock Entry", "parentfield": "items"},
        fields=["item_code", "stock_uom", "transfer_qty", "amount"],
        limit_page_length=0,
    )
    totals = {}
    for row in rows:
        item_code = row.get("item_code")
        stock_uom = row.get("stock_uom")
        qty = flt(row.get("transfer_qty"))
        amount = flt(row.get("amount"))
        if not item_code or not stock_uom or qty <= 0 or amount <= 0:
            continue
        bucket = totals.setdefault((item_code, stock_uom), [0.0, 0.0])
        bucket[0] += amount
        bucket[1] += qty
    return {key: amount / qty for key, (amount, qty) in totals.items() if qty > 0 and amount > 0}


def _read_state(item):
    raw = item.get(FIELD)
    if not raw:
        return None
    try:
        state = json.loads(raw)
    except (TypeError, ValueError) as exc:
        frappe.throw(_("商品 {0} 的成本同步记录无法读取，请联系管理员。" ).format(item.name))
    if state.get("version") != 1 or not state.get("item_price"):
        frappe.throw(_("商品 {0} 的成本同步记录不完整，请联系管理员。" ).format(item.name))
    return state


def _company_currency(company):
    currency = frappe.db.get_value("Company", company, "default_currency")
    if currency != "MZN":
        frappe.throw(_("公司币种与到货成本同步要求不符，请先核对公司和价目表币种。"))
    if frappe.db.get_value("Price List", PRICE_LIST, "currency") != currency:
        frappe.throw(_("Standard Buying 价目表币种必须与公司币种一致。"))
    return currency


def _matching_prices(item_code, stock_uom, currency):
    today = nowdate()
    rows = frappe.get_all(
        "Item Price",
        filters={
            "item_code": item_code,
            "price_list": PRICE_LIST,
            "uom": stock_uom,
            "currency": currency,
        },
        fields=["name", "price_list_rate", "valid_from", "valid_upto", "buying", "selling",
                "item_code", "price_list", "uom", "currency", "supplier", "customer"],
        limit_page_length=0,
    )
    return [row for row in rows if row.buying and not row.selling and not row.supplier and not row.customer
            and (not row.valid_from or getdate(row.valid_from) <= getdate(today))
            and (not row.valid_upto or getdate(row.valid_upto) >= getdate(today))]


def current_reference_rate(item_code, stock_uom):
    """Return the active global Standard Buying rate, preferring stock UOM then blank UOM."""
    currency = frappe.db.get_value("Price List", PRICE_LIST, "currency")
    if not currency:
        return None
    rows = frappe.get_all(
        "Item Price",
        filters={"item_code": item_code, "price_list": PRICE_LIST},
        fields=["name", "price_list_rate", "valid_from", "valid_upto", "buying", "selling",
                "item_code", "price_list", "uom", "currency", "supplier", "customer", "modified"],
        limit_page_length=0,
    )
    today = getdate(nowdate())
    valid = [row for row in rows if row.buying and not row.selling and not row.supplier and not row.customer
        and row.currency == currency and row.uom in (stock_uom, None, "")
        and (not row.valid_from or getdate(row.valid_from) <= today)
        and (not row.valid_upto or getdate(row.valid_upto) >= today)]
    if not valid:
        return None
    selected = max(valid, key=lambda row: (
        bool(stock_uom and row.uom == stock_uom), str(row.valid_from or ""), str(row.modified or ""), str(row.name)
    ))
    rate = flt(selected.price_list_rate)
    return rate if rate > 0 else None


def _new_price(item_code, stock_uom, currency, rate):
    price = frappe.get_doc({
        "doctype": "Item Price",
        "item_code": item_code,
        "price_list": PRICE_LIST,
        "buying": 1,
        "selling": 0,
        "uom": stock_uom,
        "currency": currency,
        "price_list_rate": rate,
    })
    price.insert(ignore_permissions=True)
    return price, True


def _set_rate(state, item_code, stock_uom, currency, rate):
    price_name = state.get("item_price") if state else None
    if price_name:
        price = frappe.get_doc("Item Price", price_name)
        if (price.item_code != item_code or price.price_list != PRICE_LIST or price.uom != stock_uom
                or price.currency != currency or price.supplier or price.customer
                or not price.buying or price.selling):
            frappe.throw(_("商品 {0} 的定价参考成本记录已被更改，请先核对有效参考价。" ).format(item_code))
        price.price_list_rate = rate
        price.save(ignore_permissions=True)
        return price, bool(state.get("created"))

    rows = _matching_prices(item_code, stock_uom, currency)
    if len(rows) > 1:
        frappe.throw(_("商品 {0} 有多条有效的定价参考成本，系统无法判断应更新哪一条。" ).format(item_code))
    if not rows:
        return _new_price(item_code, stock_uom, currency, rate)
    price = frappe.get_doc("Item Price", rows[0].name)
    price.price_list_rate = rate
    price.save(ignore_permissions=True)
    return price, False


def _write_state(item_code, state):
    frappe.db.set_value("Item", item_code, FIELD, json.dumps(state, separators=(",", ":")), update_modified=False)


def _clear_state(item_code):
    frappe.db.set_value("Item", item_code, FIELD, None, update_modified=False)


def _latest_receipt(item_code, stock_uom, exclude_name=None):
    filters = {"item_code": item_code, "stock_uom": stock_uom, "parenttype": "Stock Entry",
               "parentfield": "items"}
    rows = frappe.get_all(
        "Stock Entry Detail",
        filters=filters,
        fields=["parent", "transfer_qty", "amount", "valuation_rate"],
        limit_page_length=0,
    )
    parents = {}
    for row in rows:
        if row.parent == exclude_name:
            continue
        parents.setdefault(row.parent, []).append(row)
    keys = {}
    for name in parents:
        parent = frappe.db.get_value("Stock Entry", name,
            ["purpose", "docstatus", "posting_date", "posting_time", "creation"], as_dict=True)
        if not parent or parent.purpose != "Material Receipt" or parent.docstatus != 1:
            continue
        if isinstance(parent, dict):
            parent = {**parent, "name": name}
        else:
            parent.name = name
        keys[name] = _voucher_key(parent)
    if not keys:
        return None
    latest_name = max(keys, key=keys.get)
    total_amount = total_qty = 0.0
    for row in parents[latest_name]:
        qty = flt(row.transfer_qty)
        amount = flt(row.amount)
        if qty > 0 and amount > 0:
            total_qty += qty
            total_amount += amount
    if total_qty <= 0 or total_amount <= 0:
        return None
    return {"name": latest_name, "key": list(keys[latest_name]), "rate": total_amount / total_qty}


def on_submit(doc, method=None):
    if doc.get("docstatus") != 1 or doc.get("purpose") != "Material Receipt":
        return
    costs = _entry_costs(doc)
    if not costs:
        return
    item_codes = [item_code for item_code, _ in costs]
    _lock_items(item_codes)
    company_currency = _company_currency(doc.company)
    for (item_code, stock_uom), rate in sorted(costs.items()):
        item = frappe.get_doc("Item", item_code)
        if item.stock_uom != stock_uom:
            frappe.throw(_("商品 {0} 的库存单位与入库明细不一致，请检查入库单。" ).format(item_code))
        state = _read_state(item)
        current_key = _voucher_key(doc)
        latest = _latest_receipt(item_code, stock_uom)
        if not latest or latest["name"] != doc.name:
            continue
        if state and tuple(state.get("latest_key") or ()) >= current_key:
            continue
        existing = _matching_prices(item_code, stock_uom, company_currency)
        if state:
            if not frappe.db.exists("Item Price", state["item_price"]):
                state = None
        if state:
            price = frappe.get_doc("Item Price", state["item_price"])
            if not _managed_price_matches(price, item_code, stock_uom, state):
                frappe.throw(_("商品 {0} 的定价参考成本记录或有效期已被更改，请先核对。" ).format(item_code))
            today = getdate(nowdate())
            if ((price.valid_from and getdate(price.valid_from) > today)
                    or (price.valid_upto and getdate(price.valid_upto) < today)):
                state = None
            elif not _managed_price_matches(price, item_code, stock_uom, state, check_rate=True):
                state = None
        baseline = None
        if state:
            baseline = state.get("baseline")
        else:
            if len(existing) > 1:
                frappe.throw(_("商品 {0} 有多条有效的定价参考成本，系统无法判断应更新哪一条。" ).format(item_code))
            baseline = ({"exists": True, "rate": flt(existing[0].price_list_rate)} if existing else {"exists": False})
        price, created = _set_rate(state, item_code, stock_uom, company_currency, rate)
        applied_rate = _stored_rate(price)
        _write_state(item_code, {
            "version": 1,
            "baseline": baseline,
            "item_price": price.name,
            "created": created,
            "applied_rate": applied_rate,
            "managed_dates": {"valid_from": str(price.valid_from or ""), "valid_upto": str(price.valid_upto or "")},
            "latest_voucher": doc.name,
            "latest_key": list(current_key),
        })


def on_cancel(doc, method=None):
    if doc.get("purpose") != "Material Receipt":
        return
    costs = _entry_costs_for_cancel(doc)
    if not costs:
        return
    _lock_items([item_code for item_code, _ in costs])
    for item_code, stock_uom in sorted(costs):
        item = frappe.get_doc("Item", item_code)
        state = _read_state(item)
        if not state or state.get("latest_voucher") != doc.name:
            continue
        if not frappe.db.exists("Item Price", state["item_price"]):
            _clear_state(item_code)
            continue
        price = frappe.get_doc("Item Price", state["item_price"])
        if not _managed_price_matches(price, item_code, stock_uom, state, check_rate=True):
            _clear_state(item_code)
            continue
        previous = _latest_receipt(item_code, stock_uom, exclude_name=doc.name)
        if previous:
            price.price_list_rate = previous["rate"]
            price.save(ignore_permissions=True)
            state.update({"applied_rate": _stored_rate(price), "latest_voucher": previous["name"],
                          "latest_key": previous["key"]})
            _write_state(item_code, state)
        elif state.get("baseline", {}).get("exists"):
            price.price_list_rate = state["baseline"]["rate"]
            price.save(ignore_permissions=True)
            _clear_state(item_code)
        elif state.get("created") and price.name == state.get("item_price"):
            price.delete(ignore_permissions=True)
            _clear_state(item_code)
        else:
            _clear_state(item_code)


def _managed_price_matches(price, item_code, stock_uom, state, check_rate=False):
    matches = (price.name == state.get("item_price") and price.item_code == item_code
        and price.price_list == PRICE_LIST and price.uom == stock_uom and price.currency == "MZN"
        and bool(price.buying) and not price.selling and not price.supplier and not price.customer
        and str(price.valid_from or "") == str((state.get("managed_dates") or {}).get("valid_from") or "")
        and str(price.valid_upto or "") == str((state.get("managed_dates") or {}).get("valid_upto") or ""))
    return matches and (not check_rate or _same_rate(price.price_list_rate, state.get("applied_rate")))


def _same_rate(left, right):
    return abs(flt(left) - flt(right)) < 0.0000000001


def _stored_rate(price):
    return flt(frappe.db.get_value("Item Price", price.name, "price_list_rate"))


def _entry_costs_for_cancel(doc):
    rows = frappe.get_all("Stock Entry Detail", filters={"parent": doc.name, "parenttype": "Stock Entry",
        "parentfield": "items"}, fields=["item_code", "stock_uom"], limit_page_length=0)
    return {(row.item_code, row.stock_uom) for row in rows if row.item_code and row.stock_uom}
