# solua_home/api/sales.py
# ============================
# 销售模块的自定义验证和事件处理
# ============================

import csv
import io
import json
import re
from decimal import Decimal, InvalidOperation

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

    # Keep the row field readable in the form while the print snapshot uses
    # the same live resolver. Never copy item_code into the barcode field.
    from solua_home.printing.wholesale import get_item_sales_display

    for item in doc.get("items", []):
        if not item.get("item_code"):
            continue
        display = get_item_sales_display(item.item_code, item.get("description"))
        if frappe.get_meta("Sales Order Item").has_field("custom_item_barcode"):
            item.custom_item_barcode = display["barcode"]
        if display["description"]:
            item.description = display["description"]

    # 交货日期只需不早于销售单日期；不要求提前若干天。
    if doc.delivery_date and doc.transaction_date:
        from frappe.utils import getdate

        if getdate(doc.delivery_date) < getdate(doc.transaction_date):
            frappe.throw(_("交货日期不能早于销售单日期"))


@frappe.whitelist()
def get_sales_order_item_display(item_code):
    """Return only the real barcode and clean sales description for a row."""
    from solua_home.printing.wholesale import get_item_sales_display

    return get_item_sales_display(item_code)


# Sales-order-only import/selection helpers.  The resolver deliberately calls
# ERPNext's get_item_details() so price rules, UOM conversion and item defaults
# remain owned by ERPNext rather than being copied here.
_UPLOAD_COLUMN_ALIASES = {
    "itemcode": "item_code", "itemno": "item_code", "itemnumber": "item_code",
    "sku": "item_code", "code": "item_code", "item": "item_code",
    "货号": "item_code", "物料": "item_code", "物料编码": "item_code", "物料号": "item_code",
    "料号": "item_code", "产品编码": "item_code", "产品编号": "item_code",
    "商品编号": "item_code", "商品编码": "item_code", "商品代码": "item_code",
    "qty": "qty", "quantity": "qty", "salesqty": "qty", "orderedqty": "qty",
    "数量": "qty", "数量条": "qty", "订购数量": "qty", "订单数量": "qty", "销售数量": "qty", "件数": "qty",
    "warehouse": "warehouse", "仓库": "warehouse", "库位": "warehouse",
}


def _json_value(value):
    if isinstance(value, str):
        return frappe.parse_json(value) if value.strip() else {}
    return value or {}


def _header_key(value):
    text = str(value or "").strip().lower()
    text = re.sub(r"[\s_\-./\\()（）【】\[\]:：]+", "", text)
    return _UPLOAD_COLUMN_ALIASES.get(text)


def _positive_integer(value):
    if value is None or isinstance(value, bool):
        return None
    try:
        number = Decimal(str(value).strip().replace(",", ""))
        if not number.is_finite() or number <= 0 or number != number.to_integral_value():
            return None
        return int(number)
    except (InvalidOperation, ValueError, TypeError):
        return None


def _merge_input_rows(rows):
    merged = {}
    errors = []
    for index, row in enumerate(rows or [], start=1):
        row = row or {}
        row_number = row.get("_row", index)
        item_code = str(row.get("item_code") or row.get("sku") or "").strip()
        qty = _positive_integer(row.get("qty") or row.get("quantity"))
        warehouse = str(row.get("warehouse") or "").strip()
        if not item_code:
            errors.append({"row": row_number, "item_code": "", "error": "缺少货号/SKU"})
            continue
        if qty is None:
            errors.append({"row": row_number, "item_code": item_code, "error": "数量必须为正整数"})
            continue
        key = (item_code, warehouse)
        if key not in merged:
            merged[key] = {"item_code": item_code, "qty": 0, "warehouse": warehouse, "source_rows": []}
        merged[key]["qty"] += qty
        merged[key]["source_rows"].append(row_number)
    return list(merged.values()), errors


def _parse_table_rows(table):
    rows = [list(row) for row in (table or []) if any(str(cell or "").strip() for cell in row)]
    if not rows:
        return [], [{"row": 1, "item_code": "", "error": "文件没有可读取的行"}]

    header = {_header_key(value): index for index, value in enumerate(rows[0]) if _header_key(value)}
    has_header = "item_code" in header or "qty" in header
    if has_header:
        missing = [label for field, label in (("item_code", "货号/SKU"), ("qty", "数量")) if field not in header]
        if missing:
            actual = "、".join(str(value) for value in rows[0])
            return [], [{"row": 1, "item_code": "", "error": f"缺少列：{'、'.join(missing)}；实际表头：{actual}。支持：货号/SKU、数量"}]
        code_index, qty_index = header["item_code"], header["qty"]
        warehouse_index = header.get("warehouse")
        data_rows = rows[1:]
        start_row = 2
    elif len(rows[0]) >= 2 and _positive_integer(rows[0][1]) is not None:
        # Also accept a headerless two-column export: SKU in column A, qty in B.
        code_index, qty_index, warehouse_index = 0, 1, None
        data_rows = rows
        start_row = 1
    else:
        actual = "、".join(str(value) for value in rows[0])
        return [], [{"row": 1, "item_code": "", "error": f"未识别到有效列；实际表头：{actual}。支持：货号/SKU、数量"}]

    parsed = []
    for row_number, row in enumerate(data_rows, start=start_row):
        parsed.append({
            "item_code": row[code_index] if code_index < len(row) else "",
            "qty": row[qty_index] if qty_index < len(row) else "",
            "warehouse": row[warehouse_index] if warehouse_index is not None and warehouse_index < len(row) else "",
            "_row": row_number,
        })
    merged, errors = _merge_input_rows(parsed)
    return merged, errors


def _read_order_table(file_url):
    file_doc = frappe.get_doc("File", {"file_url": file_url})
    extension = (file_doc.get_extension()[1] or "").lower().lstrip(".")
    if extension not in {"csv", "xlsx", "xls"}:
        frappe.throw(_("只支持 CSV、XLSX 或 XLS 文件"))
    content = file_doc.get_content()
    if extension == "csv":
        text, encoding = _decode_csv_content(content)
        table, delimiter = _parse_csv_text(text, encoding)
        return table, {"encoding": encoding, "delimiter": repr(delimiter)}
    from frappe.utils.xlsxutils import read_xlsx_file_from_attached_file

    if extension == "xlsx":
        return read_xlsx_file_from_attached_file(fcontent=content), None
    from frappe.utils.xlsxutils import read_xls_file_from_attached_file

    return read_xls_file_from_attached_file(content), None


def _parse_csv_text(text, encoding):
    try:
        delimiter = csv.Sniffer().sniff(text[:8192], delimiters=",;\t").delimiter
    except csv.Error:
        first_line = next(iter(text.splitlines()), "")
        counts = {char: first_line.count(char) for char in ",;\t"}
        delimiter = max(counts, key=counts.get) if counts and max(counts.values()) else ","
    try:
        table = list(csv.reader(io.StringIO(text, newline=""), delimiter=delimiter))
    except csv.Error as exc:
        frappe.throw(_("CSV 格式错误（编码：{0}，分隔符：{1}）：{2}").format(encoding, repr(delimiter), str(exc)))
    if table:
        table[0] = [str(value).strip().lstrip("\ufeff").strip() for value in table[0]]
    return table, delimiter


def _decode_csv_content(content):
    if isinstance(content, str):
        text = content
        if _has_upload_headers(text):
            return text, "UTF-8 text"
        # Some file readers decode GBK bytes as Windows-1250 text before this
        # parser receives them. Recover the original bytes only when the
        # round-trip produces both required upload headers.
        try:
            recovered = content.encode("cp1250").decode("gb18030")
        except (UnicodeEncodeError, UnicodeDecodeError):
            recovered = ""
        if recovered and _has_upload_headers(recovered):
            return recovered, "GB18030/GBK (recovered from Windows-1250 text)"
        content = content.encode("utf-8")
    try:
        text = content.decode("utf-8-sig")
        encoding = "UTF-8 BOM" if content.startswith(b"\xef\xbb\xbf") else "UTF-8"
    except UnicodeDecodeError:
        try:
            text = content.decode("gb18030")
            encoding = "GB18030/GBK"
        except UnicodeDecodeError:
            frappe.throw(_("CSV 解码失败（已尝试 UTF-8 和 GB18030/GBK）；文件内容不是受支持的编码。"))
    return text, encoding


def _has_upload_headers(text):
    try:
        delimiter = csv.Sniffer().sniff(text[:8192], delimiters=",;\t").delimiter
    except csv.Error:
        first_line = next(iter(text.splitlines()), "")
        counts = {char: first_line.count(char) for char in ",;\t"}
        delimiter = max(counts, key=counts.get) if counts and max(counts.values()) else ","
    try:
        header = next(csv.reader([next(iter(text.splitlines()), "")], delimiter=delimiter))
    except (csv.Error, StopIteration):
        return False
    keys = {_header_key(value.strip().lstrip("\ufeff")) for value in header}
    return "item_code" in keys and "qty" in keys


def _sales_context(context):
    context = frappe._dict(_json_value(context))
    context.doctype = "Sales Order"
    context.parenttype = "Sales Order"
    context.transaction_date = context.get("transaction_date") or context.get("posting_date") or frappe.utils.nowdate()
    context.selling_price_list = context.get("selling_price_list") or context.get("price_list") or ""
    context.price_list = context.get("price_list") or context.selling_price_list
    context.company = context.get("company") or ""
    context.customer = context.get("customer") or ""
    context.set_warehouse = context.get("set_warehouse") or ""
    context.conversion_rate = context.get("conversion_rate") or 1
    context.plc_conversion_rate = context.get("plc_conversion_rate") or 1
    context.ignore_pricing_rule = cint(context.get("ignore_pricing_rule") or 0)
    return context


def _native_sales_item_details(item_code, context, qty=1, warehouse=None, price_list=None):
    from erpnext.stock.get_item_details import get_item_details

    ctx = frappe._dict(context.copy())
    ctx.update({
        "doctype": "Sales Order", "parenttype": "Sales Order", "child_doctype": "Sales Order Item",
        "item_code": item_code, "qty": qty, "warehouse": warehouse or ctx.get("warehouse") or None,
        "child_docname": None,
    })
    if price_list is not None:
        ctx.price_list = price_list
        ctx.selling_price_list = price_list
    return frappe._dict(get_item_details(ctx, None, for_validate=False, overwrite_warehouse=False))


def _item_master(item_code):
    return frappe.db.get_value(
        "Item", item_code,
        ["name", "item_name", "item_group", "variant_of", "has_variants", "disabled", "is_stock_item"],
        as_dict=True,
    )


def _display_price(item_code, context, price_list, warehouse=None):
    if not price_list:
        return 0
    try:
        details = _native_sales_item_details(item_code, context, warehouse=warehouse, price_list=price_list)
        return flt(details.get("price_list_rate") or details.get("rate"))
    except Exception:
        return 0


def _resolve_sales_item(input_row, context, strict=True):
    item_code = str(input_row.get("item_code") or "").strip()
    errors = []
    master = _item_master(item_code) if item_code else None
    if not master:
        return None, [{"row": input_row.get("source_rows", [None])[0], "item_code": item_code, "error": "物料不存在"}]
    if cint(master.get("disabled")):
        errors.append("物料已停用")
    if cint(master.get("has_variants")):
        errors.append("模板物料不能直接下单，请选择颜色变体")

    context_warehouse = input_row.get("warehouse") or context.get("set_warehouse") or None
    try:
        details = _native_sales_item_details(item_code, context, input_row.get("qty", 1), context_warehouse)
    except Exception as exc:
        details = frappe._dict()
        errors.append(str(exc)[:240] or "ERPNext 商品详情读取失败")

    warehouse = context_warehouse or details.get("warehouse") or ""
    rate = flt(details.get("rate") or details.get("price_list_rate"))
    price_list_rate = flt(details.get("price_list_rate") or rate)
    if rate <= 0 and price_list_rate <= 0:
        errors.append("当前销售价格表没有有效价格")
    if cint(master.get("is_stock_item")) and not warehouse:
        errors.append("没有默认仓库或订单仓库")

    actual_qty = reserved_qty = available_qty = 0
    if warehouse:
        from erpnext.stock.get_item_details import get_bin_details

        bin_details = get_bin_details(item_code, warehouse, context.get("company"), include_child_warehouses=True)
        actual_qty = flt(bin_details.get("actual_qty"))
        reserved_qty = flt(bin_details.get("reserved_qty"))
        available_qty = actual_qty - reserved_qty

    try:
        from solua_home.printing.color_card import get_item_color_info
        from solua_home.printing.wholesale import get_item_sales_display

        display = get_item_sales_display(item_code, details.get("description"))
        color = get_item_color_info(item_code)
    except Exception:
        display = {"barcode": "", "description": details.get("description") or ""}
        color = {}

    row = {
        "item_code": item_code,
        "item_name": details.get("item_name") or master.get("item_name") or item_code,
        "description": display.get("description") or details.get("description") or "",
        "qty": input_row.get("qty", 1),
        "uom": details.get("uom") or details.get("stock_uom") or "",
        "stock_uom": details.get("stock_uom") or "",
        "conversion_factor": flt(details.get("conversion_factor") or 1),
        "rate": rate,
        "price_list_rate": price_list_rate,
        "warehouse": warehouse,
        "custom_item_barcode": display.get("barcode") or "",
        "barcode": display.get("barcode") or "",
        "order_code": color.get("order_code") or item_code,
        "color_code": color.get("color_code") or "",
        "color": color.get("color_name") or "",
        "image": color.get("image") or "",
        "template_code": color.get("template_code") or master.get("variant_of") or "",
        "actual_qty": actual_qty,
        "reserved_qty": reserved_qty,
        "available_qty": available_qty,
        "wholesale_rate": _display_price(item_code, context, "Wholesale Selling", warehouse),
        "standard_selling_rate": _display_price(item_code, context, "Standard Selling", warehouse),
        "errors": errors,
    }
    if errors and strict:
        return None, [{"row": input_row.get("source_rows", [None])[0], "item_code": item_code, "error": "；".join(errors)}]
    return row, ([{"row": input_row.get("source_rows", [None])[0], "item_code": item_code, "error": "；".join(errors)}] if errors else [])


def _resolve_sales_rows(rows, context, strict=True):
    context = _sales_context(context)
    normalized, errors = _merge_input_rows(rows)
    resolved = []
    for input_row in normalized:
        row, row_errors = _resolve_sales_item(input_row, context, strict=strict)
        if row:
            resolved.append(row)
        errors.extend(row_errors)
    return {"rows": resolved, "errors": errors, "summary": {"valid": len(resolved), "errors": len(errors)}}


@frappe.whitelist()
def preview_sales_order_upload(file_url, context=None):
    """Parse an attached CSV/XLSX/XLS and return an unsaved enriched preview."""
    table, source_info = _read_order_table(file_url)
    parsed, errors = _parse_table_rows(table)
    if source_info and errors:
        actual = "、".join(str(value) for value in table[0]) if table else "（空）"
        for error in errors:
            error["error"] = f"{error['error']}（实际表头：{actual}；编码：{source_info['encoding']}；分隔符：{source_info['delimiter']}；支持：货号/SKU、数量）"
    result = _resolve_sales_rows(parsed, context, strict=True)
    result["errors"] = errors + result["errors"]
    result["summary"]["errors"] = len(result["errors"])
    return result


@frappe.whitelist()
def preview_sales_order_paste(text, context=None):
    """Resolve two pasted columns (货号/SKU + 数量) without saving anything."""
    lines = [line for line in str(text or "").splitlines() if line.strip()]
    table = []
    for line in lines:
        delimiter = "\t" if "\t" in line else "," if "," in line else ";" if ";" in line else None
        table.append(line.split(delimiter) if delimiter else re.split(r"\s+", line.strip()))
    parsed, errors = _parse_table_rows(table)
    result = _resolve_sales_rows(parsed, context, strict=True)
    result["errors"] = errors + result["errors"]
    result["summary"]["errors"] = len(result["errors"])
    return result


@frappe.whitelist()
def preview_sales_order_rows(rows, context=None):
    """Re-resolve selected rows through the same native ERPNext item-detail path."""
    rows = _json_value(rows)
    return _resolve_sales_rows(rows, context, strict=True)


@frappe.whitelist()
def get_sales_order_color_variants(barcode, context=None):
    """Return one shared-barcode template's sellable variants with native order details."""
    from solua_home.api.home import get_color_variants

    context = _sales_context(context)
    result = get_color_variants(barcode=barcode, barcode_only=True)
    if result.get("state") != "ok":
        return {"state": result.get("state") or "no_data", "templates": [], "variants": []}

    rows = []
    errors = []
    template_groups = result.get("templates") or []
    has_template = any(group.get("template", {}).get("has_variants") for group in template_groups)
    warehouse = context.get("set_warehouse") or None
    for group in template_groups:
        for variant in group.get("variants") or []:
            row, row_errors = _resolve_sales_item(
                {"item_code": variant.get("item_code"), "qty": 1, "warehouse": warehouse},
                context,
                strict=False,
            )
            if row:
                row["name"] = variant.get("name") or variant.get("item_code")
                row["color_code"] = variant.get("color_code") or row.get("color_code") or ""
                row["color"] = variant.get("color") or row.get("color") or ""
                row["image"] = variant.get("image") or row.get("image") or ""
                row["status"] = "；".join(error["error"] for error in row_errors) if row_errors else ""
                rows.append(row)
            errors.extend(row_errors)
    return {
        "state": "ok" if rows else "no_data",
        "has_template": has_template,
        "templates": template_groups,
        "variants": rows,
        "errors": errors,
    }


@frappe.whitelist()
def search_sales_order_items(context=None, filters=None):
    """Search selectable stock items and show live Bin/prices for an order."""
    context = _sales_context(context)
    filters = frappe._dict(_json_value(filters))
    if not context.company:
        return {"items": [], "errors": ["请先选择公司"]}
    item_filters = {"disabled": 0, "has_variants": 0}
    if filters.get("item_group"):
        item_filters["item_group"] = filters.item_group
    if filters.get("template"):
        item_filters["variant_of"] = filters.template
    fields = ["name", "item_name", "item_group", "variant_of", "has_variants", "disabled", "is_stock_item"]
    for field in ("custom_order_code", "custom_swatch_image", "image"):
        if frappe.get_meta("Item").has_field(field):
            fields.append(field)
    query = str(filters.get("search") or "").strip()
    or_filters = None
    if query:
        like = f"%{query}%"
        or_filters = [[field, "like", like] for field in ("name", "item_name", "custom_order_code") if field in fields]
    items = frappe.get_all("Item", filters=item_filters, or_filters=or_filters, fields=fields, limit=100, order_by="name asc")
    results = []
    color_query = str(filters.get("color") or "").strip().lower()
    for item in items:
        row, row_errors = _resolve_sales_item({"item_code": item.name, "qty": 1, "warehouse": filters.get("warehouse") or context.get("set_warehouse")}, context, strict=False)
        if not row:
            continue
        if color_query and color_query not in f"{row.get('color','')} {row.get('color_code','')}".lower():
            continue
        if cint(filters.get("in_stock")) and flt(row.get("available_qty")) <= 0:
            continue
        row["status"] = "；".join(error["error"] for error in row_errors) if row_errors else ""
        results.append(row)
    return {"items": results, "errors": [], "warehouse": filters.get("warehouse") or context.get("set_warehouse") or ""}


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
