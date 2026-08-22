# -*- coding: utf-8 -*-
"""POS 小票生成 API

根据零售参数设置生成小票 HTML：
- 支持 80mm / 58mm 纸宽
- 小票标题/页脚从零售参数读取
- 自动显示商品明细、合计、支付方式、找零
"""
import frappe
from frappe import _
import json


@frappe.whitelist()
def generate_receipt_html(invoice_name, paper_width="80mm"):
    """生成小票 HTML

    Args:
        invoice_name: Sales Invoice 名称
        paper_width: 纸宽 "80mm" 或 "58mm"
    """
    # 获取发票数据
    invoice = frappe.get_doc("Sales Invoice", invoice_name)
    if not invoice:
        frappe.throw(_("发票 {0} 不存在").format(invoice_name))

    # 获取零售参数
    settings = _get_retail_settings()

    # 纸宽对应的字体大小和间距
    is_80mm = paper_width == "80mm"
    font_size = "12px" if is_80mm else "10px"
    small_font = "10px" if is_80mm else "8px"
    line_width = "72mm" if is_80mm else "48mm"

    # 构建小票内容
    title1 = settings.get("receipt_title_1", "Solua Home")
    title2 = settings.get("receipt_title_2", "Lda")
    footer1 = settings.get("receipt_footer_1", "Obrigado pela preferência!")
    footer2 = settings.get("receipt_footer_2", "")
    footer3 = settings.get("receipt_footer_3", "www.solua.one")
    footer4 = settings.get("receipt_footer_4", "")

    # 抹零
    grand_total = invoice.grand_total or 0
    rounding_method = settings.get("rounding_method", "不处理")
    rounded_total = _apply_rounding(grand_total, rounding_method)

    # 支付方式
    payments = []
    for p in invoice.payments:
        payments.append({
            "method": p.mode_of_payment,
            "amount": p.amount,
        })

    # 构建 HTML
    items_html = ""
    for item in invoice.items:
        qty = item.qty or 0
        rate = item.rate or 0
        amount = item.amount or 0
        item_name = item.item_name or item.item_code
        # 截断过长名称
        max_name_len = 18 if is_80mm else 14
        if len(item_name) > max_name_len:
            item_name = item_name[:max_name_len-1] + "…"

        items_html += f"""
        <div style="display:flex;justify-content:space-between;margin:2px 0;">
            <span>{item_name}</span>
        </div>
        <div style="display:flex;justify-content:space-between;margin:1px 0;font-size:{small_font};color:#666;">
            <span>  {qty} × {rate:,.2f}</span>
            <span>{amount:,.2f}</span>
        </div>"""

    payments_html = ""
    for p in payments:
        payments_html += f"""
        <div style="display:flex;justify-content:space-between;margin:2px 0;">
            <span>{p['method']}</span>
            <span>{p['amount']:,.2f}</span>
        </div>"""

    change = 0
    if payments:
        total_paid = sum(p["amount"] for p in payments)
        change = total_paid - rounded_total

    # 完整小票
    html = f"""<!DOCTYPE html>
<html>
<head>
<meta charset="utf-8">
<style>
@media print {{
    @page {{ margin: 2mm; size: {paper_width} auto; }}
    body {{ margin: 0; padding: 0; width: {paper_width}; }}
}}
body {{
    font-family: 'Courier New', monospace;
    font-size: {font_size};
    width: {paper_width};
    padding: 2mm;
    box-sizing: border-box;
}}
.receipt {{ width: 100%; }}
.title {{ text-align: center; font-weight: bold; font-size: {font_size}; }}
.subtitle {{ text-align: center; font-size: {small_font}; }}
.separator {{ border-top: 1px dashed #000; margin: 3px 0; }}
.item-row {{ display: flex; justify-content: space-between; }}
.footer {{ text-align: center; font-size: {small_font}; margin-top: 4px; }}
</style>
</head>
<body>
<div class="receipt">
    <!-- 标题 -->
    <div class="title">{title1}</div>
    <div class="subtitle">{title2}</div>
    <div class="separator"></div>

    <!-- 发票信息 -->
    <div style="font-size:{small_font};">
        <div>Nº: {invoice.name}</div>
        <div>Data: {frappe.utils.formatdate(invoice.posting_date, 'dd/MM/yyyy')}</div>
        <div>Hora: {str(invoice.posting_time)[:5]}</div>
        <div>Caixa: {invoice.owner or ''}</div>
    </div>
    <div class="separator"></div>

    <!-- 商品明细 -->
    {items_html}
    <div class="separator"></div>

    <!-- 合计 -->
    <div style="display:flex;justify-content:space-between;font-weight:bold;">
        <span>TOTAL</span>
        <span>{grand_total:,.2f} MT</span>
    </div>"""

    if rounding_method != "不处理" and rounded_total != grand_total:
        html += f"""
    <div style="display:flex;justify-content:space-between;font-size:{small_font};">
        <span>Arredondamento ({rounding_method})</span>
        <span>{rounded_total:,.2f} MT</span>
    </div>"""

    html += f"""
    <div class="separator"></div>

    <!-- 支付方式 -->
    {payments_html}"""

    if change > 0:
        html += f"""
    <div style="display:flex;justify-content:space-between;font-weight:bold;">
        <span>Troco</span>
        <span>{change:,.2f} MT</span>
    </div>"""

    html += f"""
    <div class="separator"></div>

    <!-- 页脚 -->
    <div class="footer">
        <div>{footer1}</div>
        <div>{footer2}</div>
        <div>{footer3}</div>
        <div>{footer4}</div>
    </div>
</div>
</body>
</html>"""

    return {"html": html, "paper_width": paper_width}


@frappe.whitelist()
def get_receipt_templates():
    """获取可用的小票模板列表"""
    templates = frappe.get_all(
        "Print Format",
        filters={"doc_type": "Sales Invoice", "disabled": 0},
        fields=["name", "module"],
        order_by="name",
    )
    # 添加预设模板
    presets = [
        {"name": "小票 80mm", "module": "预设模板", "paper_width": "80mm"},
        {"name": "小票 58mm", "module": "预设模板", "paper_width": "58mm"},
    ]
    return {"templates": templates, "presets": presets}


def _get_retail_settings():
    """获取零售参数"""
    if frappe.db.exists("DocType", "Retail Settings"):
        settings = frappe.get_single("Retail Settings")
        return {
            "receipt_title_1": getattr(settings, "receipt_title_1", "Solua Home"),
            "receipt_title_2": getattr(settings, "receipt_title_2", "Lda"),
            "receipt_footer_1": getattr(settings, "receipt_footer_1", "Obrigado pela preferência!"),
            "receipt_footer_2": getattr(settings, "receipt_footer_2", ""),
            "receipt_footer_3": getattr(settings, "receipt_footer_3", "www.solua.one"),
            "receipt_footer_4": getattr(settings, "receipt_footer_4", ""),
            "print_copies": getattr(settings, "print_copies", 1),
            "rounding_method": getattr(settings, "rounding_method", "不处理"),
            "receipt_format": getattr(settings, "receipt_format", "条码+品名+数量+单价+小计"),
        }
    return {
        "receipt_title_1": "Solua Home",
        "receipt_title_2": "Lda",
        "receipt_footer_1": "Obrigado pela preferência!",
        "receipt_footer_2": "",
        "receipt_footer_3": "www.solua.one",
        "receipt_footer_4": "",
        "print_copies": 1,
        "rounding_method": "不处理",
        "receipt_format": "条码+品名+数量+单价+小计",
    }


def _apply_rounding(amount, method):
    """按抹零方式处理金额"""
    import math
    if method == "不处理":
        return amount
    elif method == "四舍五入到角":
        return round(amount, 1)
    elif method == "四舍五入到元":
        return round(amount)
    elif method == "舍去分":
        return math.floor(amount * 100) / 100
    elif method == "舍去角":
        return math.floor(amount * 10) / 10
    return amount
