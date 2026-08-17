# -*- coding: utf-8 -*-
# solua_home/api/item_data.py
# ============================================
# 物料资料补全向导 + 档案完整性校验
#   - get_item_data:        加载物料资料（模板+变体 / 物料组 / 搜索）
#   - bulk_update_item_data:批量更新中文名/SPU/POS简称/规格摘要/最低库存
#   - validate_item_master: 全量校验物料档案完整性
# ============================================

import frappe
from frappe import _

# 向导可编辑的自定义字段
EDITABLE_FIELDS = [
    "custom_chinese_name",   # 中文显示名
    "custom_spu_code",       # SPU编码
    "custom_spec_summary",   # 规格摘要（可选）
    "custom_pos_short_name", # POS收银简称
    "custom_min_stock_level",# 最低库存
]

COLOR_ATTR_NAMES = ["Cor", "Color", "Colour"]


# ---------------------------------------------------------------------------
# 加载物料资料
# ---------------------------------------------------------------------------

@frappe.whitelist()
def get_item_data(template_item=None, item_group=None, search=None):
    """加载物料资料列表

    Args:
        template_item: 模板物料（has_variants=1）→ 返回模板 + 全部变体
        item_group:    物料组名（与 template_item 二选一）
        search:        编码/名称模糊搜索（附加过滤）

    Returns:
        list: [{name, item_name, item_group, variant_of, has_variants,
                custom_chinese_name, custom_spu_code, custom_spec_summary,
                custom_pos_short_name, custom_min_stock_level,
                color, template_zh, template_spu, status:{missing, warnings}}]
    """
    codes = None
    if template_item:
        if not frappe.db.exists("Item", template_item):
            frappe.throw(_("物料 {0} 不存在").format(template_item))
        variants = frappe.get_all(
            "Item", filters={"variant_of": template_item, "disabled": 0},
            fields=["name"], order_by="name asc",
        )
        codes = [template_item] + [v.name for v in variants]

    filters = {}
    if codes:
        filters["name"] = ["in", codes]
    if item_group:
        filters["item_group"] = item_group
    if search:
        filters["name"] = ["like", f"%{search}%"]

    items = frappe.get_all(
        "Item", filters=filters,
        fields=["name", "item_name", "item_group", "variant_of", "has_variants",
                "disabled"] + EDITABLE_FIELDS,
        order_by="name asc",
    )

    result = []
    for it in items:
        row = dict(it)
        row["color"] = _variant_color(it.name) if it.variant_of else None
        if it.variant_of:
            tpl = frappe.db.get_value(
                "Item", it.variant_of,
                ["custom_chinese_name", "custom_spu_code"], as_dict=True,
            )
            row["template_zh"] = (tpl or {}).get("custom_chinese_name")
            row["template_spu"] = (tpl or {}).get("custom_spu_code")
        row["status"] = _item_status(row)
        result.append(row)

    return result


# ---------------------------------------------------------------------------
# 批量更新
# ---------------------------------------------------------------------------

@frappe.whitelist()
def bulk_update_item_data(updates):
    """批量更新物料资料字段

    Args:
        updates: JSON 数组，每项：
            {item_code, chinese_name?, spu_code?, spec_summary?,
             pos_short_name?, min_stock?}
            （值为 null 或空字符串 = 不改该字段；数字 0 会被写入）

    Returns:
        {updated: [item_code], errors: [{item_code, error}]}
    """
    if isinstance(updates, str):
        updates = frappe.parse_json(updates)
    if not updates:
        frappe.throw(_("没有要保存的数据"))

    result = {"updated": [], "errors": []}

    for u in updates:
        item_code = u.get("item_code")
        if not item_code or not frappe.db.exists("Item", item_code):
            result["errors"].append({"item_code": item_code, "error": "物料不存在"})
            continue
        try:
            doc = frappe.get_doc("Item", item_code)
            mapping = {
                "custom_chinese_name": u.get("chinese_name"),
                "custom_spu_code": u.get("spu_code"),
                "custom_spec_summary": u.get("spec_summary"),
                "custom_pos_short_name": u.get("pos_short_name"),
                "custom_min_stock_level": u.get("min_stock"),
            }
            changed = False
            for field, val in mapping.items():
                # None 或空串 = 不改；0 是合法值必须写入
                if val is None or val == "":
                    continue
                if doc.get(field) != val:
                    doc.set(field, val)
                    changed = True
            if changed:
                doc.save(ignore_permissions=True)
            result["updated"].append(item_code)
        except Exception as e:
            frappe.db.rollback()
            frappe.log_error(f"物料资料更新失败 [{item_code}]: {e}", "solua_home.item_data")
            result["errors"].append({"item_code": item_code, "error": str(e)[:200]})

    frappe.db.commit()
    return result


# ---------------------------------------------------------------------------
# 完整性校验（全量）
# ---------------------------------------------------------------------------

@frappe.whitelist()
def validate_item_master():
    """校验全部未停用物料的档案完整性

    必填（missing）：中文名、SPU编码、条码、默认仓库、售价；
    变体额外必填：POS简称。
    警告（warnings）：规格摘要、最低库存、成本价。

    Returns:
        {total, complete, incomplete,
         field_summary: {字段名: {missing, total}},
         issues: {item_code: {name, missing, warnings}}}
    """
    items = frappe.get_all(
        "Item", filters={"disabled": 0},
        fields=["name", "item_name", "variant_of", "has_variants",
                "valuation_rate", "custom_label_barcode"] + EDITABLE_FIELDS,
        order_by="name asc",
    )
    codes = [i.name for i in items]

    # 批量取子表/关联数据
    barcode_parents = {d.parent for d in frappe.get_all(
        "Item Barcode", filters={"parent": ["in", codes]}, fields=["parent"])}
    has_barcode = barcode_parents | {
        i.name for i in items if i.get("custom_label_barcode")
    }
    has_default_wh = {d.parent for d in frappe.get_all(
        "Item Default",
        filters={"parent": ["in", codes], "default_warehouse": ["is", "set"]},
        fields=["parent"],
    )}
    price_items = {p.item_code for p in frappe.get_all(
        "Item Price",
        filters={"item_code": ["in", codes], "price_list": "Standard Selling", "selling": 1},
        fields=["item_code"],
    )}

    field_summary = {}
    issues = {}
    complete = 0

    for it in items:
        missing, warnings = [], []
        if not it.get("custom_chinese_name"):
            missing.append("中文名")
        if not it.get("custom_spu_code"):
            missing.append("SPU编码")
        if it.variant_of and not it.get("custom_pos_short_name"):
            missing.append("POS简称")
        if it.name not in has_barcode:
            missing.append("条码")
        if it.name not in has_default_wh:
            missing.append("默认仓库")
        # 模板（has_variants）本身不出售，不要求售价
        if not it.has_variants and it.name not in price_items:
            missing.append("售价")

        if not it.get("custom_spec_summary"):
            warnings.append("规格摘要")
        if not (it.get("custom_min_stock_level") or 0) > 0:
            warnings.append("最低库存")
        if not it.get("valuation_rate"):
            warnings.append("成本价")

        for f in missing:
            field_summary.setdefault(f, {"missing": 0, "warn": 0, "total": 0})
            field_summary[f]["missing"] += 1
        for f in warnings:
            field_summary.setdefault(f, {"missing": 0, "warn": 0, "total": 0})
            field_summary[f]["warn"] += 1
        for f in set(missing + warnings):
            field_summary[f]["total"] += 1

        if missing or warnings:
            issues[it.name] = {
                "name": it.item_name,
                "missing": missing,
                "warnings": warnings,
            }
        else:
            complete += 1

    return {
        "total": len(items),
        "complete": complete,
        "incomplete": len(items) - complete,
        "field_summary": field_summary,
        "issues": issues,
    }


# ---------------------------------------------------------------------------
# 内部工具
# ---------------------------------------------------------------------------

def _variant_color(item_code):
    vals = frappe.get_all(
        "Item Variant Attribute",
        filters={"parent": item_code, "attribute": ["in", COLOR_ATTR_NAMES]},
        fields=["attribute_value"], limit=1,
    )
    return vals[0]["attribute_value"] if vals else None


def _item_status(row):
    """单条物料资料状态（供向导行内显示）"""
    missing, warnings = [], []
    if not row.get("custom_chinese_name"):
        missing.append("中文名")
    if not row.get("custom_spu_code"):
        missing.append("SPU")
    if row.get("variant_of") and not row.get("custom_pos_short_name"):
        missing.append("POS简称")
    if not (row.get("custom_min_stock_level") or 0) > 0:
        warnings.append("最低库存")
    if not row.get("custom_spec_summary"):
        warnings.append("规格摘要")
    return {"missing": missing, "warnings": warnings}
