# solua_home/api/stock.py
# ============================
# 库存模块的自定义验证和事件处理
# ============================

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
        existing = frappe.db.get_value(
            "Item",
            {"custom_order_code": doc.custom_order_code, "name": ["!=", doc.name]},
            "name",
        )
        if existing:
            frappe.throw(_("对外订货货号 {0} 已被物料 {1} 使用").format(doc.custom_order_code, existing))

    # 物料名称校验：只拦截危险字符（< > " '），放开常见字符（如 /、&、:、（））
    # 2026-08-15 用户要求放开：导入真实物料时名称常含 "/"（如 "140×200 / Algodão"），
    # 斜杠无实际危害，只影响打印/文件名观感，不应因此拦建档
    import re
    if doc.item_name and re.search(r'[<>"\']', doc.item_name):
        frappe.throw(_("物料名称不能包含特殊字符（< > \" \'）"))

    # 颜色变体共用模板原包装条码；模板自身的 Item Barcode 子表不复制到变体。
    attributes = doc.get("attributes") or []
    has_color_attribute = any(row.get("attribute") == "Cor" for row in attributes)
    if doc.variant_of and has_color_attribute:
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


def validate_delivery_note(doc, method=None):
    """交货单验证"""
    validate_transaction_quantities(doc)

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
    """Variant 创建时自动从模板生成 Item Price"""
    if not doc.variant_of:
        return  # 不是 Variant，跳过

    # 获取模板价格
    if not doc.standard_rate:
        # 如果 Variant 没有价格，尝试从模板继承
        template_rate = frappe.db.get_value("Item", doc.variant_of, "standard_rate")
        if not template_rate:
            return  # 模板也没有价格，跳过

    # 检查是否已有 Item Price
    existing = frappe.db.get_value("Item Price",
        {"item_code": doc.name, "price_list": "Standard Selling", "selling": 1},
        "name"
    )
    if existing:
        return  # 已存在，不重复创建

    # 获取默认货币
    currency = frappe.defaults.get_user_default("currency") or "MZN"

    # 创建 Item Price
    try:
        price_doc = frappe.get_doc({
            "doctype": "Item Price",
            "item_code": doc.name,
            "price_list": "Standard Selling",
            "price_list_rate": doc.standard_rate,
            "selling": 1,
            "currency": currency,
        })
        price_doc.insert(ignore_permissions=True)
    except Exception as e:
        frappe.log_error(f"Item Price 自动创建失败 [{doc.name}]: {e}", "solua_home.auto_price")
