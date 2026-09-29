import json
from frappe.desk.form.meta import get_meta
from solua_home.api.home import get_color_variants

js = get_meta("Sales Order").get("__js") or ""
item_name = frappe.db.get_value("Item", "SH151015", "item_name")
name_lookup = get_color_variants(barcode=item_name, barcode_only=False) if item_name else {}
print(json.dumps({
    "hook": frappe.get_hooks("doctype_js").get("Sales Order"),
    "js_length": len(js),
    "contains_wholesale": "wholesale_forms" in js,
    "template_filter": "has_variants: 1" in js,
    "sku_name_label": "条码 / SKU / 物料名称" in js,
    "old_warehouse_prompt": "请选择明确订单仓库或仓库范围" in js,
    "item_name_lookup": {"item_name": item_name, "state": name_lookup.get("state"), "templates": len(name_lookup.get("templates") or [])},
}, ensure_ascii=False))
