"""销售订单 / 销售单 / 交货单 / 拣货单：把单据明细导出成表格（Excel / CSV）。

导出列与打印表格保持一致（货号、SPU、色号、条码、描述、补充说明、数量、单价、金额、仓库），
并在底部给出数量合计，方便仓管、客户与财务直接拿去用表格处理；图片列不导出。

入口（均为 GET 可调用，浏览器打开链接即下载）：
    /api/method/solua_home.api.export.export_document_table?doctype=..&name=..&fmt=xlsx
"""

import csv
import io
import re
from zipfile import ZIP_DEFLATED, ZipFile

import frappe
from frappe import _
from frappe.utils import cint, flt, nowdate

EXPORT_DOCTYPES = ("Sales Order", "Sales Invoice", "Delivery Note", "Pick List")

SOLUA_BULK_PDF_DOCTYPES = frozenset(EXPORT_DOCTYPES)
SOLUA_PDF_MARGINS = {
    "margin-top": "12mm",
    "margin-bottom": "12mm",
    "margin-left": "12mm",
    "margin-right": "12mm",
}

# 列顺序 = 导出/勾选面板的显示顺序
COLUMN_LABELS = (
    ("idx", "序号"),
    ("item_code", "货号"),
    ("item_name", "商品名称"),
    ("spu", "SPU"),
    ("order_code", "订货货号"),
    ("color_code", "色号"),
    ("color", "颜色"),
    ("barcode", "条码"),
    ("description", "描述"),
    ("additional_notes", "补充说明"),
    ("qty", "数量"),
    ("picked_qty", "已拣数量"),
    ("uom", "单位"),
    ("rate", "单价"),
    ("amount", "金额"),
    ("warehouse", "仓库"),
    ("ordered_qty", "订购数量"),
    ("delivered_before_qty", "此前已交付"),
    ("remaining_qty", "剩余数量"),
)
LABELS = dict(COLUMN_LABELS)
# 作为数字写入表格（Excel 可直接求和），其余按文本写入
NUMERIC_COLUMNS = ("idx", "qty", "picked_qty", "rate", "amount", "ordered_qty", "delivered_before_qty", "remaining_qty")

_WHOLESALE_COLUMNS = (
    "idx", "item_code", "item_name", "spu", "order_code", "color_code", "color", "barcode", "description",
    "additional_notes", "qty", "uom", "rate", "amount", "warehouse",
)
DOCTYPE_COLUMNS = {
    "Sales Order": _WHOLESALE_COLUMNS,
    "Sales Invoice": _WHOLESALE_COLUMNS,
    "Delivery Note": _WHOLESALE_COLUMNS + ("ordered_qty", "delivered_before_qty", "remaining_qty"),
    # 拣货单没有价格与订单关联，只导出拣货数量、仓库与商品信息
    "Pick List": (
        "idx", "item_code", "item_name", "spu", "color_code", "color", "barcode", "description", "additional_notes",
        "qty", "picked_qty", "uom", "warehouse",
    ),
}


def _require_doctype(doctype):
    if doctype not in EXPORT_DOCTYPES:
        frappe.throw(_("不支持导出该单据类型：{0}").format(doctype))


def get_export_document(doctype, name):
    """Load a document that this whitelist allows exporting, with a read check."""
    _require_doctype(doctype)
    doc = frappe.get_doc(doctype, name)
    if not frappe.has_permission(doctype, "read", doc=doc):
        frappe.throw(_("没有读取该单据的权限"), frappe.PermissionError)
    return doc


def _wholesale_rows(doc):
    """Reuse the print data so the export matches the printed table exactly."""
    from solua_home.printing.wholesale import get_wholesale_print_data

    data = get_wholesale_print_data(doc)
    rows = []
    for position, item in enumerate(data.get("items") or [], start=1):
        row = {"idx": position}
        for key in DOCTYPE_COLUMNS[doc.doctype]:
            if key != "idx":
                row[key] = item.get(key)
        rows.append(row)
    return rows


def _pick_list_rows(doc):
    """拣货单的行在 locations 子表（Pick List Item）里，不是 items。"""
    from solua_home.printing.color_card import get_item_color_info
    from solua_home.printing.wholesale import get_item_sales_display, get_item_spu, _get_pick_list_additional_notes

    rows = []
    entries = doc.get("locations") or doc.get("items") or []
    for position, item in enumerate(entries, start=1):
        color = get_item_color_info(item.item_code) or {}
        display = get_item_sales_display(item.item_code, item.get("description"))
        rows.append({
            "idx": position,
            "item_code": item.item_code,
            "item_name": item.get("item_name") or item.item_code,
            "spu": get_item_spu(item.item_code),
            "color_code": color.get("color_code") or "",
            "color": color.get("color_name") or "",
            "barcode": display.get("barcode") or "",
            "description": display.get("description") or "",
            "additional_notes": _get_pick_list_additional_notes(item),
            "qty": flt(item.get("qty")),
            "picked_qty": flt(item.get("picked_qty")),
            "uom": item.get("uom") or "",
            "warehouse": item.get("warehouse") or "",
        })
    return rows


def get_item_rows(doc):
    return _pick_list_rows(doc) if doc.doctype == "Pick List" else _wholesale_rows(doc)


def _selected_columns(doctype, columns):
    allowed = DOCTYPE_COLUMNS[doctype]
    if columns is None or columns == "":
        return list(allowed)
    if isinstance(columns, str):
        wanted = [value.strip() for value in columns.split(",")]
    else:
        wanted = [str(value).strip() for value in columns]
    selected = [key for key in allowed if key in wanted]
    if not selected:
        frappe.throw(_("请至少选择一列"))
    return selected


def _header_rows(doc):
    date = doc.get("posting_date") or doc.get("transaction_date") or str(doc.get("creation") or "")[:10]
    customer = doc.get("customer_name") or doc.get("customer") or ""
    status = doc.get("status") or {0: _("草稿"), 1: _("已提交"), 2: _("已取消")}.get(doc.docstatus, "")
    rows = [(_("单据类型"), doc.doctype), (_("单号"), doc.name)]
    if date:
        rows.append((_("日期"), str(date)))
    if customer:
        rows.append((_("客户"), customer))
    if status:
        rows.append((_("状态"), str(status)))
    return [list(row) for row in rows]


def _cell(value, key):
    if value is None or value == "":
        return ""
    if key in NUMERIC_COLUMNS:
        number = flt(value)
        return int(number) if float(number).is_integer() else round(number, 6)
    return str(value)


def _total_row(rows, columns):
    total = ["" for _column in columns]
    for index, key in enumerate(columns):
        if key in ("qty", "picked_qty", "ordered_qty", "delivered_before_qty", "remaining_qty"):
            total[index] = round(sum(flt(row.get(key)) for row in rows), 6)
        elif key == "amount":
            total[index] = round(sum(flt(row.get(key)) for row in rows), 2)
    if total and total[0] == "":
        total[0] = _("合计")
    return total


def build_table(doc, columns=None, include_header=1, include_total=1):
    """Rows ready for xlsx/csv: [[...], ...] with a header block and a totals row."""
    selected = _selected_columns(doc.doctype, columns)
    rows = get_item_rows(doc)
    table = []
    if cint(include_header):
        table.extend(_header_rows(doc))
        table.append([])
    table.append([_(LABELS[key]) for key in selected])
    for row in rows:
        table.append([_cell(row.get(key), key) for key in selected])
    if cint(include_total):
        table.append(_total_row(rows, selected))
    return table


def _send_csv(table, filename):
    from frappe.desk.utils import provide_binary_file

    buffer = io.StringIO()
    writer = csv.writer(buffer, lineterminator="\r\n")
    for row in table:
        writer.writerow(["" if cell is None else cell for cell in row])
    # BOM 让 Excel 正确识别中文；内容为 UTF-8
    provide_binary_file(filename, "csv", ("\ufeff" + buffer.getvalue()).encode("utf-8"))


def _send_xlsx(table, filename):
    from frappe.utils.xlsxutils import build_xlsx_response

    build_xlsx_response([[("" if cell is None else cell) for cell in row] for row in table], filename)


@frappe.whitelist()
def get_export_options(doctype):
    """列选择面板的数据：可用列、默认勾选、可下载格式。"""
    _require_doctype(doctype)
    return {
        "columns": [
            {"key": key, "label": _(LABELS[key]), "numeric": key in NUMERIC_COLUMNS}
            for key in DOCTYPE_COLUMNS[doctype]
        ],
        "defaults": (
            ["idx", "item_code", "item_name", "qty", "uom", "additional_notes"]
            if doctype == "Pick List"
            else [
                key for key in DOCTYPE_COLUMNS[doctype]
                if key not in ("ordered_qty", "delivered_before_qty", "remaining_qty", "picked_qty", "additional_notes", "spu")
            ]
        ),
        "formats": [
            {"value": "xlsx", "label": _("Excel (.xlsx)")},
            {"value": "csv", "label": _("CSV (.csv)")},
        ],
    }


@frappe.whitelist()
def export_document_table(doctype, name, columns=None, fmt="xlsx", include_header=1, include_total=1):
    """下载单据明细表格：fmt=xlsx（默认）或 csv。"""
    doc = get_export_document(doctype, name)
    table = build_table(doc, columns, include_header, include_total)
    filename = "-".join([frappe.scrub(doctype).replace("_", "-"), doc.name, nowdate()])
    if str(fmt or "").lower() == "csv":
        _send_csv(table, filename)
    else:
        _send_xlsx(table, filename)
    return filename


def _safe_sales_order_filename(value):
    value = re.sub(r'[<>:"/\\|?*\x00-\x1f]+', "_", str(value or "")).strip(" .")
    return value[:100] or "未命名"


def _with_solua_bulk_pdf_margins(doctype, print_format, options):
    """补齐原生批量 PDF 未传递的 A4 四边距，保持标准格式原样。"""
    doctypes = set(doctype) if isinstance(doctype, dict) else {doctype}
    if not doctypes & SOLUA_BULK_PDF_DOCTYPES:
        return options

    if not print_format and len(doctypes) == 1:
        print_format = frappe.get_meta(next(iter(doctypes))).default_print_format
    if not print_format or frappe.db.get_value("Print Format", print_format, "module") != "Solua Wholesale":
        return options

    parsed = frappe.parse_json(options) if options else {}
    if not isinstance(parsed, dict) or parsed.get("page-size") not in (None, "A4"):
        return options
    for key, value in SOLUA_PDF_MARGINS.items():
        parsed.setdefault(key, value)
    return frappe.as_json(parsed)


@frappe.whitelist()
def download_multi_pdf(
    doctype, name, format=None, no_letterhead=False, letterhead=None, options=None
):
    """调用 Frappe 原生批量 PDF，并为 Solua A4 格式补齐边距。"""
    from frappe.utils.print_format import download_multi_pdf as core_download_multi_pdf

    return core_download_multi_pdf(
        doctype,
        name,
        format,
        no_letterhead,
        letterhead,
        _with_solua_bulk_pdf_margins(doctype, format, options),
    )


@frappe.whitelist()
def download_multi_pdf_async(
    doctype, name, format=None, no_letterhead=False, letterhead=None, options=None
):
    """调用 Frappe 原生异步批量 PDF，并为 Solua A4 格式补齐边距。"""
    from frappe.utils.print_format import download_multi_pdf_async as core_download_multi_pdf_async

    return core_download_multi_pdf_async(
        doctype,
        name,
        format,
        no_letterhead,
        letterhead,
        _with_solua_bulk_pdf_margins(doctype, format, options),
    )


@frappe.whitelist()
def download_sales_order_pdfs(names):
    """分别生成销售订单 PDF，并以 ZIP 作为本地批量下载容器。"""
    from frappe.utils.pdf import get_pdf
    from solua_home.api.a4_designer import _active_print_format

    names = frappe.parse_json(names) if isinstance(names, str) else names
    if not isinstance(names, (list, tuple)) or not names:
        frappe.throw(_("请至少选择一个销售订单"))

    print_format = _active_print_format("Sales Order")
    if not print_format:
        frappe.throw(_("销售订单没有可用的打印格式"))

    archive = io.BytesIO()
    used_names = set()
    with ZipFile(archive, "w", ZIP_DEFLATED) as output:
        for name in names:
            doc = get_export_document("Sales Order", name)
            html = frappe.get_print("Sales Order", doc.name, print_format=print_format, as_pdf=False)
            pdf = get_pdf(html, {
                "page-size": "A4",
                **SOLUA_PDF_MARGINS,
            })
            date = str(doc.get("transaction_date") or nowdate()).replace("-", "")[:8]
            customer = _safe_sales_order_filename(doc.get("customer_name") or doc.get("customer"))
            filename = f"{date}_{_safe_sales_order_filename(doc.name)}_{customer}_客户确认单.pdf"
            if filename in used_names:
                filename = filename.replace(".pdf", f"_{len(used_names) + 1}.pdf")
            used_names.add(filename)
            output.writestr(filename, pdf)

    frappe.local.response.filename = f"销售订单客户确认单_{nowdate().replace('-', '')}.zip"
    frappe.local.response.filecontent = archive.getvalue()
    frappe.local.response.type = "download"
