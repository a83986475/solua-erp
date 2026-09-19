# -*- coding: utf-8 -*-
import frappe


def ensure_solua_stock_entry_types():
    """Reuse or create the two issue classifications used by the Solua Home page."""
    if not frappe.db.exists("DocType", "Stock Entry Type"):
        raise RuntimeError("Stock Entry Type DocType is unavailable")

    definitions = {
        "领用": ("领用", ("领用", "Consumption", "Issue for Use")),
        "损耗": ("损耗", ("损耗", "Wastage", "Waste", "Material Loss")),
    }
    existing = frappe.get_all(
        "Stock Entry Type",
        filters={"purpose": "Material Issue"},
        fields=["name", "purpose"],
        limit_page_length=0,
    )
    by_name = {row.name: row for row in existing}
    resolved = {}
    for key, (preferred, aliases) in definitions.items():
        match = next((by_name[name] for name in aliases if name in by_name), None)
        if match:
            resolved[key] = match.name
            continue
        doc = frappe.get_doc({
            "doctype": "Stock Entry Type",
            "name": preferred,
            "purpose": "Material Issue",
            "is_standard": 0,
        })
        doc.insert(ignore_permissions=True)
        resolved[key] = doc.name
    frappe.db.commit()
    return resolved


def ensure_wholesale_module():
    """Register the one shipped module without running a site migration."""
    if not frappe.db.exists("Module Def", "Solua Wholesale"):
        frappe.get_doc({
            "doctype": "Module Def",
            "module_name": "Solua Wholesale",
            "app_name": "solua_home",
            "custom": 0,
        }).insert(ignore_permissions=True)

    module = frappe.db.get_value(
        "Module Def", "Solua Wholesale", ["name", "app_name"], as_dict=True
    )
    if not module or module.app_name != "solua_home":
        raise RuntimeError("Invalid Module Def Solua Wholesale")
    return module


def refresh_wholesale_module_map():
    """Refresh only Frappe's cached app/module map after modules.txt is shipped."""
    frappe.cache().delete_value("app_modules")
    frappe.setup_module_map(include_all_apps=True)


def install_wholesale_only():
    """Install only the reviewed wholesale page, fields and two print formats."""
    import os
    from frappe.modules.import_file import import_file_by_path
    from frappe.modules import get_module_path

    try:
        refresh_wholesale_module_map()
        page_dir = get_module_path("Solua Wholesale", "page", "solua_home")
        if not os.path.isdir(page_dir):
            raise RuntimeError("Solua Wholesale page package is not importable: " + page_dir)
        ensure_wholesale_module()
        add_wholesale_fields(commit=False)
        base = os.path.dirname(__file__)
        for folder in ("sales_order_wholesale_color", "delivery_note_guia_remessa"):
            import_file_by_path(os.path.join(base, "print_format", folder, folder + ".json"),
                                force=True, ignore_version=True)
        import_file_by_path(os.path.join(base, "solua_wholesale", "page", "solua_home", "solua_home.json"),
                            force=True, ignore_version=True)
        page = frappe.get_doc("Page", "solua-home")
        if page.module != "Solua Wholesale":
            raise RuntimeError("Unexpected Page module")
        if not page.name or page.name != "solua-home":
            raise RuntimeError("Unexpected Page name")
        page.load_assets()
        if not page.script or not page.style:
            raise RuntimeError("Solua Page assets missing")
        for method in (
            "solua_home.api.home.get_dashboard_data",
            "solua_home.api.home.get_color_variants",
            "solua_home.api.stock.prepare_delivery_snapshot",
            "solua_home.printing.wholesale.prepare_print_snapshot",
            "solua_home.printing.wholesale.get_wholesale_print_data",
            "solua_home.boot.extended_bootinfo",
        ):
            if not callable(frappe.get_attr(method)):
                raise RuntimeError("Invalid hook: " + method)
        for name in ("客户订单确认单（颜色版）", "Guia de Remessa"):
            fmt = frappe.get_doc("Print Format", name)
            if not fmt.html or fmt.raw_printing or fmt.module != "Solua Wholesale":
                raise RuntimeError("Invalid HTML print format: " + name)
        frappe.db.commit()
    except Exception:
        frappe.db.rollback()
        raise


def after_install():
    """首次安装后执行"""
    add_translations()
    add_custom_fields()
    add_item_attributes()
    add_color_pool()
    add_variant_custom_fields()
    add_color_card_fields()
    add_sales_color_print_fields()
    add_wholesale_fields()
    configure_item_variant_settings()
    add_discount_approval_field()
    add_company_discount_settings()
    add_pos_profile_settings()
    configure_pos_tax()
    ensure_solua_stock_entry_types()
    sync_standard_print_formats()
    sync_standard_pages()
    add_member_system_fields()
    frappe.db.commit()


def after_migrate():
    """每次迁移后执行"""
    after_install()


def sync_standard_print_formats():
    """导入 app 自带的标准打印格式（价格标签等）到数据库

    新版 frappe 的 migrate 只同步 app 模块目录下的 print_format，
    app 根目录下的 print_format 需要手动导入（放这里随 migrate 自动执行）。
    """
    import os

    from frappe.modules.import_file import import_file_by_path

    base = os.path.join(os.path.dirname(__file__), "print_format")
    if not os.path.isdir(base):
        return

    for folder in os.listdir(base):
        json_path = os.path.join(base, folder, f"{folder}.json")
        if not os.path.exists(json_path):
            continue
        try:
            import_file_by_path(json_path, force=True, ignore_version=True)
            frappe.db.commit()
        except Exception as e:
            frappe.log_error(f"打印格式导入失败 [{json_path}]: {e}", "solua_home.print_formats")


def sync_standard_pages():
    """Import the standard Solua Home Desk page without changing routing now."""
    import os

    from frappe.modules.import_file import import_file_by_path

    base = os.path.join(os.path.dirname(__file__), "solua_wholesale", "page")
    for folder in os.listdir(base) if os.path.isdir(base) else []:
        json_path = os.path.join(base, folder, f"{folder}.json")
        if not os.path.exists(json_path):
            continue
        try:
            import_file_by_path(json_path, force=True, ignore_version=True)
            frappe.db.commit()
        except Exception as e:
            frappe.log_error(f"页面导入失败 [{json_path}]: {e}", "solua_home.pages")


def add_translations():
    """导入中文翻译到数据库"""
    translations = {
        "Sales Invoice": "销售发票",
        "Sales Order": "销售订单",
        "Delivery Note": "交货单",
        "Quotation": "报价单",
        "Customer": "客户",
        "Customer Name": "客户名称",
        "Overdue": "逾期",
        "Pending": "待处理",
        "Pending Approval": "待审批",
        "Approved": "已审批",
        "Rejected": "已拒绝",
        "Fully Paid": "已全额付款",
        "Partially Paid": "部分付款",
        "Unpaid": "未付款",
        "Overdue Amount": "逾期金额",
        "Outstanding Amount": "未结金额",
        "Grand Total": "总计",
        "Net Total": "净额",
        "Discount Amount": "折扣金额",
        "Purchase Order": "采购订单",
        "Purchase Invoice": "采购发票",
        "Purchase Receipt": "采购收货",
        "Supplier": "供应商",
        "Supplier Name": "供应商名称",
        "Item": "物料",
        "Item Code": "物料编码",
        "Item Name": "物料名称",
        "Item Group": "物料分组",
        "UOM": "单位",
        "Quantity": "数量",
        "Rate": "单价",
        "Amount": "金额",
        "Warehouse": "仓库",
        "Stock": "库存",
        "Address": "地址",
        "Contact": "联系人",
        "Phone": "电话",
        "Email": "邮箱",
        "Status": "状态",
        "Created By": "创建人",
        "Modified By": "修改人",
        "Created": "创建时间",
        "Modified": "修改时间",
        "Enabled": "已启用",
        "Disabled": "已禁用",
        "Active": "激活",
        "Inactive": "未激活",
        "Yes": "是",
        "No": "否",
        "Save": "保存",
        "Cancel": "取消",
        "Submit": "提交",
        "Amend": "修改",
        "Print": "打印",
        "Download": "下载",
        "Upload": "上传",
        "Search": "搜索",
        "Filter": "筛选",
        "Clear": "清除",
        "Close": "关闭",
        "Open": "打开",
        "New": "新建",
        "Edit": "编辑",
        "Delete": "删除",
        "View": "查看",
        "List": "列表",
        "Report": "报表",
        "Dashboard": "仪表盘",
        "Settings": "设置",
        "Help": "帮助",
        "Error": "错误",
        "Warning": "警告",
        "Success": "成功",
        "Information": "信息",
        "Loading": "加载中",
        "No Data": "无数据",
        "This field is required": "此字段为必填",
        "Operation completed successfully": "操作成功完成",
        "Are you sure?": "确定吗？",
        "Confirm": "确认",
        "Continue": "继续",
        "Back": "返回",
        "Next": "下一步",
        "Finish": "完成",
        "Total": "合计",
        "Subtotal": "小计",
        "Tax": "税",
        "Discount": "折扣",
        "Shipping": "运费",
        "Payment": "付款",
        "Reference": "参考",
        "Description": "描述",
        "Notes": "备注",
        "Terms": "条款",
        "Valid Till": "有效期至",
        "Currency": "货币",
        "Exchange Rate": "汇率",
        "Customer Group": "客户分组",
        "Territory": "销售区域",
        "Sales Partner": "销售伙伴",
        "Campaign": "营销活动",
        "Lead": "潜在客户",
        "Opportunity": "商机",
        "Company": "公司",
        "Chart of Accounts": "会计科目表",
        "Journal Entry": "日记账",
        "Payment Entry": "付款单",
        "Budget": "预算",
        "Asset": "资产",
        "Task": "任务",
        "Project": "项目",
        "Issue": "问题",
        "Support Ticket": "支持工单",
        "Serial No": "序列号",
        "Batch No": "批次号",
        "Barcode": "条码",
        "Image": "图片",
        "Attachment": "附件",
        "Comment": "评论",
        "History": "历史",
        "Version": "版本",
        "Workflow": "工作流",
        "Approval": "审批",
        # Item Variant 相关
        "Has Variants": "启用多规格",
        "Variant Of": "所属模板",
        "Variant Based On": "变体依据",
        "Attributes": "规格属性",
        "Item Attribute": "物料属性",
        "Item Attribute Value": "属性值",
        "Attribute": "属性",
        "Attribute Value": "属性值",
        "Abbreviation": "缩写",
        "Numeric Values": "数值属性",
        "From Range": "起始范围",
        "To Range": "结束范围",
        "Increment": "增量",
        "Template Item": "模板物料",
        "Variant Item": "变体物料",
        "Variant": "变体",
        "Variants": "多规格",
        "Item Variant Settings": "物料变体设置",
        "Copy Fields to Variant": "复制字段到变体",
        "Do Not Update Variants": "不更新变体",
        "Allow Rename Attribute Value": "允许重命名属性值",
        # 自定义字段
        "SPU Code": "SPU编码",
        "Chinese Name": "中文名称",
        "Spec Summary": "规格摘要",
        "POS Short Name": "POS收银简称",
        "Main Image": "主图",
        "Color Swatch": "色卡图",
        "Swatch Image": "色卡图",
        "Color": "颜色",
        "Size": "尺码",
        "Material": "材质",
        # 颜色池（Cor 属性）
        "Branco": "白色",
        "Preto": "黑色",
        "Prata": "银色",
        "Cinza": "灰色",
        "Azul": "蓝色",
        "Vermelho": "红色",
        "Verde": "绿色",
        "Amarelo": "黄色",
        "Bege": "米色",
        "Laranja": "橙色",
        "Rosa": "粉色",
        "Roxo": "紫色",
        "Dourado": "金色",
        "Marrom": "棕色",
        "Turquesa": "青色",
        "Creme": "奶油色",
        # 批量生成变体
        "Bulk Create Variants": "批量生成变体",
        "Select Template Item": "选择模板物料",
        "Select Colors": "选择颜色",
        "Create Variants": "创建变体",
    }

    for source, translated in translations.items():
        try:
            if not frappe.db.exists("Translation", {"source_text": source, "language": "zh"}):
                doc = frappe.get_doc({
                    "doctype": "Translation",
                    "source_text": source,
                    "translated_text": translated,
                    "language": "zh",
                    "contributed": 0,
                })
                doc.insert(ignore_permissions=True)
        except Exception as e:
            frappe.log_error(f"翻译导入失败 [{source}]: {e}", "solua_home.translations")

    frappe.db.commit()


def add_custom_fields():
    """初始化自定义字段"""
    custom_fields = [
        {
            "dt": "Customer",
            "fieldname": "custom_contract_status",
            "label": "合同状态",
            "fieldtype": "Select",
            "options": "\n正常\n即将到期\n已到期\n已续约",
            "insert_after": "customer_name",
        },
    ]

    for field in custom_fields:
        try:
            if not frappe.db.exists("Custom Field", {"dt": field["dt"], "fieldname": field["fieldname"]}):
                doc = frappe.get_doc({
                    "doctype": "Custom Field",
                    **field,
                    "owner": "Administrator",
                })
                doc.insert(ignore_permissions=True)
        except Exception as e:
            frappe.log_error(f"自定义字段创建失败 [{field.get('fieldname')}]: {e}", "solua_home.custom_fields")

    frappe.db.commit()


def add_discount_approval_field():
    """销售发票折扣审批字段：审批密码输入框 + 审批标记（隐藏，仅内部使用）

    2026-08-08 升级为密码审批：管理员在「审批密码」字段输入公司配置的审批密码
    即放行；勾选框 custom_discount_approved 降级为内部标记，由代码校验密码后置位，
    界面上隐藏且只读（收银员无法自助勾选）。
    """
    fields = [
        {
            "dt": "Sales Invoice",
            "fieldname": "custom_discount_approved",
            "label": "折扣超限已审批",
            "fieldtype": "Check",
            "insert_after": "additional_discount_account",
            "description": "内部审批标记：输入正确审批密码后自动置位，请勿手动勾选",
        },
        {
            "dt": "Sales Invoice",
            "fieldname": "custom_approval_password",
            "label": "审批密码",
            "fieldtype": "Password",
            "insert_after": "custom_discount_approved",
            "description": "含折扣单据提交需审批：管理员在此输入审批密码（密码在 设置→公司→Solua Home, Lda 中配置）",
        },
    ]

    for field in fields:
        try:
            if not frappe.db.exists("Custom Field", {"dt": field["dt"], "fieldname": field["fieldname"]}):
                doc = frappe.get_doc({
                    "doctype": "Custom Field",
                    **field,
                    "owner": "Administrator",
                })
                doc.insert(ignore_permissions=True)
        except Exception as e:
            frappe.log_error(f"折扣审批字段创建失败 [{field.get('fieldname')}]: {e}", "solua_home.custom_fields")

    # 审批标记隐藏为内部字段：界面不可见、不可勾选（只由代码置位）
    try:
        frappe.make_property_setter(
            {
                "doctype": "Sales Invoice",
                "doctype_or_field": "DocField",
                "field_name": "custom_discount_approved",
                "property": "hidden",
                "property_type": "Check",
                "value": 1,
            }
        )
        frappe.make_property_setter(
            {
                "doctype": "Sales Invoice",
                "doctype_or_field": "DocField",
                "field_name": "custom_discount_approved",
                "property": "read_only",
                "property_type": "Check",
                "value": 1,
            }
        )
    except Exception as e:
        frappe.log_error(f"折扣审批字段属性设置失败: {e}", "solua_home.custom_fields")

    frappe.db.commit()


def add_company_discount_settings():
    """公司级折扣审批配置：总开关 / 阈值 / 审批密码（在 设置→公司→Solua Home, Lda 中修改）"""
    fields = [
        {
            "dt": "Company",
            "fieldname": "custom_enable_discount_approval",
            "label": "启用折扣审批",
            "fieldtype": "Check",
            "default": "1",
            "insert_after": "country",
            "description": "开启后，折扣幅度超过阈值的销售发票需输入审批密码才能提交",
        },
        {
            "dt": "Company",
            "fieldname": "custom_discount_approval_threshold",
            "label": "折扣审批阈值（%）",
            "fieldtype": "Percent",
            "default": "0",
            "insert_after": "custom_enable_discount_approval",
            "description": "折扣幅度超过此值需审批；0 = 任何折扣都需审批",
        },
        {
            "dt": "Company",
            "fieldname": "custom_discount_approval_password",
            "label": "折扣审批密码",
            "fieldtype": "Password",
            "insert_after": "custom_discount_approval_threshold",
            "description": "管理员在销售发票「审批密码」字段输入此密码后放行；为空则视为不启用审批",
        },
    ]

    for field in fields:
        try:
            if not frappe.db.exists("Custom Field", {"dt": field["dt"], "fieldname": field["fieldname"]}):
                doc = frappe.get_doc({
                    "doctype": "Custom Field",
                    **field,
                    "owner": "Administrator",
                })
                doc.insert(ignore_permissions=True)
        except Exception as e:
            frappe.log_error(f"公司折扣审批字段创建失败 [{field.get('fieldname')}]: {e}", "solua_home.custom_fields")

    frappe.db.commit()


def add_pos_profile_settings():
    """POS Profile 独立开关：收银后自动开新单（与自动打印分开控制）

    2026-08-16：原实现把「自动开新单」绑在 print_receipt_on_order_complete 上
    （打印开=自动打印+自动开新单）。拆成独立开关后，打印与小票/开新单可分别控制：
    打印开+开新单开=打印完自动开新单；打印开+开新单关=只打印停留摘要页；
    打印关+开新单开=不打印直接自动开新单；打印关+开新单关=原生手动流程。
    """
    field = {
        "dt": "POS Profile",
        "fieldname": "custom_auto_new_order",
        "label": "收银后自动开新单",
        "fieldtype": "Check",
        "default": "1",
        "insert_after": "print_receipt_on_order_complete",
        "description": "收银完成后自动开始新订单（与「打印收据」独立控制）",
    }
    try:
        if not frappe.db.exists("Custom Field", {"dt": "POS Profile", "fieldname": field["fieldname"]}):
            doc = frappe.get_doc({
                "doctype": "Custom Field",
                **field,
                "owner": "Administrator",
            })
            doc.insert(ignore_permissions=True)
    except Exception as e:
        frappe.log_error(f"POS Profile 开关字段创建失败 [{field.get('fieldname')}]: {e}", "solua_home.custom_fields")

    # 存量 POS Profile 补默认值（新建字段对已有记录不生效，自动补 1 保持原行为）
    frappe.db.sql(
        "UPDATE `tabPOS Profile` SET custom_auto_new_order = 1 WHERE custom_auto_new_order IS NULL"
    )
    frappe.db.commit()


def configure_pos_tax():
    """POS 增值税配置（模式 A：标签价含税，价内税拆分）

    2026-08-16：POS Profile 原本未挂税模板，POS 发票净额=总额（不含税）。
    模式 A = 零售标准：物料 standard_rate 即顾客实付价（含 IVA），
    模板 IVA - SH 的税额行 marked included_in_print_rate=1，系统自动拆分
    净额/税额（1500 → 1293.10 净 + 206.90 IVA），账上照记税但不多收顾客钱。

    幂等：可重复执行。模板已存在于库中（不负责创建，创建需配套科目表），
    只修正其税行标记、停用重复模板、给 POS Profile 挂模板。
    """
    template_name = "IVA - SH"
    if frappe.db.exists("Sales Taxes and Charges Template", template_name):
        # 模板是 master（is_submittable=0），但导入时 docstatus 异常为 1，
        # 会锁住后续修改（UpdateAfterSubmitError），归 0 恢复可编辑
        ds = frappe.db.get_value("Sales Taxes and Charges Template", template_name, "docstatus")
        if ds == 1:
            frappe.db.set_value("Sales Taxes and Charges Template", template_name, "docstatus", 0)

        tpl = frappe.get_doc("Sales Taxes and Charges Template", template_name)
        changed = False
        for row in tpl.taxes:
            if not row.included_in_print_rate:
                row.included_in_print_rate = 1
                changed = True
        if changed:
            tpl.save(ignore_permissions=True)

    # 停用重复模板（与 IVA - SH 同为 16%，避免误选）
    if frappe.db.exists("Sales Taxes and Charges Template", "Mozambique Tax - SH"):
        ds = frappe.db.get_value("Sales Taxes and Charges Template", "Mozambique Tax - SH", "docstatus")
        if ds == 1:
            frappe.db.set_value("Sales Taxes and Charges Template", "Mozambique Tax - SH", "docstatus", 0)
        frappe.db.set_value("Sales Taxes and Charges Template", "Mozambique Tax - SH", "disabled", 1)

    # POS Profile 挂税模板
    profile = frappe.db.get_value(
        "POS Profile",
        {"company": "Solua Home, Lda"},
        ["name", "taxes_and_charges"],
        as_dict=True,
    )
    if profile and profile.taxes_and_charges != template_name:
        doc = frappe.get_doc("POS Profile", profile.name)
        doc.taxes_and_charges = template_name
        doc.save(ignore_permissions=True)

    frappe.db.commit()


def add_item_attributes():
    """初始化 Item Attribute 框架（不含预填值，由用户自行添加属性值）

    颜色属性统一用 Cor（葡语池，见 add_color_pool），不再创建 Color/Colour。
    """
    attribute_names = ["Size", "Material", "Season", "Gender"]

    for attr_name in attribute_names:
        try:
            if frappe.db.exists("Item Attribute", attr_name):
                continue

            doc = frappe.get_doc({
                "doctype": "Item Attribute",
                "attribute_name": attr_name,
                "numeric_values": 0,
            })
            doc.insert(ignore_permissions=True)
        except Exception as e:
            frappe.log_error(f"Item Attribute 创建失败 [{attr_name}]: {e}", "solua_home.attributes")

    frappe.db.commit()


def add_variant_custom_fields():
    """添加多规格体系相关的自定义字段到 Item"""
    fields = [
        {
            "dt": "Item",
            "fieldname": "custom_spu_code",
            "label": "SPU编码",
            "fieldtype": "Data",
            "insert_after": "item_code",
            "description": "商品款号/主款编码，同一款不同规格共享此编码",
        },
        {
            "dt": "Item",
            "fieldname": "custom_chinese_name",
            "label": "中文显示名",
            "fieldtype": "Data",
            "insert_after": "item_name",
            "description": "门店或客户看到的中文商品名",
        },
        {
            "dt": "Item",
            "fieldname": "custom_spec_summary",
            "label": "规格摘要",
            "fieldtype": "Data",
            "insert_after": "custom_chinese_name",
            "description": "例如：红-M-纯棉，自动拼装或手动填写",
        },
        {
            "dt": "Item",
            "fieldname": "custom_pos_short_name",
            "label": "POS收银简称",
            "fieldtype": "Data",
            "insert_after": "custom_spec_summary",
            "description": "收银界面显示的简短名称",
        },
        {
            "dt": "Item",
            "fieldname": "custom_swatch_image",
            "label": "色卡图",
            "fieldtype": "Attach Image",
            "insert_after": "image",
            "description": "同款不同颜色的色卡小图",
        },
        {
            "dt": "Item Attribute Value",
            "fieldname": "swatch_image",
            "label": "色卡图",
            "fieldtype": "Attach Image",
            "insert_after": "abbr",
            "description": "该颜色值的色卡小图（POS 颜色弹窗/设计器显示）",
        },
    ]

    for field in fields:
        try:
            if not frappe.db.exists("Custom Field", {"dt": "Item", "fieldname": field["fieldname"]}):
                doc = frappe.get_doc({
                    "doctype": "Custom Field",
                    **field,
                    "owner": "Administrator",
                })
                doc.insert(ignore_permissions=True)
        except Exception as e:
            frappe.log_error(f"Variant 自定义字段创建失败 [{field.get('fieldname')}]: {e}", "solua_home.variant_fields")

    frappe.db.commit()


def add_color_card_fields():
    """为颜色变体补充固定色号、对外货号和公开发布开关。"""
    fields = [
        {
            "dt": "Item",
            "fieldname": "custom_color_code",
            "label": "固定色号",
            "fieldtype": "Data",
            "insert_after": "custom_pos_short_name",
            "depends_on": "eval:doc.variant_of",
            "description": "本款内固定的数字色号，例如 01、02；一旦使用不重新分配",
        },
        {
            "dt": "Item",
            "fieldname": "custom_order_code",
            "label": "对外订货货号",
            "fieldtype": "Data",
            "insert_after": "custom_color_code",
            "description": "客户使用的稳定货号；为空时公开页面回退使用 Item 编码",
        },
        {
            "dt": "Item",
            "fieldname": "custom_color_card_published",
            "label": "发布到公开色卡",
            "fieldtype": "Check",
            "insert_after": "custom_swatch_image",
            "default": "0",
            "description": "模板和具体颜色都勾选后，才会出现在 erp.solua.one/colors",
        },
    ]

    for field in fields:
        try:
            if not frappe.db.exists("Custom Field", {"dt": field["dt"], "fieldname": field["fieldname"]}):
                frappe.get_doc({
                    "doctype": "Custom Field",
                    **field,
                    "owner": "Administrator",
                }).insert(ignore_permissions=True)
        except Exception as e:
            frappe.log_error(
                f"色卡字段创建失败 [{field.get('fieldname')}]: {e}",
                "solua_home.color_card_fields",
            )

    frappe.db.commit()


def add_sales_color_print_fields():
    """给批发销售发票提供图片和二维码两个独立打印开关。"""
    fields = [
        {
            "dt": "Sales Invoice",
            "fieldname": "custom_print_color_images",
            "label": "批发单显示颜色图片",
            "fieldtype": "Check",
            "insert_after": "is_pos",
            "default": "0",
            "allow_on_submit": 1,
            "description": "批发销售单打印格式开启时，显示每个颜色的实拍图",
        },
        {
            "dt": "Sales Invoice",
            "fieldname": "custom_print_color_qr",
            "label": "批发单显示色卡二维码",
            "fieldtype": "Check",
            "insert_after": "custom_print_color_images",
            "default": "0",
            "allow_on_submit": 1,
            "description": "批发销售单打印格式开启时，显示对应款式的公开色卡二维码",
        },
    ]

    for field in fields:
        try:
            if not frappe.db.exists("Custom Field", {"dt": field["dt"], "fieldname": field["fieldname"]}):
                frappe.get_doc({
                    "doctype": "Custom Field",
                    **field,
                    "owner": "Administrator",
                }).insert(ignore_permissions=True)
        except Exception as e:
            frappe.log_error(
                f"销售单打印开关创建失败 [{field.get('fieldname')}]: {e}",
                "solua_home.color_card_fields",
            )

    frappe.db.commit()


def add_wholesale_fields(commit=True):
    """Add only the small snapshots needed for wholesale order/delivery prints."""
    fields = [
        {"dt": dt, "fieldname": "custom_wholesale_snapshot", "label": "Wholesale print snapshot",
         "fieldtype": "Long Text", "hidden": 1, "read_only": 1, "no_copy": 1}
        for dt in ("Sales Order", "Delivery Note")
    ] + [
        {"dt": "Sales Order", "fieldname": "custom_store_name", "label": "客户门店名称", "fieldtype": "Data", "insert_after": "customer_name"},
        {"dt": "Sales Order", "fieldname": "custom_customer_order_no", "label": "客户订单号", "fieldtype": "Data", "insert_after": "po_no"},
        {"dt": "Sales Order", "fieldname": "custom_payment_method", "label": "付款方式", "fieldtype": "Select", "options": "\n先款\n货到付款（COD）\n赊账\n定金+尾款", "insert_after": "payment_terms_template"},
        {"dt": "Sales Order", "fieldname": "custom_deposit_amount", "label": "定金金额", "fieldtype": "Currency", "insert_after": "custom_payment_method", "depends_on": "eval:doc.custom_payment_method=='定金+尾款'"},
        {"dt": "Sales Order", "fieldname": "custom_balance_due_date", "label": "尾款到期日", "fieldtype": "Date", "insert_after": "custom_deposit_amount", "depends_on": "eval:doc.custom_payment_method=='定金+尾款'"},
        {"dt": "Sales Order", "fieldname": "custom_invoice_plan", "label": "开票安排", "fieldtype": "Small Text", "insert_after": "terms"},
        {"dt": "Sales Order", "fieldname": "custom_print_color_images", "label": "订单显示颜色图片", "fieldtype": "Check", "default": "0", "allow_on_submit": 1, "insert_after": "letter_head"},
        {"dt": "Sales Order", "fieldname": "custom_print_color_qr", "label": "订单显示色卡二维码", "fieldtype": "Check", "default": "0", "allow_on_submit": 1, "insert_after": "custom_print_color_images"},
        {"dt": "Delivery Note", "fieldname": "custom_store_name", "label": "客户门店名称", "fieldtype": "Data", "insert_after": "customer_name"},
        {"dt": "Delivery Note", "fieldname": "custom_customer_order_no", "label": "客户订单号", "fieldtype": "Data", "insert_after": "po_no"},
        {"dt": "Delivery Note", "fieldname": "custom_departure_time", "label": "实际起运时间", "fieldtype": "Datetime", "insert_after": "posting_time"},
        {"dt": "Delivery Note", "fieldname": "custom_source_warehouse_address", "label": "发货仓库地址", "fieldtype": "Small Text", "insert_after": "company_address_display", "description": "公司与仓库目前同址：AV. DO TRABALHO, n.º 231, Cidade de Maputo；如以后分仓请在单据上维护当次地址"},
        {"dt": "Delivery Note", "fieldname": "custom_driver_phone", "label": "司机电话", "fieldtype": "Data", "insert_after": "driver_name"},
        {"dt": "Delivery Note", "fieldname": "custom_box_count", "label": "箱数", "fieldtype": "Int", "insert_after": "transporter_info", "description": "适用时填写；不适用留空"},
        {"dt": "Delivery Note", "fieldname": "custom_pallet_count", "label": "托盘数", "fieldtype": "Int", "insert_after": "custom_box_count", "description": "适用时填写；不适用留空"},
        {"dt": "Delivery Note", "fieldname": "custom_delivery_notes", "label": "差异/退货备注", "fieldtype": "Small Text", "insert_after": "instructions"},
        {"dt": "Delivery Note", "fieldname": "custom_invoice_plan", "label": "开票安排", "fieldtype": "Small Text", "insert_after": "custom_delivery_notes"},
        {"dt": "Delivery Note", "fieldname": "custom_signature_name", "label": "签收姓名", "fieldtype": "Data", "insert_after": "custom_invoice_plan"},
        {"dt": "Delivery Note", "fieldname": "custom_signature_date", "label": "签收日期", "fieldtype": "Date", "insert_after": "custom_signature_name"},
        {"dt": "Delivery Note", "fieldname": "custom_print_color_images", "label": "送货单显示颜色图片", "fieldtype": "Check", "default": "0", "allow_on_submit": 1, "insert_after": "letter_head"},
        {"dt": "Delivery Note", "fieldname": "custom_print_color_qr", "label": "送货单显示色卡二维码", "fieldtype": "Check", "default": "0", "allow_on_submit": 1, "insert_after": "custom_print_color_images"},
        {"dt": "Delivery Note Item", "fieldname": "custom_ordered_qty", "label": "订购数量", "fieldtype": "Float", "read_only": 1, "insert_after": "qty"},
        {"dt": "Delivery Note Item", "fieldname": "custom_delivered_before_qty", "label": "此前累计送货", "fieldtype": "Float", "read_only": 1, "insert_after": "custom_ordered_qty"},
        {"dt": "Delivery Note Item", "fieldname": "custom_remaining_qty", "label": "本次后剩余", "fieldtype": "Float", "read_only": 1, "insert_after": "custom_delivered_before_qty"},
    ]
    for field in fields:
        if not frappe.db.exists("Custom Field", {"dt": field["dt"], "fieldname": field["fieldname"]}):
            frappe.get_doc({"doctype": "Custom Field", **field, "owner": "Administrator"}).insert(ignore_permissions=True)
    if commit:
        frappe.db.commit()


# 窗帘颜色池（Cor 属性）：全部常用颜色 + 唯一缩写
# 变体编码 = 模板编码-缩写（如 CR-001-PR = Preto 黑）；缩写必须全局唯一
CURTAIN_COLOR_POOL = [
    ("Branco", "BR"),      # 白
    ("Preto", "PR"),       # 黑
    ("Prata", "PT"),       # 银（PT 避免与 Preto 的 PR 冲突）
    ("Cinza", "CZ"),       # 灰
    ("Azul", "AZ"),        # 蓝
    ("Vermelho", "VM"),    # 红
    ("Verde", "VD"),       # 绿
    ("Amarelo", "AM"),     # 黄
    ("Bege", "BG"),        # 米
    ("Laranja", "LJ"),     # 橙
    ("Rosa", "RS"),        # 粉
    ("Roxo", "RX"),        # 紫
    ("Dourado", "DR"),     # 金
    ("Marrom", "MR"),      # 棕
    ("Turquesa", "TQ"),    # 青
    ("Creme", "CM"),       # 奶油
]


def add_color_pool():
    """初始化/更新窗帘颜色池（Cor 属性 16 色，缩写唯一）

    - 属性不存在则创建；已存在则按 CURTAIN_COLOR_POOL 重建颜色值
    - 幂等：可重复执行，不会重复插入
    """
    if not frappe.db.exists("Item Attribute", "Cor"):
        doc = frappe.get_doc({
            "doctype": "Item Attribute",
            "attribute_name": "Cor",
            "numeric_values": 0,
        })
        doc.insert(ignore_permissions=True)

    attr = frappe.get_doc("Item Attribute", "Cor")
    # 校验缩写唯一性
    abbrs = [a for _, a in CURTAIN_COLOR_POOL]
    dupes = {x for x in abbrs if abbrs.count(x) > 1}
    if dupes:
        frappe.log_error(f"颜色池缩写重复: {dupes}", "solua_home.color_pool")
        raise ValueError(f"Color pool abbreviations conflict: {dupes}")

    existing = {v.attribute_value for v in attr.item_attribute_values}
    pool = dict(CURTAIN_COLOR_POOL)
    changed = False

    # 更新/新增
    for v in attr.item_attribute_values:
        if v.attribute_value in pool:
            new_abbr = pool[v.attribute_value]
            if v.abbr != new_abbr:
                v.abbr = new_abbr
                changed = True
            del pool[v.attribute_value]
        else:
            # 不在池子里的旧值移除（避免与池子冲突）
            attr.item_attribute_values.remove(v)
            changed = True

    # 池子里新增的
    for value, abbr in pool.items():
        attr.append("item_attribute_values", {"attribute_value": value, "abbr": abbr})
        changed = True

    if changed:
        attr.save(ignore_permissions=True)
        frappe.db.commit()
    return len(CURTAIN_COLOR_POOL)


def clear_prefilled_attributes():
    """清除服务器上已预填的属性值（改为空框架）"""
    import frappe

    for attr_name in ["Size", "Material", "Season", "Gender"]:
        try:
            if not frappe.db.exists("Item Attribute", attr_name):
                continue

            attr = frappe.get_doc("Item Attribute", attr_name)
            if attr.item_attribute_values:
                attr.item_attribute_values = []
                attr.save(ignore_permissions=True)
                print(f"  ✓ {attr_name}: values cleared")
            else:
                print(f"  - {attr_name}: already empty")
        except Exception as e:
            print(f"  ✗ {attr_name}: error - {e}")

    frappe.db.commit()
    print("Done: all attribute values cleared")

def configure_item_variant_settings():
    """配置 Item Variant Settings（复制字段到变体）"""
    try:
        settings = frappe.get_single("Item Variant Settings")

        fields_to_copy = [
            "item_name",
            "description",
            "image",
            "stock_uom",
            "brand",
            "item_group",
            "custom_chinese_name",
            "custom_spu_code",
            "custom_swatch_image",
        ]

        existing_fields = {row.field_name for row in settings.fields}
        changed = False

        for field_name in fields_to_copy:
            if field_name not in existing_fields:
                settings.append("fields", {"field_name": field_name})
                changed = True

        if changed:
            settings.save(ignore_permissions=True)
    except Exception as e:
        frappe.log_error(f"Item Variant Settings 配置失败: {e}", "solua_home.variant_settings")

    frappe.db.commit()


def add_member_system_fields():
    """会员系统自定义字段 + 会员方案初始化"""
    customer_fields = [
        {
            "dt": "Customer",
            "fieldname": "custom_member_card_no",
            "label": "会员卡号",
            "fieldtype": "Data",
            "insert_after": "customer_name",
            "unique": 1,
            "description": "唯一会员卡号，用于 POS 扫码识别",
        },
        {
            "dt": "Customer",
            "fieldname": "custom_stored_value",
            "label": "储值余额",
            "fieldtype": "Currency",
            "insert_after": "custom_member_card_no",
            "default": "0",
            "description": "会员储值卡余额",
        },
        {
            "dt": "Customer",
            "fieldname": "custom_member_since",
            "label": "入会日期",
            "fieldtype": "Date",
            "insert_after": "custom_stored_value",
        },
        {
            "dt": "Customer",
            "fieldname": "custom_total_points",
            "label": "累计积分",
            "fieldtype": "Int",
            "insert_after": "custom_member_since",
            "read_only": 1,
        },
    ]
    for field in customer_fields:
        try:
            if not frappe.db.exists("Custom Field", {"dt": field["dt"], "fieldname": field["fieldname"]}):
                doc = frappe.get_doc({"doctype": "Custom Field", **field, "owner": "Administrator"})
                doc.insert(ignore_permissions=True)
        except Exception as e:
            frappe.log_error(f"会员字段创建失败 [{field.get('fieldname')}]: {e}", "solua_home.member_fields")

    # Sales Invoice 充值标记
    inv_field = {
        "dt": "Sales Invoice",
        "fieldname": "custom_is_topup",
        "label": "储值充值",
        "fieldtype": "Check",
        "insert_after": "is_pos",
    }
    try:
        if not frappe.db.exists("Custom Field", {"dt": inv_field["dt"], "fieldname": inv_field["fieldname"]}):
            doc = frappe.get_doc({"doctype": "Custom Field", **inv_field, "owner": "Administrator"})
            doc.insert(ignore_permissions=True)
    except Exception as e:
        frappe.log_error(f"充值标记字段创建失败: {e}", "solua_home.member_fields")

    # 初始化默认会员方案
    try:
        from solua_home.api.member import ensure_loyalty_program
        ensure_loyalty_program()
    except Exception as e:
        frappe.log_error(f"会员方案初始化失败: {e}", "solua_home.member_fields")

    frappe.db.commit()
