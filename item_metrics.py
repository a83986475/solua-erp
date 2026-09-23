# -*- coding: utf-8 -*-
"""物料列表的「当前库存」与「四档售价」列。

ERPNext 自带的 `total_projected_qty` / `standard_rate` 在本地长期为 0，所以物料列表看起来
既没库存也没价格。这里把真实数据镜像到 6 个只读字段上：

- `custom_stock_qty`：本物料在各在用叶子仓库的 Bin 实际数量合计
- `custom_variant_stock_qty`：模板专用，其所有变体的库存合计
- `custom_rate_cost` / `custom_rate_home` / `custom_rate_wholesale` / `custom_rate_retail`：
  Standard Buying / Wholesale Selling 3 / Wholesale Selling / Standard Selling 四个价目表

字段只在真正变化时写入，并在库存单据提交/取消、Item Price 变化、Item 自身保存时重算，
另有 `refresh_all_item_metrics()` 供批量导入后手动重算（物料列表右上角按钮）。
"""

import frappe
from frappe import _
from frappe.utils import flt

# 字段名 -> 价目表（窗帘四级价格体系，见手册 19.8）
PRICE_FIELDS = {
    "custom_rate_cost": "Standard Buying",
    "custom_rate_home": "Wholesale Selling 3",
    "custom_rate_wholesale": "Wholesale Selling",
    "custom_rate_retail": "Standard Selling",
}
STOCK_FIELD = "custom_stock_qty"
VARIANT_STOCK_FIELD = "custom_variant_stock_qty"
METRIC_FIELDS = [STOCK_FIELD, VARIANT_STOCK_FIELD, *PRICE_FIELDS]
PRICE_LISTS = tuple(dict.fromkeys(PRICE_FIELDS.values()))
# 会移动库存且以 StockController 提交的单据：钩子在控制器之后运行，此时 Bin 已写好
STOCK_VOUCHERS = (
    "Stock Entry",
    "Stock Reconciliation",
    "Purchase Receipt",
    "Purchase Invoice",
    "Delivery Note",
    "Sales Invoice",
    "POS Invoice",
)
_CHUNK = 500

_LABELS = {
    "custom_rate_cost": _("成本价"),
    "custom_rate_home": _("Home Store 价"),
    "custom_rate_wholesale": _("批发价"),
    "custom_rate_retail": _("建议零售价"),
    STOCK_FIELD: _("当前库存"),
    VARIANT_STOCK_FIELD: _("变体库存合计"),
}


def _installed():
    return frappe.db.has_column("Item", STOCK_FIELD)


def ensure_item_metric_fields():
    """幂等创建 6 个只读字段（安装/迁移与一次性部署共用）。"""
    fields = []
    parent = "standard_rate" if frappe.get_meta("Item").has_field("standard_rate") else "item_name"
    for fieldname, price_list in PRICE_FIELDS.items():
        fields.append({
            "fieldname": fieldname,
            "label": _LABELS[fieldname],
            "fieldtype": "Currency",
            "read_only": 1,
            "no_copy": 1,
            "in_list_view": 1,
            "insert_after": parent,
            "description": _("来自价目表 {0}；在库存单据/价格变化时自动重算").format(price_list),
        })
        parent = fieldname
    fields.append({
        "fieldname": STOCK_FIELD,
        "label": _LABELS[STOCK_FIELD],
        "fieldtype": "Float",
        "precision": "2",
        "read_only": 1,
        "no_copy": 1,
        "in_list_view": 1,
        "insert_after": parent,
        "description": _("在用仓库的 Bin 实际数量合计；模板的库存在变体上"),
    })
    fields.append({
        "fieldname": VARIANT_STOCK_FIELD,
        "label": _LABELS[VARIANT_STOCK_FIELD],
        "fieldtype": "Float",
        "precision": "2",
        "read_only": 1,
        "no_copy": 1,
        "in_list_view": 1,
        "depends_on": "eval:doc.has_variants",
        "insert_after": STOCK_FIELD,
        "description": _("模板下所有变体的库存合计"),
    })

    created = []
    for field in fields:
        if frappe.db.exists("Custom Field", {"dt": "Item", "fieldname": field["fieldname"]}):
            continue
        frappe.get_doc({"doctype": "Custom Field", "dt": "Item", **field}).insert(ignore_permissions=True)
        created.append(field["fieldname"])
    if created:
        frappe.clear_cache(doctype="Item")
    return created


def _leaf_warehouses():
    return "ifnull(w.is_group, 0) = 0 and ifnull(w.disabled, 0) = 0"


def stock_totals(item_codes):
    """按物料汇总在用叶子仓库的实际库存。"""
    codes = list(item_codes)
    if not codes:
        return {}
    rows = frappe.db.sql(
        f"""select b.item_code as item_code, sum(b.actual_qty) as qty
            from `tabBin` b inner join `tabWarehouse` w on w.name = b.warehouse
            where b.item_code in %(codes)s and {_leaf_warehouses()}
            group by b.item_code""",
        {"codes": codes}, as_dict=True)
    return {row.item_code: row.qty for row in rows}


def variant_stock_totals(template_codes):
    """按模板汇总其全部变体的实际库存。"""
    codes = list(template_codes)
    if not codes:
        return {}
    rows = frappe.db.sql(
        f"""select i.variant_of as template, sum(b.actual_qty) as qty
            from `tabItem` i
            inner join `tabBin` b on b.item_code = i.name
            inner join `tabWarehouse` w on w.name = b.warehouse
            where i.variant_of in %(codes)s and {_leaf_warehouses()}
            group by i.variant_of""",
        {"codes": codes}, as_dict=True)
    return {row.template: row.qty for row in rows}


def price_rates(item_codes, stock_uoms):
    """每个物料的四个价格档位；跳过客户/供应商专属价，优先本位计量单位的那条。"""
    codes = list(item_codes)
    if not codes:
        return {}
    rows = frappe.db.sql(
        """select ip.item_code as item_code, ip.price_list as price_list, ip.price_list_rate as rate,
                  ifnull(ip.uom, '') as uom
           from `tabItem Price` ip
           where ip.item_code in %(codes)s and ip.price_list in %(lists)s
             and ifnull(ip.customer, '') = '' and ifnull(ip.supplier, '') = ''
           order by ip.valid_from desc, ip.modified desc""",
        {"codes": codes, "lists": list(PRICE_LISTS)}, as_dict=True)
    best = {}
    for row in rows:
        key = (row.item_code, row.price_list)
        score = 1 if row.uom and row.uom == stock_uoms.get(row.item_code) else 0
        if key not in best or score > best[key][0]:
            best[key] = (score, row.rate)
    return {key: value for key, (score, value) in best.items()}


def _collect(updates, name, fieldname, value, current):
    if flt(value, 2) == flt(current, 2):
        return
    updates.setdefault(name, {})[fieldname] = flt(value, 2)


def refresh_items(item_codes, stock=True, prices=True):
    """重算指定物料的库存/售价镜像字段，返回被改动的物料数。"""
    codes = [str(code).strip() for code in (item_codes or []) if code and str(code).strip()]
    codes = list(dict.fromkeys(codes))
    if not codes or not _installed():
        return 0

    fields = ["name", "has_variants", "variant_of", "stock_uom", *METRIC_FIELDS]
    targets = {row.name: row for row in frappe.get_all(
        "Item", filters={"name": ["in", codes]}, fields=fields, limit_page_length=0)}
    if not targets:
        return 0
    parents = sorted({row.variant_of for row in targets.values() if row.get("variant_of")})
    if parents:
        for row in frappe.get_all("Item", filters={"name": ["in", parents]}, fields=fields, limit_page_length=0):
            targets.setdefault(row.name, row)

    names = list(targets)
    updates = {}
    if stock:
        own = stock_totals(names)
        templates = [name for name in names if int(targets[name].get("has_variants") or 0)]
        variant_totals = variant_stock_totals(templates) if templates else {}
        for name in names:
            row = targets[name]
            _collect(updates, name, STOCK_FIELD, own.get(name, 0.0), row.get(STOCK_FIELD))
            if int(row.get("has_variants") or 0):
                _collect(updates, name, VARIANT_STOCK_FIELD, variant_totals.get(name, 0.0), row.get(VARIANT_STOCK_FIELD))
    if prices:
        uoms = {name: (targets[name].get("stock_uom") or "") for name in names}
        rates = price_rates(names, uoms)
        for name in names:
            for fieldname, price_list in PRICE_FIELDS.items():
                _collect(updates, name, fieldname, rates.get((name, price_list), 0.0), targets[name].get(fieldname))

    for name, values in updates.items():
        frappe.db.set_value("Item", name, values, update_modified=False)
    return len(updates)


def refresh_all_items():
    """全量重算（批量导入后或人工修复用）。"""
    if not _installed():
        return 0
    codes = frappe.get_all("Item", pluck="name", limit_page_length=0)
    updated = 0
    for start in range(0, len(codes), _CHUNK):
        updated += refresh_items(codes[start:start + _CHUNK])
    return updated


@frappe.whitelist()
def refresh_all_item_metrics():
    """物料列表右上角「刷新库存与售价」按钮的后端。"""
    frappe.only_for(("System Manager", "Stock Manager", "Item Manager", "Sales Manager", "Accounts Manager"))
    return {"updated": refresh_all_items()}


def on_item_price_change(doc, method=None):
    """Item Price 新增/修改/删除后刷新该物料的价格列。"""
    refresh_items([doc.item_code], stock=False)


def _doc_item_codes(doc):
    """单据明细里的物料编码（子表行既可能是文档也可能是普通字典）。"""
    rows = doc.get("items") if hasattr(doc, "get") else getattr(doc, "items", None)
    codes = set()
    for row in rows or []:
        code = row.get("item_code") if hasattr(row, "get") else getattr(row, "item_code", None)
        if code:
            codes.add(code)
    return codes


def on_stock_voucher_change(doc, method=None):
    """库存单据提交/取消后刷新涉及物料的库存列（含变体所属模板的合计）。"""
    codes = _doc_item_codes(doc)
    if codes:
        refresh_items(sorted(codes), prices=False)


def on_item_change(doc, method=None):
    """物料保存后把两列都对齐一次（导入/直接编辑时也能自愈）。"""
    refresh_items([doc.name])


def after_migrate():
    """迁移后补建字段并重算一次，避免历史数据留下空列。"""
    ensure_item_metric_fields()
    refresh_all_items()
