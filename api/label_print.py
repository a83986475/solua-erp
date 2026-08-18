"""Label Printing API for solua_home

提供：
- search_items_for_label: 按条码/名称/编码搜索物料（含库存数量）
- get_label_print_formats: 获取 Item 的可用打印格式列表
- generate_label_html: 为指定物料列表生成可打印的标签 HTML 页面
- record_print_history: 记录打印历史
- get_print_history: 查询最近打印历史
"""
import frappe
from frappe import _
import json


@frappe.whitelist()
def search_items_for_label(query=None, limit=20):
    """搜索物料用于标签打印（含库存数量）

    支持：
    - 精确条码匹配（barcode / custom_label_barcode）→ 直接返回唯一物料
    - 模糊搜索（item_code / item_name / custom_chinese_name / custom_pos_short_name）
    - 返回条码列表、库存数量供打印使用
    """
    if not query or not query.strip():
        return []

    q = query.strip()
    limit = min(int(limit or 20), 50)

    # 1) 精确条码匹配（优先级最高）
    barcode_match = _find_by_barcode(q)
    if barcode_match:
        return barcode_match

    # 2) 模糊搜索（名称/编码/中文名/简称）——含库存数量
    like = f"%{q}%"
    items = frappe.db.sql("""
        SELECT
            i.item_code, i.item_name,
            i.custom_chinese_name, i.custom_pos_short_name,
            i.custom_spu_code, i.custom_spec_summary,
            i.standard_rate, i.image,
            i.has_variants, i.variant_of,
            i.item_group, i.stock_uom,
            COALESCE(SUM(b.actual_qty), 0) as stock_qty
        FROM `tabItem` i
        LEFT JOIN `tabBin` b ON b.item_code = i.item_code
        WHERE i.disabled = 0
          AND i.is_fixed_asset = 0
          AND i.item_code NOT LIKE '_%%/_%%'
          AND (
              i.item_code LIKE %(like)s
              OR i.item_name LIKE %(like)s
              OR i.custom_chinese_name LIKE %(like)s
              OR i.custom_pos_short_name LIKE %(like)s
              OR i.custom_spu_code LIKE %(like)s
          )
        GROUP BY i.item_code
        ORDER BY
            CASE
                WHEN i.item_code LIKE %(q)s THEN 0
                WHEN i.item_code LIKE %(like)s THEN 1
                ELSE 2
            END,
            i.item_code
        LIMIT %(limit)s
    """, {"q": q, "like": like, "limit": limit}, as_dict=True)

    result = []
    for item in items:
        barcodes = _get_barcodes(item.item_code)
        item.barcodes = barcodes
        item.display_name = (
            item.custom_chinese_name
            or item.custom_pos_short_name
            or item.item_name
            or item.item_code
        )
        item.stock_qty = int(item.stock_qty or 0)
        # 变体信息
        item.is_variant = bool(item.variant_of)
        item.is_template = bool(item.has_variants)
        if item.is_variant:
            item.template_name = item.variant_of
            item.template_chinese_name = frappe.db.get_value(
                "Item", item.variant_of, "custom_chinese_name"
            ) or ""
        result.append(item)

    return result


def _find_by_barcode(query):
    """按条码精确搜索物料（含库存数量）"""
    bc_items = frappe.db.sql("""
        SELECT DISTINCT ib.parent as item_code
        FROM `tabItem Barcode` ib
        WHERE ib.barcode = %(barcode)s
        LIMIT 10
    """, {"barcode": query}, as_dict=True)

    if not bc_items:
        cf_items = frappe.db.sql("""
            SELECT item_code
            FROM `tabItem`
            WHERE custom_label_barcode = %(barcode)s
              AND disabled = 0
            LIMIT 10
        """, {"barcode": query}, as_dict=True)
        bc_items = cf_items

    if not bc_items:
        return []

    result = []
    for bc in bc_items:
        # 获取物料信息 + 库存
        row = frappe.db.sql("""
            SELECT
                i.item_code, i.item_name, i.custom_chinese_name,
                i.custom_pos_short_name, i.custom_spu_code, i.custom_spec_summary,
                i.standard_rate, i.image, i.has_variants, i.variant_of,
                i.item_group, i.stock_uom,
                COALESCE(SUM(b.actual_qty), 0) as stock_qty
            FROM `tabItem` i
            LEFT JOIN `tabBin` b ON b.item_code = i.item_code
            WHERE i.item_code = %(code)s
            GROUP BY i.item_code
        """, {"code": bc.item_code}, as_dict=True)

        if not row:
            continue

        item = row[0] if isinstance(row, list) else row
        item.stock_qty = int(item.stock_qty or 0)

        if item.has_variants:
            # 模板物料：返回模板 + 所有变体
            variants = frappe.db.sql("""
                SELECT
                    v.item_code, v.item_name, v.custom_chinese_name,
                    v.custom_pos_short_name, v.custom_spec_summary,
                    v.standard_rate, v.image, v.item_group, v.stock_uom,
                    COALESCE(SUM(b.actual_qty), 0) as stock_qty
                FROM `tabItem` v
                LEFT JOIN `tabBin` b ON b.item_code = v.item_code
                WHERE v.variant_of = %(template)s AND v.disabled = 0
                GROUP BY v.item_code
            """, {"template": item.item_code}, as_dict=True)
            for v in variants:
                v.stock_qty = int(v.stock_qty or 0)
                v.barcodes = _get_barcodes(v.item_code)
                v.display_name = (
                    v.custom_chinese_name or v.custom_pos_short_name
                    or v.item_name or v.item_code
                )
                v.is_variant = True
                v.is_template = False
                v.template_name = item.item_code
                v.template_chinese_name = item.custom_chinese_name or ""
                result.append(v)
        else:
            item.barcodes = _get_barcodes(item.item_code)
            item.display_name = (
                item.custom_chinese_name or item.custom_pos_short_name
                or item.item_name or item.item_code
            )
            item.is_variant = bool(item.variant_of)
            item.is_template = False
            if item.variant_of:
                item.template_name = item.variant_of
                item.template_chinese_name = frappe.db.get_value(
                    "Item", item.variant_of, "custom_chinese_name"
                ) or ""
            result.append(item)

    return result


def _get_barcodes(item_code):
    """获取物料的所有条码"""
    barcodes = frappe.get_all(
        "Item Barcode",
        filters={"parent": item_code},
        fields=["barcode", "barcode_type"],
    )
    existing = {b["barcode"] for b in barcodes}

    label_bc = frappe.db.get_value("Item", item_code, "custom_label_barcode")
    if label_bc and label_bc not in existing:
        barcodes.append({"barcode": label_bc, "barcode_type": "EAN"})
        existing.add(label_bc)

    if item_code not in existing:
        barcodes.append({"barcode": item_code, "barcode_type": "Code128"})

    return barcodes


@frappe.whitelist()
def get_label_print_formats():
    """获取 Item 的可用打印格式列表"""
    formats = frappe.get_all(
        "Print Format",
        filters={"doc_type": "Item", "disabled": 0},
        fields=["name", "module"],
        order_by="module, name",
    )
    return formats


@frappe.whitelist()
def generate_label_html(item_codes, format_name="价格标签 50x30", quantities=None):
    """为指定物料列表生成可打印的标签 HTML 页面"""
    if isinstance(item_codes, str):
        item_codes = json.loads(item_codes)
    if isinstance(quantities, str):
        quantities = json.loads(quantities)
    if not quantities:
        quantities = {}

    labels_html = []
    total_count = 0

    for item_code in item_codes:
        qty = int(quantities.get(item_code, 1))
        if qty <= 0:
            continue

        try:
            from frappe.utils.print_format import render_template
            label_html = render_template(
                doctype="Item",
                name=item_code,
                print_format=format_name,
                no_letterhead=True,
            )
        except Exception:
            label_html = _render_fallback_label(item_code, qty)

        for _ in range(qty):
            labels_html.append(label_html)
            total_count += 1

    page_html = _wrap_print_page(labels_html)
    return {"html": page_html, "label_count": total_count}


# ─── 打印历史 ─────────────────────────────────────────────────────


@frappe.whitelist()
def record_print_history(item_codes, format_name, quantities, total_labels):
    """记录一次标签打印历史

    Args:
        item_codes: JSON 数组，打印了哪些物料
        format_name: 使用的打印格式
        quantities: JSON 对象，各物料打印数量
        total_labels: 总标签数
    """
    if isinstance(item_codes, str):
        item_codes = json.loads(item_codes)
    if isinstance(quantities, str):
        quantities = json.loads(quantities)

    # 获取物料名称摘要
    item_names = []
    for code in item_codes[:10]:  # 最多记录 10 个
        name = frappe.db.get_value("Item", code, "custom_chinese_name") or code
        qty = quantities.get(code, 1)
        item_names.append(f"{name}×{qty}")
    summary = "、".join(item_names)
    if len(item_codes) > 10:
        summary += f" 等{len(item_codes)}种"

    try:
        doc = frappe.get_doc({
            "doctype": "Comment",
            "comment_type": "Info",
            "reference_doctype": "Item",
            "reference_name": item_codes[0] if item_codes else "",
            "content": (
                f"<b>🏷️ 标签打印</b><br>"
                f"格式：{format_name} | 数量：{total_labels}张<br>"
                f"物料：{summary}"
            ),
            "comment_by": frappe.session.user,
        })
        doc.insert(ignore_permissions=True)
        frappe.db.commit()
    except Exception as e:
        frappe.log_error(f"打印历史记录失败: {e}", "solua_home.label_print")


@frappe.whitelist()
def get_print_history(limit=20):
    """获取最近的标签打印历史

    Returns:
        list: 最近的打印记录（从 Comment 表筛选）
    """
    limit = min(int(limit or 20), 50)

    # 从 Comment 表获取标签打印记录
    records = frappe.db.sql("""
        SELECT
            c.name, c.content, c.creation, c.comment_by,
            c.reference_name
        FROM `tabComment` c
        WHERE c.comment_type = 'Info'
          AND c.content LIKE '%%标签打印%%'
        ORDER BY c.creation DESC
        LIMIT %(limit)s
    """, {"limit": limit}, as_dict=True)

    result = []
    for r in records:
        # 解析 content 提取信息
        content = r.content or ""
        result.append({
            "name": r.name,
            "creation": str(r.creation),
            "user": r.comment_by,
            "item_code": r.reference_name,
            "content": content,
            # 从 HTML content 提取纯文本摘要
            "summary": _parse_history_summary(content),
        })

    return result


def _parse_history_summary(html_content):
    """从 HTML content 提取纯文本摘要"""
    import re
    text = re.sub(r'<[^>]+>', ' ', html_content)
    text = re.sub(r'\s+', ' ', text).strip()
    return text[:120]  # 截断过长内容


# ─── 回退标签模板 ──────────────────────────────────────────────────


def _render_fallback_label(item_code, qty=1):
    """简单回退标签模板"""
    item = frappe.db.get_value(
        "Item", item_code,
        ["item_code", "item_name", "custom_chinese_name", "custom_pos_short_name",
         "standard_rate", "custom_label_barcode"],
        as_dict=True,
    )
    if not item:
        return f"<div class='label'>Not found: {item_code}</div>"

    barcode = item.custom_label_barcode or item.item_code
    name_display = item.custom_chinese_name or item.custom_pos_short_name or item.item_name

    try:
        import barcode as bc_mod
        from barcode.writer import SVGWriter
        from io import BytesIO
        bc128 = bc_mod.get_barclass('code128')(barcode, writer=SVGWriter())
        buf = BytesIO()
        bc128.write(buf, options={"module_width": 0.3, "module_height": 8, "font_size": 8})
        barcode_svg = buf.getvalue().decode("utf-8")
    except Exception:
        barcode_svg = f'<div style="text-align:center;font-family:monospace;font-size:14px;">{barcode}</div>'

    return f"""
    <div class="label" style="width:50mm;height:30mm;border:1px solid #ccc;
         padding:2mm;display:flex;flex-direction:column;justify-content:center;
         align-items:center;box-sizing:border-box;page-break-after:always;">
        <div style="font-size:8pt;font-weight:bold;text-align:center;">{name_display}</div>
        <div style="font-size:6pt;color:#666;">{item.item_code}</div>
        <div style="font-size:10pt;margin:1mm 0;">{item.standard_rate or ''}</div>
        <div style="width:35mm;height:10mm;">{barcode_svg}</div>
    </div>
    """


def _wrap_print_page(labels_html):
    """将标签列表包装成完整可打印 HTML 页面"""
    joined = "\n".join(labels_html)
    return f"""<!DOCTYPE html>
<html>
<head>
<meta charset="utf-8">
<title>{_('Label Print')}</title>
<style>
@media print {{
    @page {{ margin: 2mm; size: auto; }}
    body {{ margin: 0; padding: 0; }}
    .label {{ page-break-inside: avoid; page-break-after: always; }}
}}
@media screen {{
    body {{
        font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
        background: #f5f5f5; padding: 20px;
    }}
    .label {{
        background: white; margin: 10px auto;
        box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        page-break-inside: avoid; page-break-after: always; max-width: 200mm;
    }}
    .print-info {{ text-align: center; color: #666; margin-bottom: 20px; font-size: 14px; }}
    .print-btn {{
        display: block; margin: 20px auto; padding: 10px 30px;
        background: #007bff; color: white; border: none; border-radius: 4px;
        cursor: pointer; font-size: 16px;
    }}
    .print-btn:hover {{ background: #0056b3; }}
}}
</style>
</head>
<body>
<div class="print-info">
    {len(labels_html)} {_('labels ready to print')}
    <br><button class="print-btn" onclick="window.print()">{_('Print')}</button>
</div>
{joined}
</body>
</html>"""
