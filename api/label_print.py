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
from html import escape

from solua_home.api.stock import validate_positive_integer_qty


_DEFAULT_LABEL_FORMAT = {
    "page_width_mm": 50,
    "page_height_mm": 30,
    "columns": 1,
    "label_width_mm": 50,
    "label_height_mm": 30,
    "column_gap_mm": 0,
    "padding_left_mm": 0,
    "padding_top_mm": 0,
    "padding_right_mm": 0,
    "padding_bottom_mm": 0,
    "orientation": "portrait",
    "barcode_type": "code128",
    "template_key": "print_format",
}

_LABEL_FORMATS = {
    "价格标签 50x30": {
        "page_width_mm": 50,
        "page_height_mm": 30,
        "label_width_mm": 50,
        "label_height_mm": 30,
    },
    "价格标签 50x30 PD": {
        "page_width_mm": 50,
        "page_height_mm": 30,
        "label_width_mm": 50,
        "label_height_mm": 30,
    },
    "物料标签 60x20 双列": {
        "page_width_mm": 60,
        "page_height_mm": 20,
        "columns": 2,
        "label_width_mm": 28,
        "label_height_mm": 20,
        "column_widths_mm": [28, 28],
        "column_gap_mm": 2.5,
        "padding_left_mm": 1,
        "padding_top_mm": 1,
        "padding_right_mm": 0,
        "padding_bottom_mm": 0,
        "orientation": "portrait",
        "barcode_type": "code128",
        "template_key": "item_60x20_double",
    },
    "XPOS Item Barcode Label": {
        "page_width_mm": 50,
        "page_height_mm": 30,
        "label_width_mm": 50,
        "label_height_mm": 30,
    },
}


def _get_label_format(format_name):
    config = dict(_DEFAULT_LABEL_FORMAT)
    config.update(_LABEL_FORMATS.get(format_name, {}))
    config["name"] = format_name
    return config


_EAN13_PARITY = (
    "LLLLLL", "LLGLGG", "LLGGLG", "LLGGGL", "LGLLGG",
    "LGGLLG", "LGGGLL", "LGLGLG", "LGLGGL", "LGGLLL",
)
_EAN13_L = (
    "0001101", "0011001", "0010011", "0111101", "0100011",
    "0110001", "0101111", "0111011", "0110111", "0001011",
)
_EAN13_G = (
    "0100111", "0110011", "0011011", "0100001", "0011101",
    "0111001", "0000101", "0010001", "0001001", "0010111",
)
_EAN13_R = (
    "1110010", "1100110", "1101100", "1000010", "1011100",
    "1001110", "1010000", "1000100", "1001000", "1110100",
)
_CODE128 = (
    "11011001100", "11001101100", "11001100110", "10010011000", "10010001100",
    "10001001100", "10011001000", "10011000100", "10001100100", "11001001000",
    "11001000100", "11000100100", "10110011100", "10011011100", "10011001110",
    "10111001100", "10011101100", "10011100110", "11001110010", "11001011100",
    "11001001110", "11011100100", "11001110100", "11101101110", "11101001100",
    "11100101100", "11100100110", "11101100100", "11100110100", "11100110010",
    "11011011000", "11011000110", "11000110110", "10100011000", "10001011000",
    "10001000110", "10110001000", "10001101000", "10001100010", "11010001000",
    "11000101000", "11000100010", "10110111000", "10110001110", "10001101110",
    "10111011000", "10111000110", "10001110110", "11101110110", "11010001110",
    "11000101110", "11011101000", "11011100010", "11011101110", "11101011000",
    "11101000110", "11100010110", "11101101000", "11101100010", "11100011010",
    "11101111010", "11001000010", "11110001010", "10100110000", "10100001100",
    "10010110000", "10010000110", "10000101100", "10000100110", "10110010000",
    "10110000100", "10011010000", "10011000010", "10000110100", "10000110010",
    "11000010010", "11001010000", "11110111010", "11000010100", "10001111010",
    "10100111100", "10010111100", "10010011110", "10111100100", "10011110100",
    "10011110010", "11110100100", "11110010100", "11110010010", "11011011110",
    "11011110110", "11110110110", "10101111000", "10100011110", "10001011110",
    "10111101000", "10111100010", "11110101000", "11110100010", "10111011110",
    "10111101110", "11101011110", "11110101110", "11010000100", "11010010000",
    "11010011100", "110001110101",
)


def _ean13_check_digit(value):
    value = str(value or "")
    if len(value) != 13 or not value.isdigit():
        return None
    total = sum((1 if index % 2 == 0 else 3) * int(digit) for index, digit in enumerate(value[:12]))
    return str((10 - total % 10) % 10)


def _barcode_type_for_value(value):
    """Choose once per item; both cells receive this exact result."""
    value = str(value or "")
    return "ean13" if _ean13_check_digit(value) == value[-1] else "code128"


def _barcode_modules(value, barcode_type):
    value = str(value or "")
    if barcode_type == "ean13":
        parity = _EAN13_PARITY[int(value[0])]
        bits = "101"
        for index, digit in enumerate(value[1:7]):
            bits += (_EAN13_L if parity[index] == "L" else _EAN13_G)[int(digit)]
        bits += "01010"
        bits += "".join(_EAN13_R[int(digit)] for digit in value[7:])
        return bits + "101"

    codes = [104] + [ord(char) - 32 for char in value]
    codes.append(sum(index * code for index, code in enumerate(codes)) % 103)
    return "".join(_CODE128[code] for code in codes) + _CODE128[106]


def _barcode_svg(value, barcode_type, barcode_id):
    """Render a deterministic, print-safe SVG for one label cell.

    The barcode is built from merged runs instead of one SVG rectangle per
    module.  This avoids repeated anti-aliasing seams when Chrome rasterizes
    the two columns at different sub-pixel x offsets for the TSC driver.
    """
    value = str(value or "")
    modules = _barcode_modules(value, barcode_type)
    module_width = 1.2
    quiet_modules = 10  # 2mm at the fixed 22mm barcode width.
    view_width = (len(modules) + quiet_modules * 2) * module_width
    bar_height = 30
    view_height = 44
    bars = []
    index = 0
    while index < len(modules):
        if modules[index] != "1":
            index += 1
            continue
        run_start = index
        index += 1
        while index < len(modules) and modules[index] == "1":
            index += 1
        run_width = (index - run_start) * module_width
        bars.append(
            f'<rect x="{(run_start + quiet_modules) * module_width:g}" y="0" '
            f'width="{run_width:g}" height="{bar_height}" />'
        )
    safe_value = escape(value, quote=True)
    return (
        f'<svg id="{escape(barcode_id, quote=True)}" '
        f'viewBox="0 0 {view_width:g} {view_height}" '
        f'width="26mm" height="12mm" preserveAspectRatio="xMidYMid meet" '
        f'shape-rendering="crispEdges" '
        f'role="img" aria-label="{safe_value}" data-barcode-ready="true" '
        f'data-barcode-value="{safe_value}" data-barcode-format="{barcode_type}" '
        f'data-module-width="1.2" data-height="30" data-margin="0" '
        f'data-display-value="true" data-quiet-zone-mm="2">'
        f'<g fill="#000">{"".join(bars)}</g>'
        f'<text x="{view_width / 2:g}" y="42" text-anchor="middle" '
        f'font-family="Arial, sans-serif" font-size="8" fill="#000">{safe_value}</text>'
        '</svg>'
    )


def _item_label_barcode(item_code):
    value = frappe.db.get_value("Item", item_code, "custom_label_barcode")
    if not value:
        rows = _get_barcodes(item_code, False)
        value = next((row.get("barcode") for row in rows if row.get("barcode")), None)
    return str(value or item_code)


def _render_60x20_page(item_code, barcode_value, barcode_type, row_index):
    cells = []
    for column_index in range(2):
        barcode_id = f"barcode-row{row_index}-col{column_index}"
        cells.append(
            '<div class="label-cell"><div class="solua-item-label">'
            f'<div class="sku">{escape(str(item_code))}</div>'
            f'{_barcode_svg(barcode_value, barcode_type, barcode_id)}'
            '</div></div>'
        )
    return f'<section class="label-page">{"".join(cells)}</section>'


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
    limit = min(int(limit or 50), 100)

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
        barcodes = _get_barcodes(item.item_code, bool(item.variant_of))
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
                v.barcodes = _get_barcodes(v.item_code, True)
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
            item.barcodes = _get_barcodes(item.item_code, bool(item.variant_of))
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


def _get_barcodes(item_code, is_variant=False):
    """获取物料的原生条码和标签条码；颜色变体不把货号伪装成条码。"""
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

    if not is_variant and item_code not in existing:
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

    config = _get_label_format(format_name)
    pages_html = []
    total_count = 0

    for item_code in item_codes:
        raw_qty = quantities.get(item_code, 1)
        validate_positive_integer_qty(raw_qty, "标签打印数量", item_code)
        qty = int(raw_qty)
        page_count = (qty + config["columns"] - 1) // config["columns"]

        if config["template_key"] == "item_60x20_double":
            barcode_value = _item_label_barcode(item_code)
            barcode_type = _barcode_type_for_value(barcode_value)
            for row_index in range(page_count):
                pages_html.append(
                    _render_60x20_page(item_code, barcode_value, barcode_type, row_index)
                )
            total_count += qty
            continue

        try:
            from frappe.www.printview import get_rendered_template

            label_html = get_rendered_template(
                frappe.get_doc("Item", item_code),
                print_format=frappe.get_doc("Print Format", format_name),
                no_letterhead=True,
            )
        except Exception:
            label_html = _render_fallback_label(item_code, config)

        for _ in range(page_count):
            pages_html.append(_render_label_page(label_html, config))
        total_count += qty

    page_html = _wrap_print_page(pages_html, config)
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
    limit = min(int(limit or 50), 100)

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


def _render_fallback_label(item_code, config):
    """简单回退标签模板"""
    item = frappe.db.get_value(
        "Item", item_code,
        ["item_code", "item_name", "custom_chinese_name", "custom_pos_short_name",
         "standard_rate", "custom_label_barcode"],
        as_dict=True,
    )
    if not item:
        return f"<div class='label-cell'>Not found: {escape(str(item_code))}</div>"

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
        barcode_svg = f'<div style="text-align:center;font-family:monospace;font-size:14px;">{escape(str(barcode))}</div>'

    if config["template_key"] == "item_60x20_double":
        cell = f"""
        <div class="solua-item-label">
            <div class="sku">{escape(str(item.item_code))}</div>
            <div class="fallback-barcode">{barcode_svg}</div>
            <div class="value">{escape(str(barcode))}</div>
        </div>
        """
        return f'<div class="solua-label-stock">{cell}{cell}</div>'

    return f"""
    <div class="label" style="width:{config['label_width_mm']}mm;height:{config['label_height_mm']}mm;border:1px solid #ccc;
         padding:2mm;display:flex;flex-direction:column;justify-content:center;
         align-items:center;box-sizing:border-box;page-break-after:always;">
        <div style="font-size:8pt;font-weight:bold;text-align:center;">{escape(str(name_display or ''))}</div>
        <div style="font-size:6pt;color:#666;">{escape(str(item.item_code))}</div>
        <div style="font-size:10pt;margin:1mm 0;">{item.standard_rate or ''}</div>
        <div style="width:35mm;height:10mm;">{barcode_svg}</div>
    </div>
    """


def _render_label_page(label_html, config):
    """将一个格式模板渲染成一个物理打印页。"""
    if config["template_key"] == "item_60x20_double":
        return f'<section class="label-page">{label_html}</section>'

    cells = "".join(
        f'<div class="label-cell">{label_html}</div>'
        for _ in range(config["columns"])
    )
    return f'<section class="label-page">{cells}</section>'


def _format_number(value):
    return f"{value:g}"


def _column_widths(config):
    widths = config.get("column_widths_mm")
    if widths:
        return " ".join(f"{_format_number(width)}mm" for width in widths)

    available = (
        config["page_width_mm"]
        - config["padding_left_mm"]
        - config["padding_right_mm"]
        - config["column_gap_mm"] * (config["columns"] - 1)
    )
    return " ".join(
        f"{_format_number(available / config['columns'])}mm"
        for _ in range(config["columns"])
    )


def _wrap_print_page(pages_html, config):
    """将物理页包装成无 ERPNext 默认版式干扰的打印 HTML。"""
    joined = "\n".join(pages_html)
    width = _format_number(config["page_width_mm"])
    height = _format_number(config["page_height_mm"])
    padding = " ".join(
        f"{_format_number(config[key])}mm"
        for key in (
            "padding_top_mm",
            "padding_right_mm",
            "padding_bottom_mm",
            "padding_left_mm",
        )
    )
    return f"""<!DOCTYPE html>
<html>
<head>
<meta charset="utf-8">
<title>{_('Label Print')}</title>
<style>
@page {{ size: {width}mm {height}mm; margin: 0; }}
*, *::before, *::after {{ box-sizing: border-box; }}
html, body {{
    margin: 0 !important;
    padding: 0 !important;
    width: {width}mm;
    min-height: 0 !important;
    background: #fff;
}}
body {{ overflow-x: hidden; }}
.print-toolbar, .print-header, button, .no-print, .print-info {{ display: none !important; }}
.print-format, .print-format-gutter, .page-break {{
    margin: 0 !important;
    padding: 0 !important;
    min-height: 0 !important;
    border: 0 !important;
}}
.label-page {{
    width: {width}mm;
    height: {height}mm;
    box-sizing: border-box;
    margin: 0;
    padding: {padding};
    display: grid;
    grid-template-columns: {_column_widths(config)};
    column-gap: {_format_number(config['column_gap_mm'])}mm;
    page-break-inside: avoid;
    break-inside: avoid;
    overflow: visible;
}}
.label-page:not(:last-child) {{ page-break-after: always; break-after: page; }}
.label-cell {{
    box-sizing: border-box;
    width: 26mm;
    height: 100%;
    min-width: 0;
    overflow: visible;
    display: flex;
    align-items: flex-start;
    justify-content: center;
    page-break-inside: avoid;
    break-inside: avoid;
}}
.label-page > .solua-label-stock {{
    display: contents;
    width: auto !important;
    height: auto !important;
    padding: 0 !important;
}}
.label-page .solua-item-label {{
    box-sizing: border-box;
    width: 26mm !important;
    height: 100%;
    overflow: visible;
    text-align: center;
    font-family: Arial, sans-serif;
    white-space: nowrap;
    display: flex;
    flex-direction: column;
    align-items: center;
    page-break-inside: avoid;
    break-inside: avoid;
}}
.label-page .solua-item-label .sku {{
    height: 3.2mm;
    overflow: visible;
    font-size: 6.5pt;
    line-height: 3.2mm;
    font-weight: 700;
}}
.label-page .solua-item-label svg {{
    display: block;
    width: 26mm !important;
    height: 12mm !important;
    flex: 0 0 26mm;
    margin: 0;
    overflow: visible;
    shape-rendering: crispEdges;
}}
.label-page .label {{
    max-width: none !important;
    max-height: none !important;
    margin: 0 !important;
    page-break-after: auto !important;
    break-after: auto !important;
}}
@media screen {{
    body {{ background: #eee; }}
    .label-page {{ margin: 8px auto; background: #fff; box-shadow: 0 1px 4px #bbb; }}
}}
</style>
</head>
<body>
{joined}
</body>
</html>"""
