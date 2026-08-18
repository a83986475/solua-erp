"""Label Printing API for solua_home

提供：
- search_items_for_label: 按条码/名称/编码搜索物料，返回可用信息
- get_label_print_formats: 获取 Item 的可用打印格式列表
- generate_label_html: 为指定物料列表生成可打印的标签 HTML 页面
"""
import frappe
from frappe import _


@frappe.whitelist()
def search_items_for_label(query=None, limit=20):
    """搜索物料用于标签打印

    支持：
    - 精确条码匹配（barcode / custom_label_barcode）→ 直接返回唯一物料
    - 模糊搜索（item_code / item_name / custom_chinese_name / custom_pos_short_name）
    - 返回条码列表供打印使用

    Args:
        query: 搜索关键词（条码、编码、名称）
        limit: 最大返回数量

    Returns:
        list: 物料列表，含 item_code, item_name, custom_chinese_name,
              standard_rate, image, barcodes, has_variants, variant_of
    """
    if not query or not query.strip():
        return []

    q = query.strip()
    limit = min(int(limit or 20), 50)

    # 1) 精确条码匹配（优先级最高）
    barcode_match = _find_by_barcode(q)
    if barcode_match:
        return barcode_match

    # 2) 模糊搜索（名称/编码/中文名/简称）
    like = f"%{q}%"
    items = frappe.db.sql("""
        SELECT
            i.item_code, i.item_name,
            i.custom_chinese_name, i.custom_pos_short_name,
            i.custom_spu_code, i.custom_spec_summary,
            i.standard_rate, i.image,
            i.has_variants, i.variant_of,
            i.item_group, i.stock_uom
        FROM `tabItem` i
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
        # 变体信息
        item.is_variant = bool(item.variant_of)
        item.is_template = bool(item.has_variants)
        if item.is_variant:
            template_name = item.variant_of
            item.template_name = template_name
            item.template_chinese_name = frappe.db.get_value(
                "Item", template_name, "custom_chinese_name"
            ) or ""
        result.append(item)

    return result


def _find_by_barcode(query):
    """按条码精确搜索物料"""
    # 查 Item Barcode 子表
    bc_items = frappe.db.sql("""
        SELECT DISTINCT ib.parent as item_code
        FROM `tabItem Barcode` ib
        WHERE ib.barcode = %(barcode)s
        LIMIT 10
    """, {"barcode": query}, as_dict=True)

    if not bc_items:
        # 查 custom_label_barcode 字段
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
        item = frappe.db.get_value(
            "Item", bc.item_code,
            ["item_code", "item_name", "custom_chinese_name",
             "custom_pos_short_name", "custom_spu_code", "custom_spec_summary",
             "standard_rate", "image", "has_variants", "variant_of",
             "item_group", "stock_uom"],
            as_dict=True,
        )
        if not item or item.has_variants:
            # 模板物料：返回模板 + 所有变体
            if item and item.has_variants:
                variants = frappe.db.get_all(
                    "Item",
                    filters={"variant_of": item.item_code, "disabled": 0},
                    fields=["item_code", "item_name", "custom_chinese_name",
                            "custom_pos_short_name", "custom_spec_summary",
                            "standard_rate", "image", "item_group", "stock_uom"],
                )
                for v in variants:
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
                # 模板无变体
                item.barcodes = _get_barcodes(item.item_code)
                item.display_name = (
                    item.custom_chinese_name or item.custom_pos_short_name
                    or item.item_name or item.item_code
                )
                item.is_variant = False
                item.is_template = True
                result.append(item)
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
    # frappe.get_all 返回 dict 列表，统一用 dict 访问
    existing = {b["barcode"] for b in barcodes}

    # 加上 custom_label_barcode
    label_bc = frappe.db.get_value("Item", item_code, "custom_label_barcode")
    if label_bc and label_bc not in existing:
        barcodes.append({"barcode": label_bc, "barcode_type": "EAN"})
        existing.add(label_bc)

    # 加上物料编码本身作为备选条码
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
    """为指定物料列表生成可打印的标签 HTML 页面

    Args:
        item_codes: 物料编码列表（JSON 数组字符串）
        format_name: 打印格式名称
        quantities: 各物料打印数量（JSON 对象 {item_code: qty}）

    Returns:
        dict: {html: str, label_count: int}
    """
    import json

    if isinstance(item_codes, str):
        item_codes = json.loads(item_codes)
    if isinstance(quantities, str):
        quantities = json.loads(quantities)
    if not quantities:
        quantities = {}

    from frappe.utils.pdf import get_pdf

    labels_html = []
    total_count = 0

    for item_code in item_codes:
        qty = int(quantities.get(item_code, 1))
        if qty <= 0:
            continue

        try:
            # 使用 Frappe 的 print_format 渲染单个标签
            from frappe.utils.print_format import render_template
            label_html = render_template(
                doctype="Item",
                name=item_code,
                print_format=format_name,
                no_letterhead=True,
            )
        except Exception:
            # fallback: 用简单 HTML 模板
            label_html = _render_fallback_label(item_code, qty)

        for _ in range(qty):
            labels_html.append(label_html)
            total_count += 1

    # 组合成完整可打印页面
    page_html = _wrap_print_page(labels_html)

    return {"html": page_html, "label_count": total_count}


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

    # 生成条码图片（使用 Code128）
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
    @page {{
        margin: 2mm;
        size: auto;
    }}
    body {{
        margin: 0;
        padding: 0;
    }}
    .label {{
        page-break-inside: avoid;
        page-break-after: always;
    }}
}}
@media screen {{
    body {{
        font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
        background: #f5f5f5;
        padding: 20px;
    }}
    .label {{
        background: white;
        margin: 10px auto;
        box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        page-break-inside: avoid;
        page-break-after: always;
        max-width: 200mm;
    }}
    .print-info {{
        text-align: center;
        color: #666;
        margin-bottom: 20px;
        font-size: 14px;
    }}
    .print-btn {{
        display: block;
        margin: 20px auto;
        padding: 10px 30px;
        background: #007bff;
        color: white;
        border: none;
        border-radius: 4px;
        cursor: pointer;
        font-size: 16px;
    }}
    .print-btn:hover {{
        background: #0056b3;
    }}
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
