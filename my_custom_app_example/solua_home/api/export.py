"""销售订单 / 销售单 / 交货单 / 拣货单：把单据明细导出成表格（Excel / CSV）。

导出列与打印表格保持一致（货号、色号、条码、描述、数量、单价、金额、仓库），
并在底部给出数量合计，方便仓管、客户与财务直接拿去用表格处理；图片列不导出。

入口（均为 GET 可调用，浏览器打开链接即下载）：
    /api/method/solua_home.api.export.export_document_table?doctype=..&name=..&fmt=xlsx
"""

import csv
import io

import frappe
from frappe import _
from frappe.utils import cint, flt, nowdate

EXPORT_DOCTYPES = ("Sales Order", "Sales Invoice", "Delivery Note", "Pick List")

# 列顺序 = 导出/勾选面板的显示顺序
COLUMN_LABELS = (
    ("idx", "序号"),
    ("item_code", "货号"),
    ("item_name", "商品名称"),
    ("order_code", "订货货号"),
    ("color_code", "色号"),
    ("color", "颜色"),
    ("barcode", "条码"),
    ("description", "描述"),
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
    "idx", "item_code", "item_name", "order_code", "color_code", "color", "barcode", "description",
    "qty", "uom", "rate", "amount", "warehouse",
)
DOCTYPE_COLUMNS = {
    "Sales Order": _WHOLESALE_COLUMNS,
    "Sales Invoice": _WHOLESALE_COLUMNS,
    "Delivery Note": _WHOLESALE_COLUMNS + ("ordered_qty", "delivered_before_qty", "remaining_qty"),
    # 拣货单没有价格与订单关联，只导出拣货数量、仓库与商品信息
    "Pick List": (
        "idx", "item_code", "item_name", "color_code", "color", "barcode", "description",
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
    from solua_home.printing.wholesale import get_item_sales_display

    rows = []
    entries = doc.get("locations") or doc.get("items") or []
    for position, item in enumerate(entries, start=1):
        color = get_item_color_info(item.item_code) or {}
        display = get_item_sales_display(item.item_code, item.get("description"))
        rows.append({
            "idx": position,
            "item_code": item.item_code,
            "item_name": item.get("item_name") or item.item_code,
            "color_code": color.get("color_code") or "",
            "color": color.get("color_name") or "",
            "barcode": display.get("barcode") or "",
            "description": display.get("description") or "",
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
        "defaults": [
            key for key in DOCTYPE_COLUMNS[doctype]
            if key not in ("ordered_qty", "delivered_before_qty", "remaining_qty", "picked_qty")
        ],
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
