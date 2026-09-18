"""会员系统 API for solua_home

利用 ERPNext 内置 Loyalty Program + Customer 扩展字段实现：
- 会员注册/查询
- 储值充值/消费
- 积分查询
- POS 会员识别
"""
import frappe
from frappe import _
import json
from datetime import date, datetime


# ─── 会员方案常量 ─────────────────────────────────────────────────

DEFAULT_LOYALTY_PROGRAM = "Solua Members"
DEFAULT_COLLECTION_FACTOR = 1  # 每消费 1 元 = 1 积分
DEFAULT_REDEMPTION_FACTOR = 100  # 100 积分 = 1 元折扣


def ensure_loyalty_program():
    """确保默认会员方案存在"""
    if frappe.db.exists("Loyalty Program", DEFAULT_LOYALTY_PROGRAM):
        return DEFAULT_LOYALTY_PROGRAM

    from datetime import date as _date
    doc = frappe.get_doc({
        "doctype": "Loyalty Program",
        "loyalty_program_name": DEFAULT_LOYALTY_PROGRAM,
        "from_date": _date.today(),
        "collection_factor": DEFAULT_COLLECTION_FACTOR,
        "conversion_factor": DEFAULT_REDEMPTION_FACTOR,
        "collection_rules": [{
            "collection_factor": DEFAULT_COLLECTION_FACTOR,
            "tier_name": "普通会员",
            "min_spent": 0,
        }],
    })

    doc.insert(ignore_permissions=True)
    frappe.db.commit()
    return DEFAULT_LOYALTY_PROGRAM


# ─── 会员注册 ─────────────────────────────────────────────────────


@frappe.whitelist()
def register_member(customer_name, phone=None, email=None, card_no=None, gender=None):
    """注册新会员

    创建 Customer 并关联 Loyalty Program，生成会员卡号。

    Args:
        customer_name: 会员姓名
        phone: 手机号
        email: 邮箱
        card_no: 自定义卡号（可选，不填则自动生成）
        gender: 性别

    Returns:
        dict: 会员信息
    """
    # 检查手机号是否已注册
    if phone:
        existing = frappe.db.get_value("Customer",
            {"mobile_no": phone, "disabled": 0}, "name")
        if existing:
            frappe.throw(_("手机号 {0} 已注册为会员：{1}").format(phone, existing))

    # 生成会员卡号
    if not card_no:
        count = frappe.db.count("Customer", {"disabled": 0}) or 0
        card_no = f"MBR-{date.today().strftime('%Y%m')}-{count + 1:04d}"

    # 确保会员方案存在
    loyalty_program = ensure_loyalty_program()

    # 创建 Customer
    customer = frappe.get_doc({
        "doctype": "Customer",
        "customer_name": customer_name,
        "customer_group": "Individual",
        "territory": "All Territories",
        "mobile_no": phone or "",
        "email_id": email or "",
        "gender": gender or "",
        "loyalty_program": loyalty_program,
        "custom_member_card_no": card_no,
        "custom_member_since": date.today(),
    })

    customer.insert(ignore_permissions=True)
    frappe.db.commit()

    return {
        "customer": customer.name,
        "card_no": card_no,
        "name": customer_name,
        "phone": phone,
        "loyalty_program": loyalty_program,
        "message": f"会员注册成功：{customer.name}",
    }


# ─── 会员查询 ─────────────────────────────────────────────────────


@frappe.whitelist()
def search_member(query):
    """按卡号/手机/名称搜索会员

    Returns:
        dict: 会员信息（含储值余额、积分）
    """
    if not query or not query.strip():
        return None

    q = query.strip()

    # 按卡号搜索
    customer = frappe.db.get_value("Customer",
        {"custom_member_card_no": q, "disabled": 0}, "name")

    # 按手机号搜索
    if not customer:
        customer = frappe.db.get_value("Customer",
            {"mobile_no": q, "disabled": 0}, "name")

    # 按名称模糊搜索
    if not customer:
        customers = frappe.get_all("Customer",
            filters={"customer_name": ["like", f"%{q}%"], "disabled": 0},
            fields=["name"], limit=5)
        if len(customers) == 1:
            customer = customers[0].name
        elif len(customers) > 1:
            # 返回多个候选
            return {"multiple": True, "candidates": [
                {"customer": c.name, "name": frappe.db.get_value("Customer", c.name, "customer_name")}
                for c in customers
            ]}

    if not customer:
        return None

    return _get_member_info(customer)


def _get_member_info(customer_name):
    """获取会员完整信息"""
    info = frappe.db.get_value("Customer", customer_name,
        ["customer_name", "mobile_no", "email_id", "gender",
         "loyalty_program", "loyalty_program_tier",
         "custom_member_card_no", "custom_stored_value",
         "custom_member_since", "custom_total_points"],
        as_dict=True)

    if not info:
        return None

    # 查实际积分余额（从 Loyalty Point Entry 汇总）
    points = frappe.db.sql("""
        SELECT COALESCE(SUM(loyalty_points), 0) as balance
        FROM `tabLoyalty Point Entry`
        WHERE customer = %(customer)s
          AND (expiry_date IS NULL OR expiry_date >= %(today)s)
    """, {"customer": customer_name, "today": date.today()}, as_dict=True)

    actual_points = int(points[0].balance) if points else 0

    # 查储值流水（最近 5 条）
    topups = frappe.get_all("Sales Invoice",
        filters={
            "customer": customer_name,
            "docstatus": 1,
            "custom_is_topup": 1,
        },
        fields=["name", "grand_total", "posting_date"],
        order_by="posting_date desc",
        limit=5,
    )

    return {
        "customer": customer_name,
        "name": info.customer_name,
        "phone": info.mobile_no or "",
        "email": info.email_id or "",
        "gender": info.gender or "",
        "card_no": info.custom_member_card_no or "",
        "loyalty_program": info.loyalty_program or "",
        "tier": info.loyalty_program_tier or "普通会员",
        "stored_value": float(info.custom_stored_value or 0),
        "points": actual_points,
        "member_since": str(info.custom_member_since or ""),
        "recent_topups": [
            {"invoice": t.name, "amount": float(t.grand_total or 0), "date": str(t.posting_date)}
            for t in topups
        ],
    }


# ─── 储值 ─────────────────────────────────────────────────────────


@frappe.whitelist()
def topup_stored_value(customer, amount, payment_method="Cash"):
    """储值充值

    创建一笔 Sales Invoice（is_pos=1, custom_is_topup=1）记录充值。
    """
    amount = float(amount)
    if amount <= 0:
        frappe.throw(_("充值金额必须大于 0"))

    # 创建充值单据
    invoice = frappe.get_doc({
        "doctype": "Sales Invoice",
        "customer": customer,
        "is_pos": 1,
        "pos_profile": _get_pos_profile(),
        "company": "Solua Home, Lda",
        "posting_date": date.today(),
        "custom_is_topup": 1,
        "items": [{
            "item_code": _get_topup_item(),
            "qty": 1,
            "rate": amount,
            "amount": amount,
        }],
        "payments": [{
            "mode_of_payment": payment_method,
            "amount": amount,
        }],
    })

    invoice.insert(ignore_permissions=True)
    invoice.submit()

    # 更新储值余额
    current = frappe.db.get_value("Customer", customer, "custom_stored_value") or 0
    new_balance = float(current) + amount
    frappe.db.set_value("Customer", customer, "custom_stored_value", new_balance)
    frappe.db.commit()

    return {
        "customer": customer,
        "amount": amount,
        "new_balance": new_balance,
        "invoice": invoice.name,
        "message": f"充值成功：{amount} → 余额 {new_balance}",
    }


@frappe.whitelist()
def deduct_stored_value(customer, amount):
    """储值扣减（POS 消费时调用）

    Returns:
        dict: 扣减结果
    """
    amount = float(amount)
    current = frappe.db.get_value("Customer", customer, "custom_stored_value") or 0

    if float(current) < amount:
        frappe.throw(_("储值余额不足：当前 {0}，需扣 {1}").format(current, amount))

    new_balance = float(current) - amount
    frappe.db.set_value("Customer", customer, "custom_stored_value", new_balance)
    frappe.db.commit()

    return {
        "customer": customer,
        "deducted": amount,
        "new_balance": new_balance,
    }


# ─── POS 会员识别 ─────────────────────────────────────────────────


@frappe.whitelist()
def recognize_member_in_pos(query):
    """POS 内识别会员（扫码/输号/输手机）

    Returns:
        dict: 会员信息 + 可用支付方式
    """
    info = search_member(query)
    if not info:
        return {"found": False, "message": "未找到会员"}

    if isinstance(info, dict) and info.get("multiple"):
        return {"found": False, "multiple": True, "candidates": info["candidates"]}

    # 检查储值余额
    stored_value = float(info.get("stored_value", 0))

    return {
        "found": True,
        "customer": info["customer"],
        "name": info["name"],
        "card_no": info["card_no"],
        "tier": info["tier"],
        "points": info["points"],
        "stored_value": stored_value,
        "can_use_stored_value": stored_value > 0,
        "loyalty_program": info["loyalty_program"],
    }


# ─── 积分 ─────────────────────────────────────────────────────────


@frappe.whitelist()
def get_member_points(customer):
    """查询会员积分详情"""
    # 总积分
    total = frappe.db.sql("""
        SELECT COALESCE(SUM(loyalty_points), 0) as total
        FROM `tabLoyalty Point Entry`
        WHERE customer = %(customer)s
    """, {"customer": customer}, as_dict=True)

    # 可用积分（未过期）
    available = frappe.db.sql("""
        SELECT COALESCE(SUM(loyalty_points), 0) as available
        FROM `tabLoyalty Point Entry`
        WHERE customer = %(customer)s
          AND (expiry_date IS NULL OR expiry_date >= %(today)s)
    """, {"customer": customer, "today": date.today()}, as_dict=True)

    # 积分明细
    entries = frappe.get_all("Loyalty Point Entry",
        filters={"customer": customer},
        fields=["name", "loyalty_points", "posting_date", "expiry_date",
                "invoice_type", "invoice", "redeemed"],
        order_by="posting_date desc",
        limit=20,
    )

    return {
        "customer": customer,
        "total_earned": int(total[0].total) if total else 0,
        "available": int(available[0].available) if available else 0,
        "entries": [
            {
                "date": str(e.posting_date),
                "points": int(e.loyalty_points),
                "redeemed": bool(e.redeemed),
                "invoice": e.invoice,
                "expires": str(e.expiry_date) if e.expiry_date else "",
            }
            for e in entries
        ],
    }


# ─── 辅助函数 ─────────────────────────────────────────────────────


def _get_pos_profile():
    """获取默认 POS Profile"""
    return frappe.db.get_value("POS Profile",
        {"company": "Solua Home, Lda"}, "name")


def _get_topup_item():
    """获取储值充值专用物料（不存在则创建）"""
    item_code = "TOPUP-001"
    if not frappe.db.exists("Item", item_code):
        doc = frappe.get_doc({
            "doctype": "Item",
            "item_code": item_code,
            "item_name": "会员储值充值",
            "item_group": "All Item Groups",
            "stock_uom": "Nos",
            "is_stock_item": 0,
            "description": "会员储值充值（虚拟物料，不涉及库存）",
            "custom_chinese_name": "会员储值充值",
        })
        doc.insert(ignore_permissions=True)

        # 设置售价
        frappe.get_doc({
            "doctype": "Item Price",
            "item_code": item_code,
            "price_list": "Standard Selling",
            "price_list_rate": 0,
        }).insert(ignore_permissions=True)

        frappe.db.commit()

    return item_code
