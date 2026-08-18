"""促销管理 API for solua_home

利用 ERPNext Pricing Rule 实现零售促销：
- 创建/查询/停用促销规则
- 促销模板（特价/折扣/买赠/满减）
- POS 促销识别
"""
import frappe
from frappe import _
import json
from datetime import date, datetime


# ─── 促销模板 ─────────────────────────────────────────────────────

PROMOTION_TEMPLATES = {
    "item_discount": {
        "name": "单品特价",
        "description": "指定商品固定折扣（如：CR-001 打 8 折）",
        "apply_on": "Item Code",
        "rate_or_discount": "Discount Percentage",
        "price_or_product_discount": "Price",
        "selling": 1,
    },
    "category_discount": {
        "name": "分类折扣",
        "description": "指定商品分类统一折扣（如：窗帘全场 9 折）",
        "apply_on": "Item Group",
        "rate_or_discount": "Discount Percentage",
        "price_or_product_discount": "Price",
        "selling": 1,
    },
    "fixed_price": {
        "name": "固定售价",
        "description": "指定商品固定价格（如：CR-001-BR 特价 800）",
        "apply_on": "Item Code",
        "rate_or_discount": "Rate",
        "price_or_product_discount": "Price",
        "selling": 1,
    },
    "buy_get_free": {
        "name": "买赠",
        "description": "买 N 件送同款/指定商品（如：买 3 送 1）",
        "apply_on": "Item Code",
        "rate_or_discount": "Discount Percentage",
        "price_or_product_discount": "Product Discount",
        "same_item": 1,
        "selling": 1,
    },
    "qty_discount": {
        "name": "量大从优",
        "description": "买满 N 件打折（如：买 5 件以上打 85 折）",
        "apply_on": "Item Code",
        "rate_or_discount": "Discount Percentage",
        "price_or_product_discount": "Price",
        "selling": 1,
    },
    "member_discount": {
        "name": "会员专享价",
        "description": "会员客户专属折扣（如：会员全场 95 折）",
        "apply_on": "Transaction",
        "rate_or_discount": "Discount Percentage",
        "price_or_product_discount": "Price",
        "selling": 1,
    },
}


@frappe.whitelist()
def get_promotion_templates():
    """获取促销模板列表"""
    result = []
    for key, tpl in PROMOTION_TEMPLATES.items():
        result.append({
            "key": key,
            "name": tpl["name"],
            "description": tpl["description"],
        })
    return result


@frappe.whitelist()
def create_promotion(template_key, config=None):
    """基于模板创建促销规则

    Args:
        template_key: 模板 key（item_discount / category_discount / fixed_price / buy_get_free / qty_discount / member_discount）
        config: JSON 对象，覆盖模板参数

    Returns:
        dict: 创建结果
    """
    if isinstance(config, str):
        config = json.loads(config)

    tpl = PROMOTION_TEMPLATES.get(template_key)
    if not tpl:
        frappe.throw(_("无效的促销模板：{0}").format(template_key))

    config = config or {}
    company = config.get("company", "Solua Home, Lda")

    # 构建 Pricing Rule 文档
    rule_data = {
        "doctype": "Pricing Rule",
        "title": config.get("title", tpl["name"]),
        "apply_on": tpl["apply_on"],
        "rate_or_discount": tpl["rate_or_discount"],
        "price_or_product_discount": tpl["price_or_product_discount"],
        "selling": tpl.get("selling", 0),
        "buying": tpl.get("buying", 0),
        "company": company,
        "disable": 0,
    }

    # 买赠特殊设置
    if tpl.get("same_item"):
        rule_data["same_item"] = 1
    if tpl.get("free_item"):
        rule_data["free_item"] = config.get("free_item", "")
        rule_data["free_qty"] = config.get("free_qty", 1)

    # 用户配置覆盖
    if config.get("discount_percentage") is not None:
        rule_data["discount_percentage"] = float(config["discount_percentage"])
    if config.get("discount_amount") is not None:
        rule_data["discount_amount"] = float(config["discount_amount"])
    if config.get("rate") is not None:
        rule_data["rate"] = float(config["rate"])

    # 数量限制
    if config.get("min_qty"):
        rule_data["min_qty"] = float(config["min_qty"])
    if config.get("max_qty"):
        rule_data["max_qty"] = float(config["max_qty"])

    # 有效期
    if config.get("valid_from"):
        rule_data["valid_from"] = config["valid_from"]
    else:
        rule_data["valid_from"] = str(date.today())

    if config.get("valid_upto"):
        rule_data["valid_upto"] = config["valid_upto"]

    # 优先级
    if config.get("priority"):
        rule_data["priority"] = config["priority"]

    # 适用价格表
    rule_data["for_price_list"] = config.get("for_price_list", "Standard Selling")

    # 应用范围（子表）
    if config.get("items"):
        for item in config["items"]:
            rule_data.setdefault("items", []).append({
                "item_code": item,
            })

    if config.get("item_groups"):
        for ig in config["item_groups"]:
            rule_data.setdefault("item_groups", []).append({
                "item_group": ig,
            })

    # 创建
    doc = frappe.get_doc(rule_data)
    doc.insert(ignore_permissions=True)
    frappe.db.commit()

    return {
        "name": doc.name,
        "title": doc.title,
        "message": f"促销规则创建成功：{doc.name}",
    }


@frappe.whitelist()
def list_promotions(show_disabled=0, limit=50):
    """查询促销规则列表

    Args:
        show_disabled: 是否显示已停用的
        limit: 最大返回数
    """
    filters = {}
    if not show_disabled:
        filters["disable"] = 0

    rules = frappe.get_all("Pricing Rule",
        filters=filters,
        fields=["name", "title", "apply_on", "rate_or_discount",
                "discount_percentage", "discount_amount", "rate",
                "selling", "buying", "valid_from", "valid_upto",
                "disable", "min_qty", "max_qty", "price_or_product_discount",
                "same_item", "free_item", "free_qty", "creation"],
        order_by="creation desc",
        limit=int(limit),
    )

    today = date.today()
    result = []
    for r in rules:
        # 判断是否在有效期内
        is_active = not r.disable
        if r.valid_from and r.valid_from > today:
            is_active = False
        if r.valid_upto and r.valid_upto < today:
            is_active = False

        # 获取应用范围
        scope = ""
        if r.apply_on == "Item Code":
            items = frappe.get_all("Pricing Rule Item Code",
                filters={"parent": r.name}, fields=["item_code"])
            scope = ", ".join(i.item_code for i in items[:5])
            if len(items) > 5:
                scope += f" 等{len(items)}种"
        elif r.apply_on == "Item Group":
            groups = frappe.get_all("Pricing Rule Item Group",
                filters={"parent": r.name}, fields=["item_group"])
            scope = ", ".join(g.item_group for g in groups[:5])

        # 描述
        if r.rate_or_discount == "Rate" and r.rate:
            desc = f"固定价 {r.rate}"
        elif r.rate_or_discount == "Discount Percentage" and r.discount_percentage:
            desc = f"{r.discount_percentage}% off"
        elif r.rate_or_discount == "Discount Amount" and r.discount_amount:
            desc = f"减 {r.discount_amount}"
        else:
            desc = ""

        if r.price_or_product_discount == "Product Discount":
            desc = f"买赠 {r.free_item or '同款'}×{r.free_qty or 1}"

        result.append({
            "name": r.name,
            "title": r.title or r.name,
            "apply_on": r.apply_on,
            "scope": scope,
            "description": desc,
            "is_active": is_active,
            "valid_from": str(r.valid_from) if r.valid_from else "",
            "valid_upto": str(r.valid_upto) if r.valid_upto else "",
            "min_qty": r.min_qty or 0,
            "max_qty": r.max_qty or 0,
            "disable": r.disable,
        })

    return result


@frappe.whitelist()
def disable_promotion(pricing_rule_name):
    """停用促销规则"""
    doc = frappe.get_doc("Pricing Rule", pricing_rule_name)
    doc.disable = 1
    doc.save(ignore_permissions=True)
    frappe.db.commit()
    return {"status": "disabled", "name": doc.name}


@frappe.whitelist()
def enable_promotion(pricing_rule_name):
    """启用促销规则"""
    doc = frappe.get_doc("Pricing Rule", pricing_rule_name)
    doc.disable = 0
    doc.save(ignore_permissions=True)
    frappe.db.commit()
    return {"status": "enabled", "name": doc.name}


@frappe.whitelist()
def get_active_promotions_for_pos():
    """查询当前 POS 生效中的促销规则

    POS 收银时自动应用 Pricing Rule，此接口用于：
    - POS 页面显示当前促销信息
    - 让收银员知道哪些商品正在促销
    """
    today = date.today()

    rules = frappe.get_all("Pricing Rule",
        filters={
            "disable": 0,
            "selling": 1,
            "valid_from": ["<=", today],
        },
        fields=["name", "title", "apply_on", "rate_or_discount",
                "discount_percentage", "discount_amount", "rate",
                "min_qty", "max_qty", "valid_upto",
                "price_or_product_discount", "same_item",
                "free_item", "free_qty"],
        order_by="priority desc, creation desc",
    )

    # 过滤已过期的
    active = []
    for r in rules:
        if r.valid_upto and r.valid_upto < today:
            continue

        # 获取应用范围
        items = []
        if r.apply_on == "Item Code":
            items = [i.item_code for i in frappe.get_all("Pricing Rule Item Code",
                filters={"parent": r.name}, fields=["item_code"])]
        elif r.apply_on == "Item Group":
            items = [g.item_group for g in frappe.get_all("Pricing Rule Item Group",
                filters={"parent": r.name}, fields=["item_group"])]

        active.append({
            "name": r.name,
            "title": r.title or r.name,
            "apply_on": r.apply_on,
            "items": items,
            "discount": f"{r.discount_percentage}%" if r.discount_percentage else
                        f"¥{r.discount_amount}" if r.discount_amount else
                        f"¥{r.rate}" if r.rate else "",
            "min_qty": r.min_qty or 0,
            "is_product_discount": r.price_or_product_discount == "Product Discount",
            "free_item": r.free_item or "",
            "free_qty": r.free_qty or 0,
        })

    return active
