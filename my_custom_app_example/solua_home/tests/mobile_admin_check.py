from pathlib import Path

from jinja2 import Environment


ROOT = Path(__file__).resolve().parents[1]
api = (ROOT / "api" / "mobile.py").read_text(encoding="utf-8")
totals_api = (ROOT / "api" / "business_totals.py").read_text(encoding="utf-8")
page = (ROOT / "www" / "mobile" / "index.html").read_text(encoding="utf-8")
page_context = (ROOT / "www" / "mobile" / "index.py").read_text(encoding="utf-8")
manifest = (ROOT / "public" / "mobile" / "manifest.json").read_text(encoding="utf-8")
manifest_order = (ROOT / "public" / "mobile" / "manifest-order.json").read_text(encoding="utf-8")
manifest_sales = (ROOT / "public" / "mobile" / "manifest-sales.json").read_text(encoding="utf-8")

Environment().parse(page)

assert "System Manager" in api and "get_sales_order_color_variants" in api
assert "search_sales_order_items" in api and "Wholesale Selling 3" in api
assert "def search_customers" in api and "def list_customers" in api and "def get_customer_addresses" in api and "def save_sales_order" in api
assert "def list_sales_orders" in api and "def _customer_price_list" in api
assert "def _sales_order_relations_batch" in api and "_sales_order_relations_batch(names" in api
assert "def search_item_suggestions" in api and 'solua_home.api.mobile.search_item_suggestions' in page
assert "exact_item_or_filters" in api and 'filters={"barcode": query}' in api
assert "def get_mobile_reports" in api and "business_totals" in api
assert "def create_delivery_note" in api and "def create_sales_invoice" in api and "def create_pick_list" in api
assert "available_sales_qty" in (ROOT / "api" / "sales.py").read_text(encoding="utf-8")
assert "def get_customer_form_options" in api and "def create_customer" in api
assert 'frappe.new_doc("Address")' in api and 'frappe.new_doc("Contact")' in api
assert "solua_home.api.mobile.lookup" in page
assert "单价" in page and "适用单价" not in page and "批发价 1 级" not in page and "批发价 3 级" not in page
assert "new URLSearchParams" in page and "async function writeCall" in page
assert "mobile-suggestions" in page and "suggestionTimer" in page
assert "BarcodeDetector" in page and '"start_url": "/mobile?view=stock"' in manifest
assert "zxing-browser.min.js" in page and "ZXingBrowser" in page and "getUserMedia" in page
assert 'manifest{% if mobile_order %}-order{% elif mobile_sales %}-sales' in page
assert '"start_url": "/mobile?view=order"' in manifest_order
assert '"start_url": "/mobile?view=sales"' in manifest_sales
assert "cameraBusy" in page and "已识别，可继续扫描" in page and "keepCamera: true" in page
assert "请在上方手动输入条码、货号或名称" in page and "请检查权限；也可以在上方手动输入条码、货号或名称" in page
assert "grid-template-columns: repeat(auto-fit, minmax(210px, 1fr))" in page
assert "white-space: nowrap" in page and ".mobile-card-label" in page and ".mobile-card-actions button" in page
assert "mobile-detail-grid" in page and "mobile-order-grid" in page and "data-mobile-product-view" in page
assert "mobile_stock" in page and 'mobile_order or mobile_sales or mobile_stock' in page and "solua-mobile-stock-product-view" in page
assert '{% if mobile_order or mobile_sales %}单列详情{% else %}单列{% endif %}' in page and '{% if mobile_order or mobile_sales %}双列下单{% else %}双列{% endif %}' in page
assert '#mobile-new-sales-order[open]' in page and 'overflow: visible' in page
assert "mobile-cart-icon" in page and 'aria-label="加入购物车"' in page and 'data-add-code=' in page
assert "mobile-cart-note" in page and "data-cart-note-code" in page and 'notes: row.notes || ""' in page
assert "solua-mobile-sales-draft-v1" in page and "mobile-draft-recovery" in page and "restoreDraft" in page
assert "重新检查库存与价格" in page and "已恢复销售订单草稿" in page and "clearSavedDraft" in page
assert 'mobile-draft-recovery-actions' in page and '</div>\n    {% endif %}\n    <div class="mobile-panel mobile-order-only"' in page
assert 'def _apply_order_data(doc, context, address, resolved_rows, notes="")' in api and '"notes": str(row.get("notes") or "").strip()' in api and "additional_notes" in api
assert "grid-template-columns: 1fr 1fr;" not in page.split(".mobile-grid", 1)[1].split(".mobile-card", 1)[0]
assert "mobile_order" in page_context and "view" in page_context
assert "mobile-order-only" in page and "view=sales" in page
assert "mobile_customer" in page_context and "view=customer" in page
assert "mobile_stock" in page_context and 'view == "stock"' in page_context
assert "data-solua-mobile-nav" in page and "dropdown-menu" in page and "solua-mobile-page" in page
assert "mobile-user-menu" not in page
assert "/mobile?view=stock" in page
assert '{% if mobile_sales or mobile_order %}' in page and 'id="mobile-stock-settings"' in page
assert 'id="mobile-stock-settings"' in page and 'id="mobile-order-settings-summary"' in page
assert "精确搜索变体货号" in page and "模糊搜索货号" not in page
assert "客户中心" in page and "mobile-customers-list" in page and "mobile-customer-form" in page and "mobile-new-customer-tax-id" in page
assert "mobile-new-customer-address" in page and "mobile-new-customer-phone" in page
assert "view=order&customer=" in page and "view=orders&customer=" in page and "customerFromUrl" in page
assert 'await chooseCustomer(customer);' in page and 'window.soluaMobileOpenDetails("mobile-new-sales-order");' in page
assert "支持 Google / QQ" in page and "Google 或 QQ 地图链接" in page
assert "solua-mobile-delivery-route-v1" in page and "restoreRouteDraft" in page and "已恢复上次配送路线草稿" in page
assert '当前处于离线状态，草稿仍保留在本机，联网后可继续提交' in page and '网络已断开，当前开单草稿已保留' in page
assert 'mobile-section-collapse' in page and 'mobile-section-summary' in page and 'mobile-section-body' in page
assert '<details class="mobile-customer-card">' not in page
assert '<details class="mobile-order-card">' in page and 'mobile-order-card[open]' in page
assert 'id="mobile-new-customer"' in page and 'id="mobile-new-sales-order"' in page
assert 'id="mobile-existing-customers"' in page and 'id="mobile-sales-list"' in page
assert 'data-open-mobile-details="mobile-new-sales-order"' in page
assert "soluaMobileFeedback" in page and "solua:orders-refresh" in page
assert 'writeCall("solua_home.api.mobile.create_customer"' in page
assert "mobile_orders" in page_context and 'view == "orders"' in page_context
assert "mobile_sales" in page_context and 'view == "sales"' in page_context
assert "mobile_reports" in page_context and 'view == "reports"' in page_context
assert "download_sales_order_customer_pdf" in page and "download_sales_order_customer_xlsx" in page
assert "data-mobile-file" in page and "navigator.share" in page and "存储到文件" in page
assert "销售中心" in page and "交付与开票" in page
assert "create_delivery_note" in page and "create_sales_invoice" in page and "create_pick_list" in page
assert "data-create-pick-list" in page and "can_create_pick_list" in api
assert '"Pick List": "pick-list"' in page and "打开拣货单" in page and "mobile-feedback-actions" in page
assert 'const createdDoctype = result.doctype' in page and 'docButtons(result, createdDoctype' in page and "打开单据" in page
assert '"pick_lists": order_pick_lists' in api and "renderPickList" in page and "已关联拣货单" in page
assert "报表中心" in page and "mobile-report-period" in page and "get_mobile_reports" in page
assert "手机报表" in page and "get_mobile_report_detail" in page and "Profitability Analysis" in page and "Item-wise Sales History" in page
assert "订单、开票、应收和实际收款" in page and "订单、开票、应收和已收" not in page
assert "unallocated_amount" in api and "未分配收款" in page and "净送货金额" in totals_api and "物料销售明细金额" in page
assert "mobile-report-collapse" in page and "mobile-report-prev" in page and "mobile-report-next" in page
assert 'query.set("page_length"' in page and 'id="mobile-report-detail"' not in page and "mobile-report-link" in page
assert "MOBILE_REPORT_MAX_PAGE_LENGTH" in api and '"has_next"' in api and '"sales_orders"' in api
print("mobile admin checks passed")
