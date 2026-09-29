import json
from pathlib import Path

import frappe
from frappe.utils.file_manager import save_file


BASE = Path('/tmp/solua_moz_curtains')
PAYLOAD = json.loads((BASE / 'erp_import_payload.json').read_text(encoding='utf-8'))
PRODUCTS = PAYLOAD['products']
VARIANTS = PAYLOAD['variants']
PRICES = PAYLOAD['prices']
WAREHOUSE = 'Receiving - SH'
COMPANY = 'Solua Home, Lda'


def has_field(fieldname):
    return frappe.db.has_column('Item', fieldname)


def set_custom(doc, fieldname, value):
    if has_field(fieldname):
        doc.set(fieldname, value)


def upsert_item(product, template=False):
    code = product['itemCode']
    doc = frappe.get_doc('Item', code) if frappe.db.exists('Item', code) else frappe.new_doc('Item')
    doc.item_code = code
    doc.item_name = product['name']
    doc.description = product['description']
    doc.item_group = PAYLOAD['itemGroup']
    doc.stock_uom = PAYLOAD['stockUom']
    doc.is_stock_item = 1
    doc.valuation_rate = product['cost']
    doc.has_variants = 1 if template else 0
    doc.variant_based_on = 'Item Attribute' if template else None
    doc.attributes = []
    if template:
        doc.append('attributes', {'attribute': 'Cor'})
    set_custom(doc, 'custom_chinese_name', product['name'])
    set_custom(doc, 'custom_spu_code', product['spu'])
    set_custom(doc, 'custom_spec_summary', product['specification'])
    set_custom(doc, 'custom_order_code', code)
    set_custom(doc, 'custom_color_card_published', 1 if template else 0)

    barcode = str(product.get('barcode') or '').strip()
    existing_barcodes = {str(row.barcode).strip() for row in doc.barcodes if row.barcode}
    if barcode and barcode not in existing_barcodes:
        doc.append('barcodes', {'barcode': barcode, 'barcode_type': 'Code128'})

    doc.flags.ignore_permissions = True
    if doc.is_new():
        doc.insert(ignore_permissions=True)
    else:
        doc.save(ignore_permissions=True)
    return doc


def attach_main_image(item_code):
    item = frappe.get_doc('Item', item_code)
    if item.image:
        return item.image
    local_path = BASE / 'images' / f'{item_code}.png'
    if not local_path.exists() or local_path.stat().st_size <= 0:
        return ''
    existing = frappe.get_all(
        'File',
        filters={
            'attached_to_doctype': 'Item',
            'attached_to_name': item_code,
            'attached_to_field': 'image',
        },
        fields=['file_url'],
        limit=1,
    )
    if existing:
        item.image = existing[0].file_url
        item.save(ignore_permissions=True)
        return item.image
    file_doc = save_file(
        local_path.name,
        local_path.read_bytes(),
        'Item',
        item_code,
        is_private=0,
        df='image',
    )
    item.image = file_doc.file_url
    item.save(ignore_permissions=True)
    return item.image


def ensure_numeric_cor_values():
    values = sorted({str(v['colorCode']).zfill(2) for v in VARIANTS})
    attr = frappe.get_doc('Item Attribute', 'Cor')
    existing = {str(row.attribute_value) for row in attr.item_attribute_values}
    for value in values:
        if value not in existing:
            attr.append('item_attribute_values', {'attribute_value': value, 'abbr': value})
    if values and any(value not in existing for value in values):
        attr.save(ignore_permissions=True)
    return values


def create_or_update_variants():
    from erpnext.controllers.item_variant import create_variant

    products_by_code = {p['itemCode']: p for p in PRODUCTS}
    created = 0
    updated = 0
    for row in VARIANTS:
        code = row['itemCode']
        template_code = row['variantOf']
        product = products_by_code[template_code]
        if frappe.db.exists('Item', code):
            item = frappe.get_doc('Item', code)
            if item.variant_of != template_code:
                frappe.throw(f'{code} 已存在但所属模板不是 {template_code}')
            updated += 1
        else:
            item = create_variant(template_code, {'Cor': str(row['colorCode']).zfill(2)})
            item.item_code = code
            if item.item_code != code:
                frappe.throw(f'ERPNext 生成的变体编码 {item.item_code} 与预期 {code} 不一致')
            item.barcodes = []
            item.flags.ignore_permissions = True
            item.insert(ignore_permissions=True)
            created += 1

        item.item_name = row['itemName']
        item.description = product['description']
        item.stock_uom = PAYLOAD['stockUom']
        item.is_stock_item = 1
        item.valuation_rate = product['cost']
        item.barcodes = []
        set_custom(item, 'custom_chinese_name', row['itemName'])
        set_custom(item, 'custom_spu_code', product['spu'])
        set_custom(item, 'custom_spec_summary', product['specification'])
        set_custom(item, 'custom_pos_short_name', row['color'])
        set_custom(item, 'custom_color_code', str(row['colorCode']).zfill(2))
        set_custom(item, 'custom_order_code', code)
        item.flags.ignore_permissions = True
        item.save(ignore_permissions=True)
    return created, updated


def upsert_prices():
    created = 0
    updated = 0
    for row in PRICES:
        filters = {'item_code': row['itemCode'], 'price_list': row['priceList']}
        matches = frappe.get_all('Item Price', filters=filters, fields=['name'], limit=1)
        if matches:
            price = frappe.get_doc('Item Price', matches[0].name)
            updated += 1
        else:
            price = frappe.new_doc('Item Price')
            price.item_code = row['itemCode']
            price.price_list = row['priceList']
            created += 1
        price.price_list_rate = row['rate']
        price.currency = row['currency'] or 'MZN'
        price.uom = row['uom'] or PAYLOAD['stockUom']
        price.buying = int(row['buying'] or 0)
        price.selling = int(row['selling'] or 0)
        price.flags.ignore_permissions = True
        if price.is_new():
            price.insert(ignore_permissions=True)
        else:
            price.save(ignore_permissions=True)
    return created, updated


def create_opening_stock():
    variant_products = {row['variantOf'] for row in VARIANTS}
    rows = [
        p for p in PRODUCTS
        if p['itemCode'] not in variant_products and p.get('actualQty') not in (None, '') and float(p['actualQty']) > 0
    ]
    if not rows:
        return {'status': 'skipped', 'reason': '没有明确可入库数量'}

    existing = frappe.get_all(
        'Stock Reconciliation Item',
        filters={'item_code': ['in', [p['itemCode'] for p in rows]], 'warehouse': WAREHOUSE},
        fields=['parent', 'item_code'],
        limit=1,
    )
    if existing:
        return {'status': 'skipped', 'reason': f'仓库已有相关盘点记录 {existing[0].parent}'}

    stock = frappe.new_doc('Stock Reconciliation')
    stock.company = COMPANY
    stock.purpose = 'Opening Stock'
    stock.expense_account = '1910 - Temporary Opening - SH'
    stock.posting_date = '2026-09-19'
    stock.posting_time = '23:59:00'
    for p in rows:
        stock.append('items', {
            'item_code': p['itemCode'],
            'warehouse': WAREHOUSE,
            'qty': int(p['actualQty']),
            'valuation_rate': p['cost'],
        })
    stock.flags.ignore_permissions = True
    stock.insert(ignore_permissions=True)
    stock.submit()
    return {
        'status': 'submitted',
        'name': stock.name,
        'warehouse': WAREHOUSE,
        'items': len(rows),
        'qty': sum(int(p['actualQty']) for p in rows),
    }


def create_variant_opening_stock():
    products_by_code = {p['itemCode']: p for p in PRODUCTS}
    order_totals = {}
    for row in VARIANTS:
        order_totals[row['variantOf']] = order_totals.get(row['variantOf'], 0) + int(row['orderQty'] or 0)

    rows = []
    for row in VARIANTS:
        product = products_by_code[row['variantOf']]
        total_order_qty = order_totals[row['variantOf']]
        actual_qty = int(product['actualQty'])
        if not total_order_qty or actual_qty % total_order_qty:
            frappe.throw(f"{row['variantOf']} 的总数量不能按色号件数整除")
        pack_size = actual_qty // total_order_qty
        rows.append({
            'item_code': row['itemCode'],
            'warehouse': WAREHOUSE,
            'qty': int(row['orderQty']) * pack_size,
            'valuation_rate': product['cost'],
        })

    existing = frappe.get_all(
        'Stock Reconciliation Item',
        filters={'item_code': ['in', [row['item_code'] for row in rows]], 'warehouse': WAREHOUSE},
        fields=['parent', 'item_code'],
        limit=1,
    )
    if existing:
        return {'status': 'skipped', 'reason': f'仓库已有相关变体盘点记录 {existing[0].parent}'}

    stock = frappe.new_doc('Stock Reconciliation')
    stock.company = COMPANY
    stock.purpose = 'Opening Stock'
    stock.expense_account = '1910 - Temporary Opening - SH'
    stock.posting_date = '2026-09-19'
    stock.posting_time = '23:59:00'
    for row in rows:
        stock.append('items', row)
    stock.flags.ignore_permissions = True
    stock.insert(ignore_permissions=True)
    stock.submit()
    return {
        'status': 'submitted',
        'name': stock.name,
        'warehouse': WAREHOUSE,
        'items': len(rows),
        'qty': sum(row['qty'] for row in rows),
    }


def run():
    numeric_values = ensure_numeric_cor_values()
    frappe.db.commit()

    variant_codes = {row['variantOf'] for row in VARIANTS}
    templates = [p for p in PRODUCTS if p['itemCode'] in variant_codes]
    direct = [p for p in PRODUCTS if p['itemCode'] not in variant_codes]
    for p in direct:
        upsert_item(p, template=False)
    for p in templates:
        upsert_item(p, template=True)
    frappe.db.commit()

    images = sum(1 for p in PRODUCTS if attach_main_image(p['itemCode']))
    frappe.db.commit()

    variant_created, variant_updated = create_or_update_variants()
    frappe.db.commit()

    price_created, price_updated = upsert_prices()
    frappe.db.commit()

    try:
        stock = create_opening_stock()
        variant_stock = create_variant_opening_stock()
        frappe.db.commit()
    except Exception:
        frappe.db.rollback()
        raise

    return {
        'status': 'ok',
        'item_count': len(PRODUCTS),
        'direct_item_count': len(direct),
        'template_count': len(templates),
        'variant_count': len(VARIANTS),
        'variant_created': variant_created,
        'variant_updated': variant_updated,
        'price_count': len(PRICES),
        'price_created': price_created,
        'price_updated': price_updated,
        'main_images': images,
        'cor_numeric_values': numeric_values,
        'opening_stock': stock,
        'variant_opening_stock': variant_stock,
        'variant_stock_note': '3 款模板的颜色级实际装箱数量未在源表中分配，未凭空拆分库存；待后续按颜色盘点后入库。',
    }


print(json.dumps(run(), ensure_ascii=False, default=str))
