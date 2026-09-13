app_name = "solua_home"
app_title = "Solua Home 定制"
app_publisher = "Solua Home, Lda"
app_description = "Solua Home 生产定制：POS 扫码选色、多规格变体、中文翻译、业务校验"
app_icon = "fa fa-home"
app_color = "#3498db"
app_email = "admin@solua.one"
app_license = "GNU General Public License (v3)"
source_link = "https://github.com/a83986475/solua-erp"
app_logo_url = "/assets/solua_home/logo.png"
app_home = "."

# ------------------- DocType 事件钩子 -------------------
doc_events = {
    # ========== 销售模块 ==========
    "Sales Invoice": {
        "before_validate": "solua_home.api.sales.before_validate_sales_invoice",
        "validate": "solua_home.api.sales.validate_sales_invoice",
        "on_submit": "solua_home.api.sales.on_invoice_submitted",
        "on_cancel": "solua_home.api.sales.on_invoice_cancelled",
    },
    "Sales Order": {
        "validate": "solua_home.api.sales.validate_sales_order",
    },
    "Quotation": {
        "validate": "solua_home.api.sales.validate_quotation",
    },
    "Customer": {
        "validate": "solua_home.api.sales.validate_customer",
        "after_insert": "solua_home.api.sales.after_customer_created",
    },

    # ========== 采购模块 ==========
    "Purchase Order": {
        "validate": "solua_home.api.buying.validate_purchase_order",
    },
    "Purchase Invoice": {
        "validate": "solua_home.api.buying.validate_purchase_invoice",
    },
    "Supplier": {
        "validate": "solua_home.api.buying.validate_supplier",
    },

    # ========== 库存模块 ==========
    "Item": {
        "before_validate": "solua_home.api.stock.before_validate_item",
        "validate": "solua_home.api.stock.validate_item",
        "after_insert": "solua_home.api.stock.auto_create_item_price",
    },
    "Stock Entry": {
        "on_submit": "solua_home.api.stock.on_stock_entry_submitted",
    },
    "Delivery Note": {
        "validate": "solua_home.api.stock.validate_delivery_note",
    },
    # 允许负库存与 POS「禁止超卖」保持一致（两个字段语义相反）
    "Stock Settings": {
        "on_update": "solua_home.api.stock_settings.sync_from_stock_settings",
    },
    "POS Profile": {
        "on_update": "solua_home.api.stock_settings.sync_from_pos_profile",
    },

    # ========== 通用 ==========
    "Address": {
        "validate": "solua_home.api.common.validate_address",
    },
    "Contact": {
        "validate": "solua_home.api.common.validate_contact",
    },
}

# ------------------- 类重写 -------------------
extend_doctype_class = {
    "Sales Invoice": "solua_home.override.sales_invoice.CustomSalesInvoice",
}

override_whitelisted_methods = {
    "erpnext.selling.page.point_of_sale.point_of_sale.get_items": "solua_home.api.pos.get_items",
    # 强制 Page 文档不缓存进 localStorage（否则 pos_custom.js 等 page_js 更新不生效）
    "frappe.desk.desk_page.getpage": "solua_home.override.desk_page.getpage",
}

# ------------------- Jinja 打印 helper（价格标签等） -------------------
jinja = {
    "methods": [
        "solua_home.printing.label_helpers.get_barcode_img",
        "solua_home.printing.label_helpers.get_selling_price",
        "solua_home.api.color_card.get_public_color_card_url",
        "solua_home.printing.color_card.get_item_color_info",
        "solua_home.printing.color_card.get_color_card_qr_img",
    ],
}

# ------------------- 安装/迁移 -------------------
after_install = "solua_home.install.after_install"
after_migrate = "solua_home.install.after_migrate"

# ------------------- 启动信息 -------------------
extend_bootinfo = "solua_home.boot.extended_bootinfo"

# ------------------- 权限 -------------------
permission_query_conditions = {}
has_permission = {}

# ------------------- 调度任务 -------------------
scheduler_events = {
    "daily": [
        "solua_home.tasks.daily_tasks",
    ],
    "weekly": [
        "solua_home.tasks.weekly_tasks",
    ],
    "cron": {
        "0 2 * * *": [
            "solua_home.tasks.custom_cron_task",
        ],
    },
}

# ------------------- UI 扩展 -------------------
global_search_doctypes = {}
website_route_rules = []
standard_navbar_items = []

# 全局 CSS：隐藏表单评论输入框（保留活动时间线）
app_include_css = [
    "/assets/solua_home/css/hide_comments.css",
]

# 全局 JS：Link 输入框有内容时点击也弹出下拉（全站表单生效）+ 标签打印（Ctrl+L）+ 零售参数/商品打包/打印导入导出
app_include_js = [
    "/assets/solua_home/js/solua_home_global.js",
    "/assets/solua_home/js/label_print.js?v=20260822b",
    "/assets/solua_home/js/promotion_wizard.js",
    "/assets/solua_home/js/retail_settings_panel.js",
    "/assets/solua_home/js/print_format_import_export.js",
    # Point of Sale 是已打包的标准页面，page_js 不一定会被执行；
    # 全局引入后由 pos_custom.js 自己等待 POS 类加载，确保颜色弹窗可靠生效。
    "/assets/solua_home/js/pos_custom.js",
]

# Custom JS for standard pages
page_js = {
    "print-designer": "public/js/print_designer_zh.js",
}

# Custom JS for Item form: template page shows per-color and total stock.
doctype_js = {
    "Item": "public/js/item_color_stock.js",
    "Sales Invoice": "public/js/sales_invoice_print_options.js",
}

# Custom JS for doctype list views（Item 列表页的向导按钮）
# 注：不能用 page_js（只对 Page 文档生效），Item 是 DocType，必须用 doctype_list_js
doctype_list_js = {
    "Item": [
        "public/js/item_variant_wizard.js",
        "public/js/item_data_wizard.js",
    ],
}
