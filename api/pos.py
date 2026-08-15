# -*- coding: utf-8 -*-
import frappe
from frappe import _


@frappe.whitelist()
def scan_barcode_for_pos(barcode):
    """扫码查找商品。

    如果条码对应模板物料（有 Variant），返回该模板的所有颜色选项。
    如果条码直接对应 Variant 或普通物料，直接返回该物料信息。
    如果未找到，返回 not_found。
    """
    if not barcode:
        return {"type": "not_found"}

    try:
        # 1. 查找条码（条码存在 Item Barcode 子表中，与 erpnext.stock.utils.scan_barcode 一致）
        item_code = frappe.db.get_value("Item Barcode", {"barcode": barcode}, "parent")
        if not item_code:
            # 2. 兜底：条码 = 物料编码（变体标签打印的是变体编码 Code 128，
            #    如 CR-001-BR，扫标签直接定位具体颜色）
            item_code = frappe.db.get_value(
                "Item", {"item_code": barcode, "disabled": 0}, "name"
            )
        if not item_code:
            return {"type": "not_found"}

        has_variants = frappe.db.get_value("Item", item_code, "has_variants")

        # 2. 如果是模板物料
        if has_variants:
            template_name = frappe.db.get_value("Item", item_code, "item_name")
            # custom_swatch_image 是可选自定义字段，未创建时跳过避免报错
            item_fields = ["item_code", "item_name", "image"]
            if frappe.db.has_column("Item", "custom_swatch_image"):
                item_fields.append("custom_swatch_image")

            variants = frappe.get_all(
                "Item",
                filters={"variant_of": item_code, "disabled": 0},
                fields=item_fields,
                order_by="item_code asc",
            )
            color_options = []
            for v in variants:
                cor = frappe.db.get_value(
                    "Item Variant Attribute",
                    {"parent": v.item_code, "attribute": "Cor"},
                    "attribute_value",
                )
                if not cor:
                    attrs = frappe.get_all(
                        "Item Variant Attribute",
                        filters={"parent": v.item_code},
                        fields=["attribute", "attribute_value"],
                        limit=1,
                    )
                    if attrs:
                        cor = attrs[0].attribute_value
                    else:
                        cor = v.item_name
                color_options.append({
                    "variant_code": v.item_code,
                    "variant_name": v.item_name,
                    "cor": cor,
                    "image": v.image or "",
                    "swatch": getattr(v, "custom_swatch_image", "") or "",
                })
            return {
                "type": "template",
                "template_code": item_code,
                "template_name": template_name,
                "colors": color_options,
            }

        # 3. 如果是 Variant 或普通物料
        item_name = frappe.db.get_value("Item", item_code, "item_name")
        return {
            "type": "variant",
            "item_code": item_code,
            "item_name": item_name,
        }
    except Exception as e:
        frappe.log_error(f"POS 扫码查询失败 ({barcode}): {e!s}", "solua_home")
        return {"type": "error", "message": str(e)}


def create_test_data():
    """Create test data for POS barcode scanning testing."""
    import frappe

    # 1. Item Attribute Cor
    if not frappe.db.exists("Item Attribute", "Cor"):
        attr = frappe.get_doc({
            "doctype": "Item Attribute",
            "attribute_name": "Cor",
            "numeric_values": 0,
            "item_attribute_values": [
                {"attribute_value": "Branco", "abbr": "BR"},
                {"attribute_value": "Preto", "abbr": "PR"},
                {"attribute_value": "Azul", "abbr": "AZ"},
                {"attribute_value": "Vermelho", "abbr": "VM"},
                {"attribute_value": "Bege", "abbr": "BG"},
                {"attribute_value": "Cinza", "abbr": "CZ"},
            ]
        })
        attr.insert(ignore_permissions=True)
        print("Created: Cor")
    else:
        print("Already exists: Cor")
    frappe.db.commit()

    # 2. Template Item with barcode
    if not frappe.db.exists("Item", "CR-001"):
        t = frappe.get_doc({
            "doctype": "Item",
            "item_code": "CR-001",
            "item_name": "Cortina Roman 2.5m",
            "item_group": "Products",
            "stock_uom": "Nos",
            "has_variants": 1,
            "variant_based_on": "Item Attribute",
            "attributes": [{"attribute": "Cor"}],
            "barcodes": [{"barcode": "6901234567890", "barcode_type": "Code128"}],
        })
        t.insert(ignore_permissions=True)
        print("Created: CR-001")
    else:
        print("Already exists: CR-001")
    frappe.db.commit()

    # 3. Variants
    colors = [("Branco","BR"),("Preto","PR"),("Azul","AZ"),
              ("Vermelho","VM"),("Bege","BG"),("Cinza","CZ")]
    for name, abbr in colors:
        vc = "CR-001-" + abbr
        if not frappe.db.exists("Item", vc):
            v = frappe.get_doc({
                "doctype": "Item",
                "item_code": vc,
                "item_name": "Cortina Roman 2.5m / " + name,
                "item_group": "Products",
                "stock_uom": "Nos",
                "variant_of": "CR-001",
                "attributes": [{"attribute": "Cor", "attribute_value": name}],
            })
            v.insert(ignore_permissions=True)
            print("Created: " + vc)
        else:
            print("Exists: " + vc)
    frappe.db.commit()
    print("=== Test data created! ===")


if __name__ == "__main__":
    create_test_data()


def fix_is_billing_contact():
    "Add missing is_billing_contact custom field to Contact doctype."
    import frappe

    fieldname = "is_billing_contact"
    if frappe.db.exists("Custom Field", {"dt": "Contact", "fieldname": fieldname}):
        print("Already exists:", fieldname)
        return

    doc = frappe.get_doc({
        "doctype": "Custom Field",
        "dt": "Contact",
        "fieldname": fieldname,
        "label": "Is Billing Contact",
        "fieldtype": "Check",
        "insert_after": "is_primary_contact",
    })
    doc.insert(ignore_permissions=True)
    frappe.db.commit()
    print("Created:", fieldname)



@frappe.whitelist()
def get_items(start, page_length, price_list, item_group, pos_profile, search_term=''):
    """POS 商品加载：默认不返回商品（扫码/搜索才加载），避免全量物料导致卡顿；

    附加 has_variants 标记：前端据此拦截「模板物料直接加购」（模板无价会报
    错「未设置物料价格」），改为弹颜色选择框让收银员选具体颜色。
    """
    if not search_term:
        return {"items": []}

    from erpnext.selling.page.point_of_sale import point_of_sale as pos_page

    result = pos_page.get_items(start, page_length, price_list, item_group, pos_profile, search_term)
    items = (result or {}).get("items") or []
    if items:
        codes = [it.get("item_code") for it in items if it.get("item_code")]
        if codes:
            hv_map = dict(
                frappe.db.get_all(
                    "Item",
                    filters={"name": ["in", codes]},
                    fields=["name", "has_variants"],
                    as_list=True,
                )
            )
            for it in items:
                it["has_variants"] = 1 if hv_map.get(it.get("item_code")) else 0
    return result
