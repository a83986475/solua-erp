# solua_home/api/stock.py
# ============================
# 库存模块的自定义验证和事件处理
# ============================

import json
import random
from decimal import Decimal, InvalidOperation

import frappe
from frappe import _
from frappe.utils import cint, flt


def validate_positive_integer_qty(value, label="数量", item_code=None):
    """数量只能是大于等于 1 的整数；空值交给字段必填校验处理。"""
    if value in (None, ""):
        return

    try:
        qty = Decimal(str(value))
        valid = qty.is_finite() and qty >= 1 and qty == qty.to_integral_value()
    except (InvalidOperation, ValueError, TypeError):
        valid = False

    if not valid:
        target = item_code or label
        frappe.throw(_("{0} 的数量必须是大于等于 1 的整数，当前值为 {1}").format(target, value))


def validate_transaction_quantities(doc, method=None):
    """校验销售、采购和库存单据中的物料数量。"""
    for table_name in ("items", "locations"):
        for item in (doc.get(table_name) or []):
            if not item.get("item_code"):
                continue
            value = item.get("qty")
            # ERPNext 退货行用负数表示；仍要求绝对值为正整数。
            if doc.get("is_return") and flt(value) < 0:
                value = abs(Decimal(str(value)))
            validate_positive_integer_qty(value, "数量", item.item_code)


def _row_value(row, fieldname, default=None):
    value = row.get(fieldname) if hasattr(row, "get") else getattr(row, fieldname, default)
    return default if value is None else value


def _sales_order_names_for_draft(doc):
    """Return source orders for a draft Delivery Note or Pick List."""
    doctype = getattr(doc, "doctype", "")
    if doctype == "Delivery Note":
        return {
            _row_value(row, "against_sales_order")
            for row in (doc.get("items") or [])
            if _row_value(row, "against_sales_order")
        }
    if doctype == "Pick List":
        names = {
            _row_value(row, "sales_order")
            for row in (doc.get("locations") or [])
            if _row_value(row, "sales_order")
        }
        if doc.get("custom_sales_order"):
            names.add(doc.custom_sales_order)
        return names
    return set()


def _lock_sales_orders(order_names):
    """Serialize draft creation for each source order in this transaction."""
    for order_name in sorted({name for name in order_names if name}):
        frappe.db.sql(
            "SELECT name FROM `tabSales Order` WHERE name=%s FOR UPDATE",
            (order_name,),
        )


def _existing_draft_for_sales_order(doctype, child_doctype, source_field, sales_order, exclude=None):
    parents = frappe.get_all(
        child_doctype,
        filters={source_field: sales_order, "parenttype": doctype},
        pluck="parent",
        limit_page_length=100,
    )
    if not parents:
        return None
    drafts = frappe.get_all(
        doctype,
        filters={"name": ["in", list(dict.fromkeys(parents))], "docstatus": 0},
        fields=["name"],
        order_by="modified desc",
        limit_page_length=100,
    )
    for row in drafts:
        if row.name != exclude:
            return frappe.get_doc(doctype, row.name)
    return None


def get_existing_draft_delivery_note(sales_order, exclude=None):
    return _existing_draft_for_sales_order(
        "Delivery Note", "Delivery Note Item", "against_sales_order", sales_order, exclude
    )


def get_existing_draft_pick_list(sales_order, exclude=None):
    return _existing_draft_for_sales_order(
        "Pick List", "Pick List Item", "sales_order", sales_order, exclude
    )


def validate_single_draft_source(doc, method=None):
    """Allow one source-order draft; submitted partial documents remain valid."""
    if doc.get("docstatus") != 0 or doc.get("is_return"):
        return
    order_names = _sales_order_names_for_draft(doc)
    if not order_names:
        return
    _lock_sales_orders(order_names)
    doctype = getattr(doc, "doctype", "")
    finder = get_existing_draft_delivery_note if doctype == "Delivery Note" else get_existing_draft_pick_list
    for order_name in order_names:
        existing = finder(order_name, exclude=doc.name)
        if existing:
            label = "交货单" if doctype == "Delivery Note" else "拣货单"
            frappe.throw(_("销售订单 {0} 已有{1}草稿 {2}，请打开现有草稿继续编辑。").format(
                order_name, label, existing.name
            ))


def _row_stock_qty(row, qty_field="qty"):
    stock_qty = flt(_row_value(row, "stock_qty", 0))
    if stock_qty:
        return stock_qty
    factor = flt(_row_value(row, "conversion_factor", 1)) or 1
    return flt(_row_value(row, qty_field, 0)) * factor


def _is_stock_item(item_code, row=None):
    if row is not None and _row_value(row, "is_stock_item") is not None:
        return bool(_row_value(row, "is_stock_item"))
    return bool(frappe.get_cached_value("Item", item_code, "is_stock_item"))


def _has_product_bundle(doc, item_code):
    checker = getattr(doc, "has_product_bundle", None)
    if not checker:
        return False
    try:
        return bool(checker(item_code))
    except TypeError:
        return bool(checker())


def _add_stock_requirement(target, item_code, warehouse, qty):
    qty = flt(qty)
    if not item_code or not warehouse or qty <= 0:
        return
    key = (item_code, warehouse)
    target[key] = target.get(key, 0) + qty


def get_sales_order_stock_requirements(doc):
    """Return remaining demand in Stock UOM, including Product Bundle components."""
    requirements = {}
    delivered_field = "delivered_qty"
    if frappe.get_cached_value(
        "Selling Settings", "Selling Settings", "dont_reserve_sales_order_qty_on_sales_return"
    ):
        delivered_field = "delivered_qty_with_returns"
    packed_by_parent = {}
    for packed in doc.get("packed_items") or []:
        packed_by_parent.setdefault(_row_value(packed, "parent_detail_docname"), []).append(packed)

    for item in doc.get("items") or []:
        item_code = _row_value(item, "item_code")
        if not item_code or _row_value(item, "delivered_by_supplier"):
            continue
        warehouse = _row_value(item, "warehouse") or doc.get("set_warehouse")
        packed_rows = packed_by_parent.get(_row_value(item, "name"), [])
        delivered_qty = flt(_row_value(item, "delivered_qty"))
        if delivered_field == "delivered_qty_with_returns":
            delivered_qty += flt(_row_value(item, "returned_qty"))
        if packed_rows and _has_product_bundle(doc, item_code):
            ordered_qty = flt(_row_value(item, "qty"))
            remaining_ratio = max(ordered_qty - delivered_qty, 0) / ordered_qty if ordered_qty else 0
            for packed in packed_rows:
                _add_stock_requirement(
                    requirements,
                    _row_value(packed, "item_code"),
                    _row_value(packed, "warehouse") or warehouse,
                    flt(_row_value(packed, "qty")) * remaining_ratio,
                )
            continue
        if not _is_stock_item(item_code, item):
            continue
        factor = flt(_row_value(item, "conversion_factor", 1)) or 1
        remaining = max(_row_stock_qty(item) - delivered_qty * factor, 0)
        _add_stock_requirement(requirements, item_code, warehouse, remaining)
    return requirements


def _warehouse_names(warehouse):
    from erpnext.stock.doctype.warehouse.warehouse import get_child_warehouses

    warehouses = list(get_child_warehouses(warehouse) or [])
    if warehouse not in warehouses:
        warehouses.append(warehouse)
    return warehouses


def _lock_bin_rows(item_code, warehouse):
    if not warehouse:
        return
    warehouses = _warehouse_names(warehouse)
    bin_table = frappe.qb.DocType("Bin")
    frappe.qb.from_(bin_table).select(bin_table.name).where(
        (bin_table.item_code == item_code) & bin_table.warehouse.isin(warehouses)
    ).for_update().run()


def validate_stock_requirements(requirements, company, self_reserved=None, message="库存不足"):
    """Check actual stock less live Sales Order reservations, locking Bin rows first."""
    self_reserved = self_reserved or {}
    shortages = []
    from erpnext.stock.get_item_details import get_bin_details
    from erpnext.stock.stock_balance import get_reserved_qty

    for (item_code, warehouse), required_qty in sorted(requirements.items()):
        _lock_bin_rows(item_code, warehouse)
        bin_details = get_bin_details(item_code, warehouse, company, include_child_warehouses=True) or {}
        actual_qty = flt(bin_details.get("actual_qty"))
        # Bin.reserved_qty is a denormalized rollup refreshed after submit; use
        # the native live Sales Order query while the Bin rows are locked.
        reserved_qty = sum(flt(get_reserved_qty(item_code, child)) for child in _warehouse_names(warehouse))
        available_qty = actual_qty - reserved_qty + flt(self_reserved.get((item_code, warehouse)))
        if required_qty > available_qty + 0.000001:
            shortages.append(_("{0}（仓库：{1}，需求：{2}，实际：{3}，预留：{4}，可用：{5}）").format(
                item_code, warehouse, required_qty, actual_qty, reserved_qty, available_qty
            ))

    if shortages:
        frappe.throw(_("{0}：<br>{1}").format(message, "<br>".join(shortages)))


def copy_sales_order_pick_notes(doc, method=None):
    """从销售订单复制拣货备注到拣货单，保留用户手工填写的值。"""
    locations = doc.get("locations") or []
    has_line_notes = frappe.get_meta("Pick List Item").has_field("custom_additional_notes")
    has_header_notes = frappe.get_meta("Pick List").has_field("custom_additional_notes")
    order_names = []
    order_item_cache = {}

    for row in locations:
        order_item = row.get("sales_order_item")
        source = order_item_cache.get(order_item) if order_item else None
        if order_item and source is None:
            source_fields = ["parent", "additional_notes"]
            if frappe.get_meta("Sales Order Item").has_field("pos_additional_notes"):
                source_fields.append("pos_additional_notes")
            source = frappe.db.get_value(
                "Sales Order Item", order_item, source_fields, as_dict=True
            ) or {}
            order_item_cache[order_item] = source

        sales_order = row.get("sales_order") or (source.get("parent") if source else "")
        if sales_order and sales_order not in order_names:
            order_names.append(sales_order)
        if has_line_notes and not row.get("custom_additional_notes"):
            note = (source.get("additional_notes") or source.get("pos_additional_notes")) if source else ""
            if note:
                row.custom_additional_notes = note

    if has_header_notes and not doc.get("custom_additional_notes") and order_names:
        notes = []
        for sales_order in order_names:
            note = frappe.db.get_value("Sales Order", sales_order, "custom_additional_notes")
            if note and note not in [value for _, value in notes]:
                notes.append((sales_order, note))
        if len(notes) == 1:
            doc.custom_additional_notes = notes[0][1]
        elif notes:
            doc.custom_additional_notes = "\n".join(f"{sales_order}: {note}" for sales_order, note in notes)

    if frappe.get_meta("Pick List").has_field("custom_sales_order") and len(order_names) == 1:
        doc.custom_sales_order = order_names[0]


@frappe.whitelist()
def make_delivery_note(source_name, target_doc=None, kwargs=None):
    """Reuse an existing draft before opening the native mapped Delivery Note."""
    if target_doc is None:
        existing = get_existing_draft_delivery_note(source_name)
        if existing:
            return existing
    from erpnext.selling.doctype.sales_order.mapper import make_delivery_note as native_make_delivery_note

    return native_make_delivery_note(source_name, target_doc, kwargs=kwargs)


@frappe.whitelist()
def create_pick_list(source_name, target_doc=None):
    """Keep the source Sales Order even when the native mapper creates no location rows."""
    if target_doc is None:
        existing = get_existing_draft_pick_list(source_name)
        if existing:
            return existing
    from erpnext.selling.doctype.sales_order.mapper import create_pick_list as native_create_pick_list

    doc = native_create_pick_list(source_name, target_doc)
    if frappe.get_meta("Pick List").has_field("custom_sales_order"):
        doc.custom_sales_order = source_name
    return doc


def validate_product_bundle_definition(doc, method=None):
    """校验打包定义的包含数量。"""
    validate_positive_integer_qty(doc.get("quantity"), "打包包含数量", doc.get("parent_item"))


def validate_stock_reconciliation_quantities(doc, method=None):
    """盘点数量允许 0（用于清零），但不允许小数或负数。"""
    for item in doc.get("items", []):
        if not item.get("item_code") or item.get("qty") in (None, ""):
            continue
        try:
            qty = Decimal(str(item.get("qty")))
            valid = qty.is_finite() and qty >= 0 and qty == qty.to_integral_value()
        except (InvalidOperation, ValueError, TypeError):
            valid = False
        if not valid:
            frappe.throw(
                _("物料 {0} 的盘点数量必须是大于等于 0 的整数，当前值为 {1}").format(
                    item.item_code, item.get("qty")
                )
            )


# ---------------------------------------------------------------------------
# EAN-13 条码工具（校验位计算 + 自动生成）
# ---------------------------------------------------------------------------

def calc_ean13_checksum(code12):
    """计算 EAN-13 校验位。code12 为前 12 位（数字字符串或 12 位数字）。"""
    digits = str(code12)
    if not digits.isdigit() or len(digits) != 12:
        return None
    total = sum(int(d) * (3 if i % 2 else 1) for i, d in enumerate(digits))
    return (10 - total % 10) % 10


def is_valid_ean13(barcode):
    """校验 EAN-13 条码（13 位数字 + 校验位正确）"""
    s = str(barcode)
    if not s.isdigit() or len(s) != 13:
        return False
    cs = calc_ean13_checksum(s[:12])
    return cs is not None and int(s[-1]) == cs


def generate_unique_barcode():
    """生成一个当前库里不存在的 13 位 Code 128 条码（无需校验位）。

    2026-08-08 简化：放弃 EAN-13 校验位，统一 Code 128 编码——
    扫码枪两种码制都读，只要条码值不重复即可。
    格式 69 + 11 位随机数字；去重检查 Item Barcode 子表 + custom_label_barcode，
    碰撞重试（最多 20 次）。
    """
    for _ in range(20):
        barcode = "69" + "".join(str(random.randint(0, 9)) for _ in range(11))
        if frappe.db.exists("Item Barcode", {"barcode": barcode}):
            continue
        if frappe.db.get_value("Item", {"custom_label_barcode": barcode}, "name"):
            continue
        return barcode
    return None


# ---------------------------------------------------------------------------
# Item 事件
# ---------------------------------------------------------------------------

def before_validate_item(doc, method=None):
    """物料保存前执行（必须在 ERPNext 自带校验之前）

    1. 厂家条码校验位容错：barcode_type 填了 EAN 且校验位错误的条码，
       自动把 barcode_type 置空 → ERPNext 跳过格式校验（防重复仍在），
       否则建档会被 InvalidBarcode 拒收。
    2. 无条码自动生成：非变体物料没有条码时，自动生成标签条码。
    3. 用户根据供应商实物色卡填写固定色号；系统校验后组合对外订货货号。
    """
    # 1. 校验位容错：EAN 类型条码校验位错误 → 清空 barcode_type
    for row in doc.get("barcodes", []):
        bt = (row.get("barcode_type") or "").lower()
        bc = row.get("barcode")
        if bc and bt in ("ean", "ean13") and not is_valid_ean13(bc):
            row.barcode_type = ""
            frappe.msgprint(
                _("条码 {0} 校验位有误，已跳过 EAN 格式校验（防重复检查保留）").format(bc),
                alert=True,
            )

    # 2. 无条码自动生成（仅非变体）
    # barcode_type 留空：ERPNext 只保留选项表内的类型（无 Code128），
    # 空类型跳过一切格式校验，只剩防重复检查——符合「只要条码不重复」策略；
    # 标签渲染统一 Code 128，与类型无关。
    if not doc.variant_of and not any((r.get("barcode") or "").strip() for r in doc.get("barcodes", [])):
        generated = generate_unique_barcode()
        if generated:
            doc.append("barcodes", {"barcode": generated})
            doc.custom_label_barcode = generated
            frappe.msgprint(
                _("未填写条码，已自动生成：{0}").format(generated),
                alert=True,
            )

    # 变体默认继承模板的对外货号；保留显式值，方便其他商品继续使用独立货号。
    if doc.get("variant_of") and frappe.db.has_column("Item", "custom_order_code") and not doc.get("custom_order_code"):
        inherited_order_code = frappe.db.get_value("Item", doc.variant_of, "custom_order_code")
        if inherited_order_code:
            doc.custom_order_code = inherited_order_code


def validate_item(doc, method=None):
    """物料保存时验证"""
    # ERPNext 原生创建 Variant 时不会复制 valuation_rate；有模板默认成本时补上，
    # 没有则让下面的校验明确拦截，避免生成零成本的可销售 SKU。
    if (
        doc.is_new()
        and doc.get("variant_of")
        and flt(doc.get("valuation_rate")) <= 0
    ):
        template_rate = flt(frappe.db.get_value("Item", doc.variant_of, "valuation_rate") or 0)
        if template_rate > 0:
            doc.valuation_rate = template_rate

    # 普通库存物料/具体变体必须带正数成本；模板只负责生成变体，可暂不设成本。
    if (
        doc.is_new()
        and cint(doc.get("is_stock_item"))
        and not cint(doc.get("is_customer_provided_item"))
        and not cint(doc.get("has_variants"))
        and flt(doc.get("valuation_rate")) <= 0
    ):
        frappe.throw(
            _(
                "库存物料建档时必须填写大于 0 的“成本价”（Valuation Rate）；"
                "物料模板可暂不填写；创建具体物料或变体前，请先维护成本价。"
            )
        )

    # 物料编码规则校验：至少 3 位
    if doc.item_code and len(doc.item_code) < 3:
        frappe.throw(_("物料编码长度不能少于3位"))

    # custom_color_code is retired UI data. Native Item Variant Attribute.Cor
    # owns current color identity; preserve the old field but never validate,
    # generate, or deduplicate new items from it.

    if frappe.db.has_column("Item", "custom_order_code") and doc.get("custom_order_code"):
        current_family = doc.get("variant_of") or doc.get("name") or doc.get("item_code")
        existing = frappe.get_all(
            "Item",
            filters={"custom_order_code": doc.custom_order_code, "name": ["!=", doc.name]},
            fields=["name", "variant_of", "has_variants"],
        )
        conflict = next(
            (row for row in existing if (row.get("variant_of") or row.get("name")) != current_family),
            None,
        )
        if conflict:
            frappe.throw(_("对外订货货号 {0} 已被其他款式物料 {1} 使用；同一模板的颜色变体可以共用").format(
                doc.custom_order_code, conflict.get("name")
            ))

    # 物料名称校验：只拦截危险字符（< > " '），放开常见字符（如 /、&、:、（））
    # 2026-08-15 用户要求放开：导入真实物料时名称常含 "/"（如 "140×200 / Algodão"），
    # 斜杠无实际危害，只影响打印/文件名观感，不应因此拦建档
    import re
    if doc.item_name and re.search(r'[<>"\']', doc.item_name):
        frappe.throw(_("物料名称不能包含特殊字符（< > \" \'）"))

    # 颜色变体优先使用自己的条码；没有独立条码时才继承模板条码。
    attributes = doc.get("attributes") or []
    has_color_attribute = any(row.get("attribute") == "Cor" for row in attributes)
    if doc.variant_of and has_color_attribute:
        own_barcodes = []
        for row in doc.get("barcodes") or []:
            value = str(row.get("barcode") or "").strip()
            if value and value not in own_barcodes:
                own_barcodes.append(value)

        if len(own_barcodes) == 1:
            doc.custom_label_barcode = own_barcodes[0]
            return

        template_barcodes = frappe.get_all(
            "Item Barcode",
            filters={"parent": doc.variant_of},
            pluck="barcode",
        )
        unique_barcodes = []
        for value in template_barcodes:
            value = str(value or "").strip()
            if value and value not in unique_barcodes:
                unique_barcodes.append(value)

        if len(unique_barcodes) == 1:
            doc.custom_label_barcode = unique_barcodes[0]
        else:
            reason = _("没有非空 Item Barcode") if not unique_barcodes else _("有多个不同 Item Barcode")
            frappe.msgprint(
                _("模板 {0} {1}，无法确定颜色变体 {2} 的共享标签条码；保留当前值。").format(
                    doc.variant_of, reason, doc.name
                ),
                alert=True,
                indicator="orange",
            )
    elif doc.variant_of:
        # 非颜色变体沿用既有规则。
        barcode = doc.barcodes[0].get("barcode") if doc.barcodes else None
        doc.custom_label_barcode = barcode or doc.name
    elif not doc.get("custom_label_barcode"):
        # 非变体：子表第一条条码（无条码时 before_validate 已自动生成 EAN-13）
        barcode = doc.barcodes[0].get("barcode") if doc.barcodes else None
        if barcode:
            doc.custom_label_barcode = barcode


def on_stock_entry_submitted(doc, method=None):
    """库存入库/出库提交后"""
    # 示例：库存变更后通知
    if doc.stock_entry_type == "Material Transfer":
        frappe.msgprint(_("物料转移单 {0} 已提交").format(doc.name))


def _pick_list_source_orders(doc):
    names = []
    custom_name = _row_value(doc, "custom_sales_order")
    if custom_name:
        names.append(custom_name)

    for row in doc.get("locations") or []:
        sales_order = _row_value(row, "sales_order")
        if not sales_order and _row_value(row, "sales_order_item"):
            sales_order = frappe.db.get_value(
                "Sales Order Item", _row_value(row, "sales_order_item"), "parent"
            )
        if sales_order and sales_order not in names:
            names.append(sales_order)
    return names


def _merge_pick_list_order_comparison(doc, order_names, expected, expected_meta):
    picked_by_key = {}
    picked_keys_by_order_item = {}
    for row in doc.get("locations") or []:
        sales_order_item = _row_value(row, "sales_order_item")
        item_code = _row_value(row, "item_code")
        if not sales_order_item or not item_code:
            continue
        key = (sales_order_item, item_code)
        entry = picked_by_key.setdefault(key, {"planned": 0, "picked": 0})
        entry["planned"] += _row_stock_qty(row)
        entry["picked"] += flt(_row_value(row, "picked_qty"))
        picked_keys_by_order_item.setdefault(sales_order_item, set()).add(key)

    rows = []
    matched_renamed_keys = set()
    tolerance = 0.000001
    for key, required_stock in expected.items():
        meta = dict(expected_meta[key])
        picked = picked_by_key.get(key, {})
        if not picked:
            # Submitted snapshots can contain an old Item code; the Sales Order
            # row is the stable identity for a non-bundle line.
            candidates = picked_keys_by_order_item.get(key[0], set())
            if len(candidates) == 1:
                renamed_key = next(iter(candidates))
                picked = picked_by_key[renamed_key]
                matched_renamed_keys.add(renamed_key)
        planned_stock = flt(picked.get("planned"))
        picked_stock = flt(picked.get("picked"))
        shortage_stock = max(required_stock - picked_stock, 0)
        if shortage_stock <= tolerance:
            status = "已拣齐"
        elif picked_stock > tolerance:
            status = "部分拣货"
        else:
            status = "缺货/未生成拣货行"
        meta.update({
            "order_qty": required_stock,
            "planned_qty": planned_stock,
            "picked_qty": picked_stock,
            "shortage_qty": shortage_stock,
            "status": status,
            "missing": planned_stock <= tolerance,
        })
        rows.append(meta)

    for key, picked in picked_by_key.items():
        if key in expected or key in matched_renamed_keys:
            continue
        sales_order_item, item_code = key
        rows.append({
            "sales_order": _row_value(doc, "custom_sales_order") or "",
            "sales_order_item": sales_order_item,
            "item_code": item_code,
            "item_name": item_code,
            "stock_uom": "",
            "order_qty": 0,
            "planned_qty": flt(picked.get("planned")),
            "picked_qty": flt(picked.get("picked")),
            "shortage_qty": 0,
            "status": "拣货单多出",
            "missing": False,
            "extra": True,
        })

    shortage_rows = [row for row in rows if flt(row.get("shortage_qty")) > tolerance]
    return {
        "sales_orders": order_names,
        "rows": rows,
        "summary": {
            "order_qty": sum(flt(row.get("order_qty")) for row in rows),
            "planned_qty": sum(flt(row.get("planned_qty")) for row in rows),
            "picked_qty": sum(flt(row.get("picked_qty")) for row in rows),
            "shortage_qty": sum(flt(row.get("shortage_qty")) for row in rows),
            "shortage_count": len(shortage_rows),
            "missing_count": sum(1 for row in shortage_rows if row.get("missing")),
            "extra_count": sum(1 for row in rows if row.get("extra")),
            "complete": not shortage_rows and not any(row.get("extra") for row in rows),
        },
    }


def _pick_list_order_comparison(doc):
    """Compare a Pick List with every remaining stock line on its Sales Order(s)."""
    order_names = _pick_list_source_orders(doc)

    # Submission updates Sales Order.picked_qty. Keep the pre-submit order
    # quantities so a submitted Pick List remains a reliable audit snapshot.
    snapshot_data = _row_value(doc, "custom_sales_order_comparison_data") if cint(doc.get("docstatus")) == 1 else None
    if snapshot_data:
        try:
            snapshot = json.loads(snapshot_data) if isinstance(snapshot_data, str) else snapshot_data
            snapshot_orders = snapshot.get("sales_orders") or []
            expected = {}
            expected_meta = {}
            for row in snapshot.get("rows") or []:
                sales_order_item = _row_value(row, "sales_order_item")
                item_code = _row_value(row, "item_code")
                order_qty = flt(_row_value(row, "order_qty"))
                if not sales_order_item or not item_code or order_qty <= 0:
                    continue
                key = (sales_order_item, item_code)
                expected[key] = order_qty
                expected_meta[key] = {
                    "sales_order": _row_value(row, "sales_order") or "",
                    "sales_order_item": sales_order_item,
                    "item_code": item_code,
                    "item_name": _row_value(row, "item_name") or item_code,
                    "stock_uom": _row_value(row, "stock_uom") or "",
                }
            if expected:
                return _merge_pick_list_order_comparison(
                    doc,
                    snapshot_orders or order_names,
                    expected,
                    expected_meta,
                )
        except (TypeError, ValueError, json.JSONDecodeError):
            pass

    expected = {}
    expected_meta = {}
    order_cache = {}

    for order_name in order_names:
        order = order_cache.get(order_name)
        if order is None:
            order = frappe.get_doc("Sales Order", order_name)
            order_cache[order_name] = order

        packed_by_parent = {}
        for packed in order.get("packed_items") or []:
            packed_by_parent.setdefault(_row_value(packed, "parent_detail_docname"), []).append(packed)

        for item in order.get("items") or []:
            if _row_value(item, "delivered_by_supplier"):
                continue

            item_name = _row_value(item, "name")
            item_code = _row_value(item, "item_code")
            if not item_name or not item_code:
                continue

            factor = flt(_row_value(item, "conversion_factor", 1)) or 1
            picked_uom = flt(_row_value(item, "picked_qty")) / factor
            delivered_uom = flt(_row_value(item, "delivered_qty"))
            remaining_uom = max(flt(_row_value(item, "qty")) - max(picked_uom, delivered_uom), 0)
            packed_rows = packed_by_parent.get(item_name, [])

            if packed_rows and _has_product_bundle(order, item_code):
                ordered_uom = flt(_row_value(item, "qty"))
                remaining_ratio = remaining_uom / ordered_uom if ordered_uom else 0
                for packed in packed_rows:
                    component_code = _row_value(packed, "item_code")
                    required_stock = _row_stock_qty(packed) * remaining_ratio
                    if not component_code or required_stock <= 0:
                        continue
                    key = (item_name, component_code)
                    expected[key] = expected.get(key, 0) + required_stock
                    expected_meta[key] = {
                        "sales_order": order_name,
                        "sales_order_item": item_name,
                        "item_code": component_code,
                        "item_name": _row_value(packed, "item_name") or component_code,
                        "stock_uom": _row_value(packed, "stock_uom")
                        or frappe.get_cached_value("Item", component_code, "stock_uom")
                        or "",
                    }
                continue

            if not _is_stock_item(item_code, item):
                continue

            required_stock = max(_row_stock_qty(item) - max(
                flt(_row_value(item, "picked_qty")), delivered_uom * factor
            ), 0)
            if required_stock <= 0:
                continue
            key = (item_name, item_code)
            expected[key] = expected.get(key, 0) + required_stock
            expected_meta[key] = {
                "sales_order": order_name,
                "sales_order_item": item_name,
                "item_code": item_code,
                "item_name": _row_value(item, "item_name") or item_code,
                "stock_uom": _row_value(item, "stock_uom")
                or frappe.get_cached_value("Item", item_code, "stock_uom")
                or "",
            }

    return _merge_pick_list_order_comparison(doc, order_names, expected, expected_meta)


@frappe.whitelist()
def get_pick_list_sales_order_comparison(pick_list):
    doc = frappe.get_doc("Pick List", pick_list)
    doc.check_permission("read")
    return _pick_list_order_comparison(doc)


def _active_pick_list_for_sales_order_item(sales_order_item):
    if not sales_order_item:
        return None
    rows = frappe.db.sql(
        """SELECT i.parent, i.name FROM `tabPick List Item` i
        JOIN `tabPick List` p ON p.name=i.parent
        WHERE p.docstatus=1 AND i.sales_order_item=%s
        LIMIT 1""",
        (sales_order_item,),
        as_dict=True,
    )
    return rows[0] if rows else None


def _validate_delivery_pick_rows(doc):
    current_by_pick_item = {}
    row_by_pick_item = {}
    for row in doc.get("items") or []:
        pick_item = _row_value(row, "pick_list_item")
        against_pick_list = _row_value(row, "against_pick_list")
        if not pick_item and not against_pick_list:
            continue
        if not pick_item or not against_pick_list:
            frappe.throw(_("交货单拣货路径缺少 Pick List 行关联：{0}").format(_row_value(row, "item_code")))
        current_by_pick_item[pick_item] = current_by_pick_item.get(pick_item, 0) + _row_stock_qty(row)
        row_by_pick_item[pick_item] = row

    for pick_item, current_qty in current_by_pick_item.items():
        pick = frappe.db.get_value(
            "Pick List Item",
            pick_item,
            ["parent", "item_code", "warehouse", "picked_qty", "delivered_qty", "sales_order_item"],
            as_dict=True,
        )
        row = row_by_pick_item[pick_item]
        if not pick or pick.parent != _row_value(row, "against_pick_list"):
            frappe.throw(_("交货单引用的 Pick List 行不存在或不匹配：{0}").format(pick_item))
        if cint(frappe.db.get_value("Pick List", pick.parent, "docstatus")) != 1:
            frappe.throw(_("交货单只能引用已提交的 Pick List：{0}").format(pick.parent))
        if pick.item_code != _row_value(row, "item_code"):
            is_bundle_parent = (
                pick.sales_order_item
                and pick.sales_order_item == _row_value(row, "so_detail")
                and not _is_stock_item(_row_value(row, "item_code"), row)
            )
            if not is_bundle_parent:
                frappe.throw(_("交货单物料与 Pick List 不匹配：{0}").format(_row_value(row, "item_code")))
        if _row_value(row, "warehouse") and pick.warehouse and _row_value(row, "warehouse") != pick.warehouse:
            frappe.throw(_("交货单仓库与 Pick List 不匹配：{0}").format(_row_value(row, "item_code")))

        prior_delivered = flt(frappe.db.sql(
            """SELECT COALESCE(SUM(i.stock_qty),0) FROM `tabDelivery Note Item` i
            JOIN `tabDelivery Note` d ON d.name=i.parent
            WHERE d.docstatus=1 AND COALESCE(d.is_return,0)=0 AND d.name<>%s
            AND i.pick_list_item=%s""",
            (doc.name or "", pick_item),
        )[0][0])
        allowed_qty = flt(pick.picked_qty)
        if prior_delivered + current_qty > allowed_qty + 0.000001:
            frappe.throw(_("交货单数量超过实际已拣数量：{0}（已拣 {1}，此前已交 {2}，本次 {3}）").format(
                pick.item_code, allowed_qty, prior_delivered, current_qty
            ))


def _get_direct_delivery_requirements(doc):
    requirements = {}
    self_reserved = {}
    source_cache = {}
    bundle_parent_names = set()

    for row in doc.get("items") or []:
        if not _row_value(row, "against_sales_order") or _row_value(row, "pick_list_item"):
            continue
        order_name = _row_value(row, "against_sales_order")
        source = source_cache.get(order_name)
        if source is None:
            source = frappe.get_doc("Sales Order", order_name)
            source_cache[order_name] = source
        if _has_product_bundle(source, _row_value(row, "item_code")):
            bundle_parent_names.add(_row_value(row, "name"))
            continue
        if _is_stock_item(_row_value(row, "item_code"), row):
            _add_stock_requirement(
                requirements,
                _row_value(row, "item_code"),
                _row_value(row, "warehouse") or doc.get("set_warehouse"),
                _row_stock_qty(row),
            )

    for packed in doc.get("packed_items") or []:
        if _row_value(packed, "parent_detail_docname") not in bundle_parent_names:
            continue
        _add_stock_requirement(
            requirements,
            _row_value(packed, "item_code"),
            _row_value(packed, "warehouse") or doc.get("set_warehouse"),
            _row_stock_qty(packed),
        )

    for source in source_cache.values():
        if cint(source.docstatus) != 1:
            continue
        for key, qty in get_sales_order_stock_requirements(source).items():
            self_reserved[key] = self_reserved.get(key, 0) + qty
    return requirements, self_reserved


def validate_delivery_route(doc, method=None):
    """Keep direct and Pick List delivery paths quantity-safe before submit."""
    if doc.get("is_return") or doc.get("docstatus") in (1, 2):
        return

    _validate_delivery_pick_rows(doc)
    for row in doc.get("items") or []:
        if _row_value(row, "pick_list_item") or not _row_value(row, "against_sales_order"):
            continue
        active_pick = _active_pick_list_for_sales_order_item(_row_value(row, "so_detail"))
        if active_pick:
            frappe.throw(_("销售订单行 {0} 已有有效 Pick List，请从 Pick List 生成交货单；如需直送，请先取消该 Pick List。").format(
                _row_value(row, "so_detail")
            ))

    requirements, self_reserved = _get_direct_delivery_requirements(doc)
    validate_stock_requirements(
        requirements,
        doc.get("company"),
        self_reserved=self_reserved,
        message="直送交货单库存不足，不能保存或提交",
    )


def validate_pick_list_result(doc, method=None, require_result=False):
    """Require an explicit full/partial shortage result before Pick List submit."""
    if doc.get("purpose") != "Delivery" or not frappe.get_meta("Pick List").has_field("custom_pick_result"):
        return

    result = doc.get("custom_pick_result")
    allowed = {"待拣货", "已拣齐", "部分拣货", "缺货待补"}
    if result and result not in allowed:
        frappe.throw(_("拣货结果无效，请重新选择"))
    if require_result and result not in {"已拣齐", "部分拣货", "缺货待补"}:
        frappe.throw(_("提交拣货单前必须选择：已拣齐、部分拣货或缺货待补"))
    if not result or result == "待拣货":
        return

    doc.pick_manually = 1
    doc.scan_mode = 1
    locations = doc.get("locations") or []
    shortage_qty = 0
    picked_qty = 0
    for row in locations:
        requested = _row_stock_qty(row)
        picked = flt(_row_value(row, "picked_qty"))
        if picked < -0.000001 or picked > requested + 0.000001:
            frappe.throw(_("{0} 的已拣数量不能超过需求数量或小于0").format(_row_value(row, "item_code")))
        picked_qty += picked
        shortage_qty += max(requested - picked, 0)

    if result == "已拣齐":
        if not locations or shortage_qty > 0.000001:
            frappe.throw(_("拣货结果选择为已拣齐时，所有拣货行必须填写实际已拣数量"))
    elif result == "部分拣货" and picked_qty <= 0:
        frappe.throw(_("部分拣货至少要有一行实际已拣数量；全部缺货请选择缺货待补"))
    elif result == "缺货待补" and not (_row_value(doc, "custom_shortage_note") or "").strip():
        frappe.throw(_("缺货待补必须填写缺货说明"))

    comparison = _pick_list_order_comparison(doc)
    summary = comparison["summary"]
    if comparison["sales_orders"] and result == "已拣齐" and not summary["complete"]:
        details = "<br>".join(
            _("{0}：订单待拣 {1}，实际已拣 {2}，缺货 {3}").format(
                row["item_code"], row["order_qty"], row["picked_qty"], row["shortage_qty"]
            )
            for row in comparison["rows"]
            if flt(row.get("shortage_qty")) > 0.000001 or row.get("extra")
        )
        frappe.throw(_("销售订单对比未通过，不能标记为已拣齐：<br>{0}").format(details))
    if comparison["sales_orders"] and result in {"部分拣货", "缺货待补"} and summary["complete"]:
        frappe.throw(_("销售订单对比显示没有缺货或未拣数量；如已全部拣齐，请选择已拣齐"))

    if require_result and comparison["sales_orders"] and frappe.get_meta("Pick List").has_field(
        "custom_sales_order_comparison_data"
    ):
        doc.custom_sales_order_comparison_data = json.dumps({
            "sales_orders": comparison["sales_orders"],
            "rows": [
                {
                    key: row.get(key)
                    for key in ("sales_order", "sales_order_item", "item_code", "item_name", "stock_uom", "order_qty")
                }
                for row in comparison["rows"]
                if not row.get("extra")
            ],
        }, ensure_ascii=False)


def validate_pick_list_before_submit(doc, method=None):
    validate_pick_list_result(doc, require_result=True)


def sync_delivery_contact_phone(doc, method=None):
    """Save a draft Delivery Note's store phone as the linked Contact's primary mobile."""
    if doc.get("docstatus") != 0:
        return

    customer = doc.get("customer")
    contact_name = doc.get("contact_person")
    phone = str(doc.get("custom_store_phone") or "").strip()
    if not customer or not contact_name or not phone:
        return

    contact = frappe.get_doc("Contact", contact_name)
    if not any(
        link.get("link_doctype") == "Customer" and link.get("link_name") == customer
        for link in (contact.get("links") or [])
    ):
        return

    target = next(
        (row for row in (contact.get("phone_nos") or [])
         if str(row.get("phone") or "").strip() == phone),
        None,
    )
    if target is None:
        target = contact.append("phone_nos", {"phone": phone})

    changed = str(target.get("phone") or "").strip() != phone or not target.get("is_primary_mobile_no")
    target.phone = phone
    target.is_primary_mobile_no = 1
    for row in contact.get("phone_nos") or []:
        if row is not target and row.get("is_primary_mobile_no"):
            row.is_primary_mobile_no = 0
            changed = True

    if changed:
        contact.save()


def validate_delivery_note(doc, method=None):
    """交货单验证"""
    validate_single_draft_source(doc)
    validate_transaction_quantities(doc)
    validate_delivery_route(doc)

    # Keep the selected store/order identifiers on the delivery snapshot when
    # a note is created from a Sales Order; standard address/contact fields are
    # still the source of the full address and contact details.
    order_names = {row.get("against_sales_order") for row in (doc.get("items") or []) if row.get("against_sales_order")}
    order_name = next(iter(order_names)) if len(order_names) == 1 else None
    if doc.get("docstatus") == 0 and order_name and not doc.get("custom_wholesale_snapshot"):
        for fieldname in ("custom_store_name", "custom_store_phone", "custom_customer_order_no", "custom_invoice_plan"):
            if not doc.get(fieldname) and frappe.get_meta("Delivery Note").has_field(fieldname):
                value = frappe.db.get_value("Sales Order", order_name, fieldname)
                if value:
                    setattr(doc, fieldname, value)

    # 只在筛选结果唯一时补齐默认运输资料；多条结果交给用户选择。
    if doc.get("docstatus") == 0:
        if not doc.get("custom_store_phone"):
            phone = doc.get("contact_mobile") or doc.get("contact_phone")
            if not phone:
                address_name = doc.get("shipping_address_name") or doc.get("customer_address")
                if address_name:
                    phone = frappe.db.get_value("Address", address_name, "phone")
            if phone:
                doc.custom_store_phone = phone

        if not doc.get("vehicle_no") and doc.get("company"):
            vehicles = frappe.get_all("Vehicle", filters={"company": doc.company}, fields=["name"], limit_page_length=2)
            if len(vehicles) == 1:
                doc.vehicle_no = vehicles[0].get("name")

        if not doc.get("driver"):
            driver_filters = {"status": "Active"}
            if doc.get("transporter"):
                driver_filters["transporter"] = doc.transporter
            drivers = frappe.get_all("Driver", filters=driver_filters, fields=["name"], limit_page_length=2)
            if len(drivers) == 1:
                doc.driver = drivers[0].get("name")

        if doc.get("driver"):
            driver = frappe.db.get_value("Driver", doc.driver, ["full_name", "cell_number"], as_dict=True) or {}
            if not doc.get("driver_name") and driver.get("full_name"):
                doc.driver_name = driver.full_name
            if not doc.get("custom_driver_phone") and driver.get("cell_number"):
                doc.custom_driver_phone = driver.cell_number

    # 原生地址选择器会自动带出唯一默认地址；多个门店时，用户先选地址。
    # 用已选地址记录名补齐门店名称，保留用户已经手工填写的值。
    if (not doc.get("custom_store_name") and doc.get("customer") and
            frappe.get_meta("Delivery Note").has_field("custom_store_name")):
        address_name = doc.get("shipping_address_name") or doc.get("customer_address")
        if address_name and frappe.db.exists("Dynamic Link", {
            "parenttype": "Address", "parent": address_name,
            "link_doctype": "Customer", "link_name": doc.get("customer"),
        }):
            doc.custom_store_name = address_name

    # 订单漏填门店/开票安排时，以送货单已填值回填订单（只补空，不覆盖）。
    # 否则下次开单还会因为「订单门店为空」再次报不一致。
    if order_name and frappe.get_meta("Sales Order").has_field("custom_store_name"):
        filled = {
            fieldname: doc.get(fieldname)
            for fieldname in ("custom_store_name", "custom_store_phone",
                              "custom_customer_order_no", "custom_invoice_plan")
            if doc.get(fieldname) and not frappe.db.get_value("Sales Order", order_name, fieldname)
        }
        if filled:
            frappe.db.set_value("Sales Order", order_name, filled)

    # Native stock-ledger validation handles UOM, serial/batch and warehouse
    # quantities atomically on submit. Do not compare sales UOM against Bin or
    # recheck already deducted stock on a submitted print-option Update.


def get_delivery_snapshot_quantities(doc, lock=False, strict=True):
    """Resolve order quantities without writing the document.

    ``strict`` is used by save/submit validation; printing uses ``False`` so
    old documents can be rendered read-only without inventing zero values.
    """
    if doc.get("is_return"):
        return []
    prior = {}
    resolved = []
    rows_value = doc.get("items") if hasattr(doc, "get") else None
    rows_value = rows_value or getattr(doc, "items", None) or []
    rows = list(enumerate(rows_value))
    for index, item in sorted(rows, key=lambda pair: pair[1].get("so_detail") or ""):
        detail = item.get("so_detail")
        order_name = item.get("against_sales_order")
        if not detail and not order_name:
            continue
        if not detail or not order_name:
            message = "送货行缺少销售订单行关联，订购/此前已交付无法可靠恢复"
            if strict:
                frappe.throw(_(message))
            resolved.append({"index": index, "error": message})
            continue
        suffix = " FOR UPDATE" if lock else ""
        order = frappe.db.sql(
            "SELECT parent, item_code, stock_qty FROM `tabSales Order Item` WHERE name=%s" + suffix,
            (detail,), as_dict=True,
        )
        if not order or order[0].parent != order_name or order[0].item_code != item.item_code:
            message = "送货行与销售订单行不匹配，订购/此前已交付无法可靠恢复"
            if strict:
                frappe.throw(_(message))
            resolved.append({"index": index, "error": message})
            continue
        factor = flt(item.get("conversion_factor") if item.get("conversion_factor") is not None else 1)
        if factor <= 0:
            message = "单位换算系数必须大于0，订购/此前已交付无法可靠恢复"
            if strict:
                frappe.throw(_(message))
            resolved.append({"index": index, "error": message})
            continue
        if detail not in prior:
            prior[detail] = flt(frappe.db.sql(
                """SELECT COALESCE(SUM(i.stock_qty),0) FROM `tabDelivery Note Item` i
                JOIN `tabDelivery Note` d ON d.name=i.parent
                WHERE d.docstatus=1 AND d.name<>%s AND i.so_detail=%s AND i.against_sales_order=%s""",
                (doc.name, detail, order_name),
            )[0][0])
        delivered = flt(item.qty) * factor
        if prior[detail] + delivered > flt(order[0].stock_qty) + 0.000001:
            message = "本次送货超过销售订单剩余数量：{0}".format(item.item_code)
            if strict:
                frappe.throw(_(message))
            resolved.append({"index": index, "error": message})
            continue
        resolved.append({
            "index": index,
            "ordered_qty": flt(order[0].stock_qty) / factor,
            "delivered_before_qty": prior[detail] / factor,
            "remaining_qty": max(flt(order[0].stock_qty) - prior[detail] - delivered, 0) / factor,
        })
        prior[detail] += delivered
    return resolved


def prepare_delivery_snapshot(doc, method=None):
    """Populate the per-order quantities before draft save and submit."""
    if doc.get("is_return") or doc.get("docstatus") in (1, 2):
        return
    for result in get_delivery_snapshot_quantities(doc, lock=True, strict=True):
        if "error" in result:
            continue
        item = doc.items[result["index"]]
        item.custom_ordered_qty = result["ordered_qty"]
        item.custom_delivered_before_qty = result["delivered_before_qty"]
        item.custom_remaining_qty = result["remaining_qty"]


def auto_create_item_price(doc, method=None):
    """Mirror quick-entry cost/selling rates into the configured price lists."""
    wholesale_rate = flt(doc.get("standard_rate"))
    if not wholesale_rate and doc.get("variant_of"):
        wholesale_rate = flt(frappe.db.get_value("Item", doc.variant_of, "standard_rate"))

    prices = [("Standard Buying", flt(doc.get("valuation_rate")))]
    prices.append(("Wholesale Selling", wholesale_rate))
    for price_list, rate in prices:
        if rate <= 0 or frappe.db.get_value(
            "Item Price", {"item_code": doc.name, "price_list": price_list}, "name"
        ):
            continue
        currency = (
            frappe.db.get_value("Price List", price_list, "currency")
            or frappe.defaults.get_user_default("currency")
            or "MZN"
        )
        try:
            frappe.get_doc({
                "doctype": "Item Price",
                "item_code": doc.name,
                "price_list": price_list,
                "price_list_rate": rate,
                "currency": currency,
            }).insert(ignore_permissions=True)
        except Exception as e:
            frappe.log_error(f"Item Price 自动创建失败 [{doc.name} / {price_list}]: {e}", "solua_home.auto_price")
