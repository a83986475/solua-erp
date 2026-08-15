# solua_home/api/stock.py
# ============================
# 库存模块的自定义验证和事件处理
# ============================

import random

import frappe
from frappe import _


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
    2. 无条码自动生成：非变体物料没有条码时，自动生成合法 EAN-13。
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

    # 2. 无条码自动生成（非变体；变体走标签条码=变体编码逻辑）
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
    # 物料编码规则校验：至少 3 位
    if doc.item_code and len(doc.item_code) < 3:
        frappe.throw(_("物料编码长度不能少于3位"))

    # 物料名称校验：只拦截危险字符（< > " '），放开常见字符（如 /、&、:、（））
    # 2026-08-15 用户要求放开：导入真实物料时名称常含 "/"（如 "140×200 / Algodão"），
    # 斜杠无实际危害，只影响打印/文件名观感，不应因此拦建档
    import re
    if doc.item_name and re.search(r'[<>"\']', doc.item_name):
        frappe.throw(_("物料名称不能包含特殊字符（< > \" \'）"))

    # 标签条码自动填充（Print Designer 用）
    if doc.variant_of:
        # 变体：优先自己的条码；无则用变体编码（标签打印 Code 128，扫码直接区分颜色）
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
    # 示例：出库前检查库存是否充足
    for item in doc.items:
        actual_qty = frappe.db.get_value(
            "Bin",
            {"item_code": item.item_code, "warehouse": item.warehouse},
            "actual_qty",
        )
        if actual_qty is not None and item.qty > actual_qty:
            frappe.throw(
                _("物料 {0} 在仓库 {1} 的库存不足（需求: {2}, 可用: {3}）").format(
                    item.item_code, item.warehouse, item.qty, actual_qty
                )
            )


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
