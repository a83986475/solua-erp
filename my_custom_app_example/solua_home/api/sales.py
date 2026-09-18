# solua_home/api/sales.py
# ============================
# 销售模块的自定义验证和事件处理
# ============================

import frappe
from frappe import _
from frappe.utils import cint, flt

from solua_home.api.stock import validate_transaction_quantities

# 折扣审批改为「密码审批」（2026-08-08）：
# 任何折扣（幅度 > 公司配置阈值，默认 0 = 任何折扣）都需在发票「审批密码」字段
# 输入公司配置的审批密码后才能提交。密码存于 设置→公司→Solua Home, Lda，
# 字段加密存储，界面上不可见；收银员没有自由打折权。


def before_validate_sales_invoice(doc, method=None):
    """销售发票保存前执行：行折扣保险

    ERPNext v16.28 的 calculate_item_rate 以 rate 优先：
    若行 rate（单价）不等于按 discount_percentage 算出的折后价，会清除行折扣。
    POS 里收银员输入折扣 % 时 rate 仍是原价 → 折扣被清。
    这里在保存前把仍为原价的 rate 同步为折后价，让折扣正确保留。
    """
    for item in doc.get("items", []):
        dp = flt(item.get("discount_percentage"))
        if dp <= 0 or item.get("is_free_item"):
            continue
        price_list_rate = flt(item.get("price_list_rate"))
        rate = flt(item.get("rate"))
        if price_list_rate and rate and abs(rate - price_list_rate) < 0.01:
            # rate 仍是原价 → 同步为折后价（保留四位小数精度）
            item.rate = flt(price_list_rate * (1 - dp / 100.0), item.precision("rate"))


def get_max_discount_percentage(doc):
    """计算单据上的最大折扣比例（整单 + 行折扣取最大值，%）"""
    pct = 0.0
    # 整单折扣（百分比形式）
    if doc.get("additional_discount_percentage"):
        pct = max(pct, flt(doc.get("additional_discount_percentage")))
    # 整单折扣（金额形式，按净额折算）
    if doc.get("discount_amount") and doc.get("net_total"):
        pct = max(pct, flt(doc.discount_amount) / flt(doc.net_total) * 100)
    # 行折扣
    for item in doc.get("items", []):
        if item.get("discount_percentage"):
            pct = max(pct, flt(item.get("discount_percentage")))
        if item.get("discount_amount") and item.get("amount"):
            pct = max(pct, flt(item.discount_amount) / flt(item.amount) * 100)
    return pct


def _try_decrypt(value):
    """尝试解密密码字段值：已加密则解密出明文，已是明文则原样返回

    注意：Frappe 的 decrypt() 对非 Fernet 密文（如明文密码）会先执行
    frappe.throw（内部 msgprint 写入 message_log）再抛异常——即使这里
    try/except 接住，"加密密钥无效"等消息仍会随响应返回并在前端弹出误导性
    警告。因此**只对 Fernet 密文（固定以 gAAAA 开头）调用 decrypt**，
    其余值直接原样返回。
    """
    if not value:
        return ""
    if not str(value).startswith("gAAAA"):
        return value
    try:
        from frappe.utils.password import decrypt

        return decrypt(value)
    except Exception:
        return value


def _get_discount_approval_settings(doc):
    """读取公司折扣审批配置，返回 (总开关, 阈值%, 审批密码明文)"""
    company = doc.get("company")
    enabled = cint(frappe.db.get_value("Company", company, "custom_enable_discount_approval") or 0)
    threshold = flt(frappe.db.get_value("Company", company, "custom_discount_approval_threshold") or 0)
    pwd_hash = frappe.db.get_value("Company", company, "custom_discount_approval_password") or ""
    return enabled, threshold, _try_decrypt(pwd_hash)


def validate_sales_invoice(doc, method=None):
    """销售发票保存时验证"""
    validate_transaction_quantities(doc)

    # 示例1：大额审批控制
    if doc.grand_total > 100000:
        frappe.throw(_("金额超过 100,000，需要额外审批"))

    # 示例2：检查客户信用额度
    customer_credit_limit = frappe.db.get_value(
        "Customer", doc.customer, "custom_credit_limit"
    )
    if customer_credit_limit and doc.outstanding_amount > customer_credit_limit:
        frappe.throw(
            _("客户 {0} 的信用额度为 {1}，当前欠款 {2} 已超限").format(
                doc.customer, customer_credit_limit, doc.outstanding_amount
            )
        )

    # 折扣审批门（密码审批）：折扣幅度 > 阈值（默认0=任何折扣）需输入审批密码
    max_pct = get_max_discount_percentage(doc)
    enabled, threshold, approval_pwd = _get_discount_approval_settings(doc)
    if (
        enabled
        and approval_pwd
        and max_pct > threshold
        and not cint(doc.get("custom_discount_approved"))
    ):
        entered = _try_decrypt(doc.get("custom_approval_password") or "")
        if entered == approval_pwd:
            # 密码正确 → 置审批标记并清空密码字段（标记随单据持久化）
            doc.custom_discount_approved = 1
            doc.custom_approval_password = ""
        elif entered:
            frappe.throw(_("审批密码错误，请重新输入正确的审批密码"))
        elif doc.get("_action") == "submit":
            frappe.throw(
                _("折扣 {0}% 未经审批：需管理员在「审批密码」字段输入审批密码后保存，再重新提交").format(
                    max_pct
                )
            )
        elif doc.get("is_pos"):
            # POS 草稿保存静默——提交时由前端弹审批密码对话框处理
            pass
        else:
            # 桌面表单草稿保存：仅提示不拦截
            frappe.msgprint(
                _("折扣 {0}% 未经审批：提交前需管理员输入审批密码").format(max_pct)
            )

    # ── 成本价校验：任何行的实际售价不得低于成本价（硬拦截，管理员也不例外） ──
    for item in doc.get("items", []):
        selling_price = flt(item.get("rate")) or 0
        if selling_price <= 0:
            continue
        # 获取成本价
        cost = frappe.db.sql("""
            SELECT SUM(b.valuation_rate * b.actual_qty) / NULLIF(SUM(b.actual_qty), 0) as cost
            FROM tabBin b WHERE b.item_code = %(code)s AND b.actual_qty > 0
        """, {"code": item.item_code}, as_dict=True)
        cost_val = 0
        if cost and cost[0].get("cost"):
            cost_val = float(cost[0]["cost"])
        else:
            cost_val = float(frappe.db.get_value("Item", item.item_code, "valuation_rate") or 0)

        if cost_val > 0 and selling_price < cost_val:
            item_name = item.item_name or item.item_code
            frappe.throw(
                _("物料 {0} 售价 {1} 低于成本价 {2}，不允许销售！（硬性限制，管理员也不例外）").format(
                    item_name, selling_price, cost_val
                )
            )


@frappe.whitelist()
def verify_discount_approval_password(password, company=None):
    """POS 审批对话框用：校验审批密码是否正确（不修改任何数据）

    返回 {"ok": True/False}；审批未启用或密码为空时视为通过（由提交时后端门再次把关）。
    """
    if not company:
        company = frappe.defaults.get_user_default("company")
    enabled, threshold, approval_pwd = _get_discount_approval_settings(
        frappe._dict({"company": company})
    )
    if not enabled or not approval_pwd:
        return {"ok": True}
    return {"ok": password == approval_pwd}

    # 示例3：检查自定义字段
    if doc.get("custom_approver") and not doc.get("custom_approval_date"):
        frappe.msgprint(_("请填写审批日期"))


def on_invoice_submitted(doc, method=None):
    """销售发票提交后执行"""
    frappe.msgprint(_("发票 {0} 已成功提交").format(doc.name))

    # 示例：提交后自动更新客户上次交易日期
    frappe.db.set_value(
        "Customer", doc.customer, "custom_last_transaction_date", frappe.utils.nowdate()
    )

    # 示例：调用外部 API
    # if doc.custom_sync_required:
    #     sync_to_external_system(doc)


def on_invoice_cancelled(doc, method=None):
    """销售发票取消时执行"""
    frappe.msgprint(_("发票 {0} 已取消").format(doc.name))


def validate_sales_order(doc, method=None):
    """销售订单保存时验证"""
    validate_transaction_quantities(doc)

    # 交货日期只需不早于销售单日期；不要求提前若干天。
    if doc.delivery_date and doc.transaction_date:
        from frappe.utils import getdate

        if getdate(doc.delivery_date) < getdate(doc.transaction_date):
            frappe.throw(_("交货日期不能早于销售单日期"))


def validate_quotation(doc, method=None):
    """报价单验证"""
    validate_transaction_quantities(doc)

    # 报价有效期不能超过30天（date_diff 返回整数，兼容字符串/日期）
    if doc.valid_till and doc.transaction_date:
        from frappe.utils import date_diff

        if date_diff(doc.valid_till, doc.transaction_date) > 30:
            frappe.throw(_("报价有效期不能超过30天"))


def validate_customer(doc, method=None):
    """客户保存时验证"""
    # 示例：统一客户名称格式（去掉前后空格、全角转半角）
    if doc.customer_name:
        doc.customer_name = doc.customer_name.strip()

    # 示例：检查重复客户
    if doc.is_new():
        existing = frappe.db.exists(
            "Customer",
            {"customer_name": doc.customer_name, "name": ["!=", doc.name]},
        )
        if existing:
            frappe.throw(_("客户名称 {0} 已存在").format(doc.customer_name))


def after_customer_created(doc, method=None):
    """客户创建后自动操作"""
    # Walkin 客户（散客）不创建联系人
    if doc.customer_name == "Walkin" or doc.name == "Walkin":
        return

    # 自动创建默认联系人（用正确的子表过滤语法）
    existing = frappe.get_all("Contact",
        filters=[
            ["Dynamic Link", "link_doctype", "=", "Customer"],
            ["Dynamic Link", "link_name", "=", doc.name],
        ],
        limit=1
    )
    if not existing:
        contact = frappe.get_doc({
            "doctype": "Contact",
            "first_name": doc.customer_name,
            "is_primary_contact": 1,
            "links": [{"link_doctype": "Customer", "link_name": doc.name}],
        })
        contact.insert(ignore_permissions=True)
        frappe.msgprint(_("已为客户 {0} 自动创建联系人").format(doc.customer_name))


# ─── 成本价校验 ─────────────────────────────────────────────────

@frappe.whitelist()
def check_price_above_cost(item_code, price):
    """校验价格是否高于成本价（改价/折扣通用）

    返回:
        {"ok": True, "cost": 0} — 价格高于或等于成本，允许
        {"ok": False, "cost": 100, "message": "..."} — 低于成本，拒绝
    """
    if not item_code or price is None:
        return {"ok": True, "cost": 0}

    price = float(price)

    # 获取成本价（valuation_rate）
    # 优先从 Bin 表取加权平均成本，其次从 Item 取
    cost = frappe.db.sql("""
        SELECT SUM(b.valuation_rate * b.actual_qty) / NULLIF(SUM(b.actual_qty), 0)
        FROM tabBin b
        WHERE b.item_code = %(item_code)s AND b.actual_qty > 0
    """, {"item_code": item_code}, as_dict=True)

    if cost and cost[0] and cost[0][list(cost[0].keys())[0]]:
        cost_val = float(cost[0][list(cost[0].keys())[0]])
    else:
        # Bin 无库存或无成本，从 Item.valuation_rate 取
        cost_val = frappe.db.get_value("Item", item_code, "valuation_rate") or 0
        cost_val = float(cost_val)

    if cost_val <= 0:
        # 未设成本价，不拦截（允许正常销售）
        return {"ok": True, "cost": 0}

    if price < cost_val:
        item_name = frappe.db.get_value("Item", item_code, "item_name") or item_code
        return {
            "ok": False,
            "cost": cost_val,
            "message": f"价格 {price:.2f} 低于成本价 {cost_val:.2f}（{item_name}），不允许！",
        }

    return {"ok": True, "cost": cost_val}
