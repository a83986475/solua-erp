"""Run with Python; isolated fixtures never connect to a site or write business data."""
import importlib.util
import json
from pathlib import Path
import sys
import types
from copy import deepcopy

from jinja2 import Environment, StrictUndefined

ROOT = Path(__file__).resolve().parents[1]


class Doc(dict):
    __getattr__ = dict.__getitem__
    __setattr__ = dict.__setitem__

    def is_new(self):
        return False

    def check_permission(self, *args):
        pass


def fail(message):
    raise ValueError(message)


reads = []
order = Doc(customer="C", shipping_address_name="STORE-A", custom_store_name="A", custom_store_phone="111", contact_person="CONTACT-A")
def get_doc(dt, name):
    reads.append((dt, name))
    return order if dt == "Sales Order" else Doc()


frappe = types.ModuleType("frappe")
frappe._ = lambda text: text
frappe.throw = fail
frappe.get_meta = lambda dt: types.SimpleNamespace(has_field=lambda field: field != "phone")
def db_get_value(dt, name, field, **kwargs):
    if dt == "Sales Order":
        return order.get(field)
    if dt == "Company" and field == "tax_id":
        return "COMPANY-NUIT"
    if dt == "Contact" and name == "CONTACT-A":
        return "STORE-A"
    if dt == "Item" and kwargs.get("as_dict"):
        return Doc(variant_of="", description="<p>Standard description</p>", custom_item_description_pt="Cortina <b>vermelha</b>")
    return "888"


set_value_calls = []
def db_set_value(dt, name, fields):
    set_value_calls.append((dt, name, dict(fields)))
    if dt == "Sales Order":
        order.update(fields)
frappe.db = types.SimpleNamespace(get_value=db_get_value, set_value=db_set_value)
frappe.db.exists = lambda dt, filters: dt == "Dynamic Link"
frappe.get_doc = get_doc
frappe.get_all = lambda dt, *a, **k: [Doc(barcode="6901234567892", barcode_type="EAN")] if dt == "Item Barcode" else []
frappe.get_list = lambda *a, **k: []
def fmt_money(value, currency, precision=2):
    return f"{value or 0:.{precision}f} {currency}"
frappe.utils = types.SimpleNamespace(fmt_money=fmt_money)
sys.modules["frappe"] = frappe
color = types.ModuleType("solua_home.printing.color_card")
color.get_item_color_info = lambda code: {"order_code":code,"color_code":"01","color_name":"Red","image":"/red.png", "template_code":"STYLE", "card_url":"/colors?q=STYLE"}
sys.modules[color.__name__] = color
spec = importlib.util.spec_from_file_location("wholesale_candidate", ROOT / "printing/wholesale.py")
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)


def fixture(dt):
    return Doc(doctype=dt, name="CHECK-1", docstatus=0, company="Solua Home, Lda", customer="C",
        customer_name="Customer", tax_id="CUSTOMER-NUIT", shipping_address_name="STORE-A",
        shipping_address="Store address", address_display="WRONG BILLING", contact_display="Person",
        contact_mobile="999", contact_person="CONTACT-A", custom_store_name="A", custom_store_phone="", custom_invoice_plan="订单 CHECK-1 在签收后次日开票",
        custom_source_warehouse_address=module.COMPANY_ADDRESS_LINE, custom_departure_time="2026-09-15 10:00:00",
        driver_name="Driver", vehicle_no="ABC", driver="D", custom_driver_phone="",
        currency="MZN", grand_total=20, posting_date="2026-09-15", transaction_date="2026-09-15",
        items=[Doc(item_code="RED",item_name="Curtain",qty=2,rate=10,amount=20,uom="条",
                   against_sales_order="SO-1",so_detail="SOI-1",custom_ordered_qty=10,
                   custom_delivered_before_qty=3,custom_remaining_qty=5)])


so = fixture("Sales Order")
so.custom_store_phone = "111"
so.driver = so.driver_name = so.vehicle_no = ""
module.prepare_print_snapshot(so, "before_submit")
assert json.loads(so.custom_wholesale_snapshot)["company"]["nuit"] == "COMPANY-NUIT"
assert module.get_customer_print_info(so)["address"] == "Store address"
assert module.get_customer_print_info(so)["phone"] == "111"
legacy_so = Doc(so)
legacy_snapshot = json.loads(so.custom_wholesale_snapshot)
for legacy_item in legacy_snapshot["items"]:
    legacy_item["barcode"] = ""
    legacy_item["description"] = ""
legacy_so.custom_wholesale_snapshot = json.dumps(legacy_snapshot)
legacy_display = module.get_wholesale_print_data(legacy_so)["items"][0]
assert legacy_display["barcode"] == "6901234567892"
assert legacy_display["description"] == "Cortina vermelha"
assert json.loads(legacy_so.custom_wholesale_snapshot)["items"][0]["barcode"] == ""
dn = fixture("Delivery Note")
module.prepare_print_snapshot(dn, "before_submit")
stored = dn.custom_wholesale_snapshot
dn.shipping_address = "NEW ADDRESS"
dn.driver_name = "NEW DRIVER"
dn["items"][0].item_name = "NEW ITEM"
dn.custom_store_phone = "222"
dn.docstatus = 1
reads.clear()
assert module.get_wholesale_print_data(dn)["items"][0]["item_name"] == "Curtain"
assert module.get_customer_print_info(dn)["address"] == "Store address"
assert module.get_customer_print_info(dn)["phone"] == "999"  # snapshot froze the contact fallback
assert module.get_driver_phone(dn) == "888"
assert dn.custom_wholesale_snapshot == stored and not reads

# A submitted Delivery Note keeps an explicit store phone frozen in its print snapshot.
phone_note = fixture("Delivery Note")
phone_note.custom_store_phone = "222"
module.prepare_print_snapshot(phone_note, "before_submit")
phone_note.custom_store_phone = "333"
assert module.get_customer_print_info(phone_note)["phone"] == "222"
for key in ("vehicle_no", "driver"):
    bad = fixture("Delivery Note"); bad[key] = ""
    try: module.prepare_print_snapshot(bad, "before_submit")
    except ValueError: pass
    else: raise AssertionError("Missing mandatory value accepted: " + key)
# 2026-09-23 客户/门店一致性校验已按用户要求关闭：门店不同不再拦截。
bad = fixture("Delivery Note");bad.custom_store_name = "B"
module.prepare_print_snapshot(bad, "before_submit")
# 订单漏填门店时以送货单为准，不再拦截提交。
saved_store = order.custom_store_name
order.custom_store_name = ""
module.prepare_print_snapshot(fixture("Delivery Note"))
order.custom_store_name = saved_store
bad = fixture("Delivery Note");bad.custom_invoice_plan = "后续开票"
module.prepare_print_snapshot(bad)
returned_print=fixture("Delivery Note");returned_print.is_return=1
returned_print["items"][0].qty=-2
module.prepare_print_snapshot(returned_print)
returned_snapshot=module.get_wholesale_print_data(returned_print)["items"][0]
assert returned_snapshot["qty"]==-2 and returned_snapshot["remaining_qty"] is None

# 表格底部的总数量：空快照/缺行/字符串数字都不能破坏打印
assert module.get_print_total_qty({"items": [{"qty": 2}, {"qty": None}, {"qty": 0.5}]}) == 2.5
assert module.get_print_total_qty({"items": [{"qty": "3"}, {}]}) == 3
assert module.get_print_total_qty({"items": []}) == 0 and module.get_print_total_qty(None) == 0

# 拣货单：明细在 locations 子表，行要补色号/条码/描述，底部给需求与已拣合计
pick = Doc(doctype="Pick List", name="PL-CHECK-1", docstatus=1, company="Solua Home, Lda", purpose="Delivery",
           customer="C", customer_name="Customer", status="Completed", creation="2026-09-23 09:15:00",
           locations=[Doc(item_code="RED", item_name="Curtain", qty=2, picked_qty=2, uom="条",
                          warehouse="W1", sales_order="SO-1", description="<p>row desc</p>"),
                      Doc(item_code="BLUE", item_name="", qty=1.5, picked_qty=0, uom="条",
                          warehouse="W1", sales_order="", description="")])
pick_data = module.get_pick_list_print_data(pick)
assert pick_data["total_qty"] == 3.5 and pick_data["total_picked"] == 2, pick_data
assert pick_data["customer"] == "Customer" and pick_data["purpose"] == "Delivery"
assert pick_data["items"][0]["barcode"] == "6901234567892" and pick_data["items"][0]["color_code"] == "01"
assert pick_data["items"][0]["description"] == "Cortina vermelha"
assert pick_data["items"][0]["sales_order"] == "SO-1" and pick_data["items"][1]["item_name"] == "BLUE"
empty_pick = module.get_pick_list_print_data(Doc(doctype="Pick List", name="PL-2", docstatus=1, locations=[]))
assert empty_pick["items"] == [] and empty_pick["total_qty"] == 0 and empty_pick["total_picked"] == 0
assert module.get_pick_list_print_data(Doc(doctype="Pick List", name="PL-3", docstatus=1))["total_qty"] == 0
assert module.format_print_qty(5.6) == "6"
assert module.format_print_money(430.49, currency="MZN") == "430 MZN"

env = Environment(undefined=StrictUndefined)
env.globals.update(frappe=frappe, get_wholesale_print_data=module.get_wholesale_print_data,
                  format_print_money=module.format_print_money,
                  format_print_qty=module.format_print_qty,
                  get_print_total_qty=module.get_print_total_qty,
                  get_solua_print_css=module.get_solua_print_css,
                  get_pick_list_print_data=module.get_pick_list_print_data,
                  get_delivery_invoice_names=lambda name: [], get_color_card_qr_img=lambda name: "")
for folder, document in (("sales_order_wholesale_color",so),("delivery_note_guia_remessa",dn)):
    fmt = json.loads((ROOT / "print_format" / folder / (folder + ".json")).read_text(encoding="utf-8"))
    assert fmt["html"] and fmt["raw_printing"] == 0 and not fmt["raw_commands"]
    assert fmt["module"] == "Solua Wholesale"
    html = env.from_string(fmt["html"]).render(doc=document)
    assert "Curtain" in html and "COMPANY-NUIT" in html and "CUSTOMER-NUIT" in html and "20 MZN" in html
    if folder == "sales_order_wholesale_color":
        for header in ("Artigo / 商品", "SKU / 货号", "Código de cor fixo / 固定色号"):
            assert header in html  # legacy documents default the fixed code column to visible
        assert "6901234567892" in html and "Cortina vermelha" in html and "描述 / Descrição" in html
    assert "WRONG BILLING" not in html and "NEW ADDRESS" not in html
    # 明细表格最下面一行是总数量（fixture 只有一行 qty=2）
    assert "Total Qty / 总数量" in html
    assert "</td><td style='text-align:right'><b>2</b></td>" in html, folder
    option_doc=Doc(document)
    option_snapshot=json.loads(option_doc.custom_wholesale_snapshot)
    option_snapshot["items"][0]["template_code"]="STYLE"
    option_doc.custom_wholesale_snapshot=json.dumps(option_snapshot)
    env.globals["get_color_card_qr_img"]=lambda name:"data:image/png;base64,QR_TEST"
    for images,qr in ((0,0),(1,0),(0,1),(1,1)):
        option_doc.custom_print_color_images=images
        option_doc.custom_print_color_qr=qr
        rendered=env.from_string(fmt["html"]).render(doc=option_doc)
        assert ('class="photo"' in rendered)==bool(images)
        assert ('class="qr"' in rendered)==bool(qr)
    if folder in ("sales_order_wholesale_color", "delivery_note_guia_remessa"):
        assert "<colgroup>" not in fmt["html"]  # no reserved width for hidden columns
        for item_name in (0, 1):
            for sku in (0, 1):
                for color_code in (0, 1):
                    for description in (0, 1):
                        for cor in (0, 1):
                            option_doc.custom_print_item_name = item_name
                            option_doc.custom_print_sku = sku
                            option_doc.custom_print_color_code = color_code
                            option_doc.custom_print_description = description
                            option_doc.custom_print_cor = cor
                            rendered = env.from_string(fmt["html"]).render(doc=option_doc)
                            assert ("Artigo / 商品" in rendered) == bool(item_name)
                            assert ("SKU / 货号" in rendered) == bool(sku)
                            assert ("固定色号" in rendered) == bool(color_code)
                            assert ("Cor / 颜色" in rendered) == bool(cor)
                            assert ("描述 / Descrição" in rendered) == bool(description)
    if folder == "delivery_note_guia_remessa":
        assert "table-layout:fixed" not in fmt["css"]
    env.globals["get_color_card_qr_img"]=lambda name:""
# The wholesale invoice must stay an ordinary editable Jinja format, never a raw-printing one.
# 重构版销售单格式与生产上的旧版（批发销售单（颜色版））并存，所以仓库文件名/记录名都是新的
invoice_folder = "sales_invoice_wholesale_color_v2"
invoice_fmt = json.loads((ROOT / "print_format" / invoice_folder / (invoice_folder + ".json")).read_text(encoding="utf-8"))
# module 必须是真实存在的 Module Def（本 app 只有 Solua Wholesale），否则建记录会被链接校验拦下
assert invoice_fmt["doc_type"] == "Sales Invoice" and invoice_fmt["module"] == "Solua Wholesale"
assert invoice_fmt["name"] == "批发销售单（颜色版）新版", "重构版不能占用旧版记录名"
assert invoice_fmt["custom_format"] == 1 and invoice_fmt["standard"] == "No" and invoice_fmt["disabled"] == 0
assert invoice_fmt["html"] and invoice_fmt["raw_printing"] == 0 and not invoice_fmt["raw_commands"]
env.globals["_"] = lambda text: text
env.globals["get_item_color_info"] = lambda code: Doc(order_code="STYLE-01", color_code="01", color_name="Red",
                                                      display_name="Red curtain", image="/red.png",
                                                      template_code="STYLE", card_url="/colors?q=STYLE")
env.globals["get_color_card_qr_img"] = lambda name: "data:image/png;base64,QR_TEST"
# Sales Invoice now uses the same shared data path as SO and DN, including real
# barcode lookup and Portuguese description fallback.
invoice = Doc(
    doctype="Sales Invoice", name="ACC-SINV-CHECK-1", docstatus=1, company="Solua Home, Lda",
    customer="C", customer_name="Customer", posting_date="2026-09-21", currency="MZN", grand_total=40,
    custom_print_color_images=1, custom_print_color_qr=1, custom_print_item_name=1, custom_print_sku=1,
    custom_print_color_code=1, custom_print_description=1,
    items=[Doc(item_code="SH151046-01", item_name="Curtain", qty=2, rate=20, amount=40, uom="条")])
rendered_invoice = env.from_string(invoice_fmt["html"]).render(doc=invoice)
assert "SH151046-01" in rendered_invoice and "6901234567892" in rendered_invoice
assert "Cortina vermelha" in rendered_invoice and "40 MZN" in rendered_invoice
assert "wholesale-image" in rendered_invoice and "QR_TEST" in rendered_invoice
assert "<style>" in rendered_invoice and "{%" not in rendered_invoice
assert "Descrição" in rendered_invoice and "SKU / 货号" in rendered_invoice
assert "Total Qty / 总数量" in rendered_invoice
assert "</td><td style='text-align:right'><b>2</b></td>" in rendered_invoice
# 拣货单打印格式：标准格式没有总数量，这份新格式有
pick_fmt = json.loads((ROOT / "print_format/pick_list_color/pick_list_color.json").read_text(encoding="utf-8"))
assert pick_fmt["doc_type"] == "Pick List" and pick_fmt["module"] == "Solua Wholesale"
assert pick_fmt["custom_format"] == 1 and pick_fmt["standard"] == "No" and pick_fmt["disabled"] == 0
assert pick_fmt["raw_printing"] == 0 and not pick_fmt["raw_commands"]
rendered_pick = env.from_string(pick_fmt["html"]).render(doc=pick)
assert "Pick List / 拣货单" in rendered_pick and "{%" not in rendered_pick
for header in ("SKU / 货号", "Código de cor / 色号", "条码 / Código de barras", "描述 / Descrição", "Armazém / 仓库"):
    assert header in rendered_pick, header
assert "Total Qty / 总数量" in rendered_pick
assert "<b>4</b>" in rendered_pick and "<b>2</b>" in rendered_pick
assert "6901234567892" in rendered_pick and "Cortina vermelha" in rendered_pick and "SO-1" in rendered_pick
assert "非正式凭证" not in rendered_pick  # 已提交的拣货单不背"草稿"标签
assert "非正式凭证" in env.from_string(pick_fmt["html"]).render(doc=Doc(pick, docstatus=0))
assert "非正式凭证" in env.from_string(pick_fmt["html"]).render(doc=Doc(pick, docstatus=2))
print("PASS: SO without transport; DN required fields/store; stored snapshot immutability; invoice barcode/description; independent column switches; pick list totals")

# Customer ownership and contact-address linkage fail closed.
frappe.db.exists=lambda dt,filters:False
try: module.prepare_print_snapshot(fixture("Sales Order"))
except ValueError: pass
else: raise AssertionError("Foreign customer address accepted")
frappe.db.exists=lambda dt,filters:dt=="Dynamic Link"
bad=fixture("Sales Order");bad.contact_person="CONTACT-OTHER-STORE"
try: module.prepare_print_snapshot(bad)
except ValueError: pass
else: raise AssertionError("Contact linked to a different store accepted")

saved_get_all,saved_get_list=frappe.get_all,frappe.get_list
frappe.has_permission=lambda *a,**k:True
def invoice_parents(dt,filters,**kwargs):
    assert dt=="Sales Invoice Item" and filters=={"delivery_note":"CHECK-1"}
    return ["INVOICE-LINKED"]
def permitted_invoices(dt,filters,**kwargs):
    assert dt=="Sales Invoice" and filters=={"name":["in",["INVOICE-LINKED"]],"docstatus":1}
    return ["INVOICE-LINKED"]
frappe.get_all,frappe.get_list=invoice_parents,permitted_invoices
assert module.get_delivery_invoice_names("CHECK-1")==["INVOICE-LINKED"]
assert dn.custom_wholesale_snapshot==stored
frappe.has_permission=lambda *a,**k:False
assert module.get_delivery_invoice_names("CHECK-1")==[]
frappe.get_all,frappe.get_list=saved_get_all,saved_get_list

if "--pdf-html" in sys.argv:
    output=ROOT/"tests"/"artifacts"
    output.mkdir(exist_ok=True)
    for folder,document in (("sales_order_wholesale_color",so),("delivery_note_guia_remessa",dn)):
        fmt=json.loads((ROOT/"print_format"/folder/(folder+".json")).read_text(encoding="utf-8"))
        snapshot=json.loads(document.custom_wholesale_snapshot)
        snapshot["items"]=[dict(snapshot["items"][0],item_name=("长名称窗帘 / Cortina com descrição longa " * 3)+str(i)) for i in range(48)]
        document.custom_wholesale_snapshot=json.dumps(snapshot)
        html=env.from_string(fmt["html"]).render(doc=document)
        (output/(folder+".html")).write_text("<!doctype html><meta charset='utf-8'><style>body{font-family:Arial,'Microsoft YaHei';margin:0}"+fmt["css"]+"</style><div class='print-format'>"+html+"</div>",encoding="utf-8")
    print("PDF HTML fixtures:",output)

# Order quantities are compared in stock UOM under the same order-row lock.
utils = types.ModuleType("frappe.utils")
utils.flt = lambda value: float(value or 0)
utils.cint = lambda value: int(value or 0)
sys.modules["frappe.utils"] = utils
stock_spec = importlib.util.spec_from_file_location("stock_candidate", ROOT / "api/stock.py")
stock = importlib.util.module_from_spec(stock_spec);stock_spec.loader.exec_module(stock)
sys.modules["solua_home.api.stock"] = stock

# Delivery Notes created from one Sales Order inherit the editable store phone;
# a value already entered on the Delivery Note wins.
copy_note = fixture("Delivery Note")
copy_note.custom_store_phone = ""
stock.validate_delivery_note(copy_note)
assert copy_note.custom_store_phone == "111"
override_note = fixture("Delivery Note")
override_note.custom_store_phone = "222"
stock.validate_delivery_note(override_note)
assert override_note.custom_store_phone == "222"
# 订单漏填的门店/电话/开票安排由送货单回填，只补空、不覆盖。
set_value_calls.clear()
order.custom_store_name = ""
order.custom_store_phone = ""
order.custom_invoice_plan = ""
backfill_note = fixture("Delivery Note")
backfill_note.custom_store_phone = "222"
stock.validate_delivery_note(backfill_note)
assert set_value_calls and set_value_calls[0][:2] == ("Sales Order", "SO-1")
assert order.custom_store_name == "A" and order.custom_store_phone == "222"
assert order.custom_invoice_plan == "订单 CHECK-1 在签收后次日开票"
set_value_calls.clear()
compat_queries = []
def compatibility_sql(query, args, **kwargs):
    compat_queries.append((query, args))
    if "tabSales Order Item" in query:
        return [Doc(parent="SO-1", item_code="RED", stock_qty=20)]
    return [[6]]
frappe.db.sql = compatibility_sql
dn_format = json.loads((ROOT / "print_format" / "delivery_note_guia_remessa" / "delivery_note_guia_remessa.json").read_text(encoding="utf-8"))
def render_delivery(rows, ordered_before=None, current_remaining=None):
    document = fixture("Delivery Note")
    document.docstatus = 1
    document.custom_wholesale_snapshot = None
    document.items = rows
    if ordered_before is not None:
        document.custom_print_ordered_before = ordered_before
    if current_remaining is not None:
        document.custom_print_current_remaining = current_remaining
    data = module.get_wholesale_print_data(document)
    return env.from_string(dn_format["html"]).render(doc=document), data

unlinked = Doc(item_code="RED", item_name="Curtain", qty=1, rate=1, amount=1, uom="条",
               custom_ordered_qty=0, custom_delivered_before_qty=0, custom_remaining_qty=0)
html, data = render_delivery([unlinked])
assert "Quantidade encomendada / 订购数量" not in html and data["has_order_linkage"] is False
linked = Doc(item_code="RED", item_name="Curtain", qty=2, rate=1, amount=2, uom="条",
             against_sales_order="SO-1", so_detail="SOI-1", conversion_factor=2,
             custom_ordered_qty=0, custom_delivered_before_qty=0, custom_remaining_qty=0)
html, data = render_delivery([linked])
assert "Quantidade encomendada / 订购数量" in html and data["items"][0]["ordered_qty"] == 10
assert data["items"][0]["delivered_before_qty"] == 3 and data["items"][0]["remaining_qty"] == 5
assert "Esta entrega / Restante<br>本次 / 剩余" in html and ">Qtd.<" not in html
html, _ = render_delivery([linked], current_remaining=0)
assert "Esta entrega / Restante<br>本次 / 剩余" not in html and '<th class="col-qty">Qtd.</th>' in html
assert "<td class='col-qty num'>2</td>" in html and "2.0" not in html
html, _ = render_delivery([linked], ordered_before=0)
assert "Quantidade encomendada / 订购数量" not in html
missing_link = Doc(item_code="RED", item_name="Curtain", qty=1, rate=1, amount=1, uom="条",
                   against_sales_order="SO-1", conversion_factor=1,
                   custom_ordered_qty=0, custom_delivered_before_qty=0, custom_remaining_qty=0)
html, data = render_delivery([missing_link])
assert "Quantidade encomendada / 订购数量" in html and "—" in html and data.get("delivery_quantity_error")
mixed = Doc(item_code="BLUE", item_name="Blue", qty=1, rate=1, amount=1, uom="条",
            custom_ordered_qty=0, custom_delivered_before_qty=0, custom_remaining_qty=0)
html, data = render_delivery([linked, mixed])
assert "Quantidade encomendada / 订购数量" in html and data["items"][1]["ordered_qty"] is None
assert data.get("delivery_quantity_error")
history_result = stock.get_delivery_snapshot_quantities(
    Doc(name="CURRENT-DN", is_return=0, items=[Doc(item_code="RED", qty=2, conversion_factor=2,
         against_sales_order="SO-1", so_detail="SOI-1")]), lock=False, strict=True)
assert history_result[0]["ordered_qty"] == 10 and history_result[0]["delivered_before_qty"] == 3
assert history_result[0]["remaining_qty"] == 5
assert "d.docstatus=1" in compat_queries[-1][0] and "d.name<>%s" in compat_queries[-1][0]
print("PASS: delivery first/second batch, conversion factor, current/cancelled exclusion; read-only zero recovery; missing linkage; manual column switch")
queries = []
def sql(query, args, **kwargs):
    queries.append(query)
    if "FOR UPDATE" in query:
        return [Doc(parent="SO-1",item_code="RED",stock_qty=12)]
    assert "i.stock_qty" in query and "d.docstatus=1" in query
    return [[4]]
frappe.db.sql = sql
line = Doc(item_code="RED",so_detail="SOI-1",against_sales_order="SO-1",qty=2,conversion_factor=2)
note = types.SimpleNamespace(name="DN-MEMORY",items=[line],get=lambda key:False)
stock.prepare_delivery_snapshot(note)
assert (line.custom_ordered_qty,line.custom_delivered_before_qty,line.custom_remaining_qty)==(6,2,2)
assert "FOR UPDATE" in queries[0]
line.qty=5
try: stock.prepare_delivery_snapshot(note)
except ValueError: pass
else: raise AssertionError("Overdelivery accepted")
line.qty=1;line.conversion_factor=0
try: stock.prepare_delivery_snapshot(note)
except ValueError: pass
else: raise AssertionError("Zero conversion accepted")
print("PASS: stock-UOM quantities, order-line locking, overdelivery and zero conversion rejection")

# Two colours, two deliveries, repeated order detail rows, and signed returns.
history={"R":0,"B":0}
def batch_sql(query,args,**kwargs):
    if "FOR UPDATE" in query:
        return [Doc(parent="SO-1",item_code=args[0],stock_qty=10)]
    return [[history[args[1]]]]
frappe.db.sql=batch_sql
def delivery(rows,returned=False):
    return types.SimpleNamespace(name="MEMORY-DN",items=rows,get=lambda key:returned if key=="is_return" else None)
def row(code,qty):
    return Doc(item_code=code,so_detail=code,against_sales_order="SO-1",qty=qty,conversion_factor=1)
first=[row("R",3),row("B",4)]
stock.prepare_delivery_snapshot(delivery(first));assert [r.custom_remaining_qty for r in first]==[7,6]
history.update(R=3,B=4)
second=[row("R",2),row("R",5),row("B",6)]
stock.prepare_delivery_snapshot(delivery(second));assert [r.custom_remaining_qty for r in second]==[5,0,0]
history["R"]=1  # Previously submitted -2 return included in signed SUM(stock_qty).
later=row("R",9);stock.prepare_delivery_snapshot(delivery([later]));assert later.custom_remaining_qty==0
returned=row("R",-2)
stock.prepare_delivery_snapshot(delivery([returned],True));assert "custom_remaining_qty" not in returned
stock.validate_transaction_quantities(Doc(is_return=1,items=[returned]))
print("PASS: two colours/two trips; repeated SO rows; prior signed return; native return quantity sign")

# Nonempty financial fixtures; get_list emulates role + row permission filtering.
from datetime import datetime
utils.nowdate=lambda:"2026-09-15"
utils.now_datetime=lambda:datetime(2026,9,15,12)
frappe.utils=utils
frappe.session=types.SimpleNamespace(user="manager")
frappe.whitelist=lambda:lambda fn:fn
frappe.read_only=lambda:lambda fn:fn
stock_settings_warehouse = "W1"
user_default_warehouse = "W2"
frappe.db.get_single_value = lambda dt, field: stock_settings_warehouse if (dt, field) == ("Stock Settings", "default_warehouse") else None
frappe.defaults=types.SimpleNamespace(get_user_default=lambda key:user_default_warehouse if key=="Warehouse" else None)
frappe.get_meta=lambda dt:types.SimpleNamespace(has_field=lambda field:field!="base_outstanding_amount")
frappe.db.exists=lambda *a,**k:True
role={"manager"}
frappe.has_permission=lambda dt,ptype="read": role=={"manager"} or dt in {"Company","Warehouse","Item","Bin"}
frappe.get_roles=lambda user=None: role
def invoice(name,amount,outstanding=0,rate=1,**extra):
    return Doc(name=name,company="Solua Home, Lda",docstatus=1,posting_date="2026-09-15",
        base_grand_total=amount,outstanding_amount=outstanding,conversion_rate=rate,
        due_date="2026-09-14",customer="C",is_return=int(amount<0),custom_is_topup=0,**extra)
tables={
 "Company":[Doc(name="Solua Home, Lda",default_currency="MZN")],
 "Warehouse":[Doc(name="W1",company="Solua Home, Lda",is_group=0),
              Doc(name="W2",company="Solua Home, Lda",is_group=0),
              Doc(name="W-GROUP",company="Solua Home, Lda",is_group=1),
              Doc(name="W-OTHER",company="Other Company",is_group=0)],
 "Sales Invoice":[invoice("SI",100,10,2),invoice("MERGED",200,20,is_consolidated=1),
                  invoice("RETURN",-25),invoice("HIDDEN",900)],
 "POS Invoice":[invoice("POS",50,5),invoice("POS-MERGED",200,20,consolidated_invoice="MERGED")],
 "Item":[Doc(name="RED",item_name="Red",image="",variant_of="STYLE",disabled=0,is_stock_item=1,has_variants=0,stock_uom="条"),
         Doc(name="STYLE",item_name="Style",image="",variant_of="",disabled=0,is_stock_item=1,has_variants=1,stock_uom="条")],
 "Item Reorder":[Doc(parent="RED",parenttype="Item",warehouse="W1",warehouse_reorder_level=5),
                 Doc(parent="STYLE",parenttype="Item",warehouse="W1",warehouse_reorder_level=9),
                 Doc(parent="RED",parenttype="Item",warehouse="W2",warehouse_reorder_level=100)],
 "Bin":[Doc(name="BIN",item_code="RED",warehouse="W1",actual_qty=2)],
 "Item Barcode":[Doc(parent="RED",parenttype="Item",barcode="SHARED"),Doc(parent="HIDDEN",parenttype="Item",barcode="SHARED")],
}
def matches(row,filters):
    for key,want in filters.items():
        value=row.get(key)
        if isinstance(want,(list,tuple)):
            op,target=want
            if op=="in" and value not in target:return False
            if op=="not in" and value in target:return False
            if op==">" and not (value is not None and value>target):return False
            if op=="<" and not (value is not None and value<target):return False
            if op=="is" and target=="not set" and value:return False
        elif value!=want:return False
    return True
def listing(dt,filters=None,fields=None,limit_page_length=0,**kwargs):
    rows=[r.copy() for r in tables.get(dt,[]) if r.get("name")!="HIDDEN" and matches(r,filters or {})]
    if fields and isinstance(fields[0],dict):
        result={}
        for f in fields:
            result[f["as"]]=len(rows) if "COUNT" in f else sum(r.get(f["SUM"],0) for r in rows)
        return [Doc(result)]
    return [Doc(r) for r in (rows[:limit_page_length] if limit_page_length else rows)]
frappe.get_list=listing
frappe.get_all=listing
home_spec=importlib.util.spec_from_file_location("home_candidate",ROOT/"api/home.py")
home=importlib.util.module_from_spec(home_spec);home_spec.loader.exec_module(home)
result=home.get_dashboard_data()
assert result["warehouse"]=="W1"  # Stock Settings beats the user default.
assert home._resolve_warehouse(Doc(name="Solua Home, Lda"),"W2")=="W2"  # Explicit accessible warehouse wins.
assert home._resolve_warehouse(Doc(name="Solua Home, Lda"),"W-GROUP")=="W2"  # Group requests fall back safely.
assert home._resolve_warehouse(Doc(name="Solua Home, Lda"),"W-OTHER")=="W2"  # Cross-company requests are rejected.
user_default_warehouse = "W-MISSING"
assert home._resolve_warehouse(Doc(name="Solua Home, Lda"),"W-OTHER")=="W1"  # Final fallback is an accessible leaf.
user_default_warehouse = "W2"
assert result["invoiced_today"]["amount"]==325  # 100+200-25+50; linked POS excluded.
assert result["outstanding"]["amount"]==45  # 10*2 + 20 + 5; no second advance subtraction.
assert result["sales"]["return_count"]==1
assert home._low_stock("W1")["count"]==1
assert home._low_stock("W1")["items"][0]["actual_qty"]==2
# 资料准备 must name the items behind every count, not just report how many.
item_data=home._item_data_status()
assert item_data["state"]=="ok" and item_data["item_count"]==2
assert item_data["checked_count"]==1 and item_data["template_count"]==1  # templates are not checked
assert item_data["missing_image"]==1 and item_data["missing_color_code"]==0
assert [issue["key"] for issue in item_data["issues"]]==["missing_image","missing_color_code"]
assert [issue["field"] for issue in item_data["issues"]]==["image","Cor"]
assert item_data["issues"][0]["count"]==1 and item_data["issues"][1]["count"]==0
assert [row["name"] for row in item_data["issues"][0]["items"]]==["RED"]
assert item_data["issues"][0]["items"][0]["item_name"]=="Red"
assert item_data["issues"][1]["items"]==[] and not item_data["issues"][1]["truncated"]
# STYLE is a template: no image and no colour code is its normal state, never a finding.
assert "STYLE" not in [row["name"] for issue in item_data["issues"] for row in issue["items"]]
tables["Item Variant Attribute"]=[Doc(parent="RED",parenttype="Item",attribute="Cor",attribute_value="Red"),
                                  Doc(parent="STYLE",parenttype="Item",attribute="Cor",attribute_value="Style")]
assert home._item_data_status()["missing_color_code"]==0  # native Cor is the current colour source
assert home._item_data_status()["issues"][1]["items"]==[]
tables["Item Variant Attribute"]=[]
assert home.get_dashboard_data()["item_data"]["issues"][0]["items"][0]["name"]=="RED"
assert [r.parent for r in home._list("Item Barcode",{"barcode":"SHARED"},["parent"])]==["RED"]
assert home.get_dashboard_data(company="Forbidden")["state"]=="no_permission"
tables["Bin"]=[]
assert home._low_stock("W1")["state"]=="incomplete" and home._low_stock("W1")["count"] is None
role.clear();role.add("warehouse")
assert home.get_dashboard_data()["invoiced_today"]["state"]=="no_permission"
frappe.session.user="Guest"
assert home.get_dashboard_data()["state"]=="no_permission"
assert home.search_items("SHARED")["state"]=="no_permission"
assert home.get_color_variants(barcode="SHARED")["state"]=="no_permission"
print("PASS: nonempty SI/POS merge and return 325; FX outstanding 45; warehouse role/Guest/parent Item/company/warehouse/hidden Bin isolation; item-data drill-down names the items behind each count and skips templates")

# Cashier homepage mode: POS Profile membership (never a desk role) decides it.
tables["POS Profile User"]=[Doc(name="PPU",parent="收银方式1 - SH",user="pos1@solua.one",parenttype="POS Profile",pos_role=None)]
tables["POS Profile"]=[Doc(name="收银方式1 - SH",disabled=0)]
profile_disabled=0
saved_get_value=frappe.db.get_value
frappe.db.has_column=lambda dt,field: True
def fake_get_value(dt,name,field=None,**kwargs):
    if (dt,name)==("POS Profile","收银方式1 - SH"):return profile_disabled
    if dt=="POS Profile User":
        row=tables["POS Profile User"][0]
        filters=name
        if filters.get("user")!=row.user or filters.get("parent")!=row.parent:return None
        return getattr(row,field,None)
    return saved_get_value(dt,name,field)
frappe.db.get_value=fake_get_value
frappe.session.user="pos1@solua.one"
role.clear();role.add("POS Cashier")
assert home._pos_cashier_profile()=="收银方式1 - SH"
cashier=home.get_dashboard_data()
assert cashier["state"]=="ok" and cashier["home_mode"]=="pos"
assert cashier["pos_profile"]=="收银方式1 - SH"
assert "warehouse" not in cashier and "low_stock" not in cashier and "invoiced_today" not in cashier
assert "orders_pending" not in cashier and "item_data" not in cashier
assert cashier["stock_entry_types"]=={} and "permissions" in cashier
role.add("System Manager")  # a manager assigned to the profile keeps the full homepage
assert home._pos_cashier_profile() is None
assert home.get_dashboard_data()["home_mode"]=="desk"
role.discard("System Manager")
role.add("Accounts Manager")  # any POS manager role disables the cashier view
assert home._pos_cashier_profile() is None
role.discard("Accounts Manager")
# A shift supervisor (xPos POS Role Manager/Administrator) keeps the desk homepage.
tables["POS Profile User"][0].pos_role="Manager"
assert home._pos_cashier_profile() is None
assert home.get_dashboard_data()["home_mode"]=="desk"
tables["POS Profile User"][0].pos_role="Cashier"
assert home._pos_cashier_profile()=="收银方式1 - SH"
tables["POS Profile User"][0].pos_role=None
profile_disabled=1  # a disabled profile no longer identifies a cashier
assert home._pos_cashier_profile() is None
profile_disabled=0
frappe.session.user="another@solua.one"  # not on any profile
assert home._pos_cashier_profile() is None
frappe.session.user="manager"
frappe.db.get_value=saved_get_value
role.clear();role.add("manager")
assert home.get_dashboard_data()["home_mode"]=="desk"
print("PASS: cashier POS-only payload (profile membership, manager roles and disabled profiles keep the desk homepage)")

# Targeted installer: exercise actual field loop twice, then injected import error.
created_fields=set();installed_modules=set();module_inserts=0;imports=[];commits=[];rollbacks=[];module_map_refresh=[]
class InstallDoc(types.SimpleNamespace):
    def insert(self,**kwargs):
        global module_inserts
        if self.doctype=="Custom Field":created_fields.add((self.dt,self.fieldname))
        elif self.doctype=="Module Def":module_inserts+=1;installed_modules.add(self.module_name)
        else:raise AssertionError("Unexpected installer mutation")
        return self
    def load_assets(self):
        self.script="candidate JS";self.style="candidate CSS"
def install_get_doc(arg,name=None):
    if isinstance(arg,dict):return InstallDoc(**arg)
    if arg=="Page":return InstallDoc(name="solua-home",module="Solua Wholesale")
    if arg=="Print Format":return InstallDoc(html="<p>HTML</p>",raw_printing=0,module="Solua Home 定制" if name == "批发销售单（颜色版）" else "Solua Wholesale")
    raise AssertionError(arg)
frappe.get_doc=install_get_doc
frappe.get_attr=lambda name:lambda:None
frappe.db.exists=lambda dt,filters: filters in installed_modules if dt=="Module Def" else (filters["dt"],filters["fieldname"]) in created_fields
frappe.db.get_value=lambda dt,name,fields,as_dict=False: InstallDoc(name=name,app_name="solua_home") if dt=="Module Def" and name in installed_modules else None
frappe.cache=lambda: types.SimpleNamespace(delete_value=lambda key:module_map_refresh.append(key))
frappe.setup_module_map=lambda include_all_apps=True:module_map_refresh.append(("setup",include_all_apps))
frappe.db.commit=lambda:commits.append(1)
frappe.db.rollback=lambda:rollbacks.append(1)
frappe.make_property_setter=lambda *args,**kwargs: None
frappe.clear_cache=lambda **kwargs: None
frappe.get_meta=lambda dt: types.SimpleNamespace(fields=[])
importer=types.ModuleType("frappe.modules.import_file")
importer.import_file_by_path=lambda path,**kwargs:imports.append(path)
sys.modules[importer.__name__]=importer
modules_pkg=types.ModuleType("frappe.modules")
modules_pkg.__path__=[]
modules_pkg.get_module_path=lambda *args: "/virtual/solua_wholesale/page/solua_home"
sys.modules[modules_pkg.__name__]=modules_pkg
import os as _installer_test_os
_installer_test_isdir=_installer_test_os.path.isdir
_installer_test_os.path.isdir=lambda path: path=="/virtual/solua_wholesale/page/solua_home" or _installer_test_isdir(path)
install_spec=importlib.util.spec_from_file_location("installer_candidate",ROOT/"install.py")
installer=importlib.util.module_from_spec(install_spec);install_spec.loader.exec_module(installer)
installer.install_wholesale_only();field_count=len(created_fields)
installer.install_wholesale_only()
assert field_count==len(created_fields) and field_count>0 and installed_modules=={"Solua Wholesale"} and module_inserts==1
assert len(imports)==8 and len(commits)==2 and module_map_refresh==["app_modules",("setup",True),"app_modules",("setup",True)]
original_get_value=frappe.db.get_value
frappe.db.get_value=lambda dt,name,fields,as_dict=False: InstallDoc(name=name,app_name="Wrong App") if dt=="Module Def" else original_get_value(dt,name,fields,as_dict)
try:installer.install_wholesale_only()
except RuntimeError as exc:assert "Invalid Module Def" in str(exc)
else:raise AssertionError("Invalid Module Def accepted")
assert len(rollbacks)==1 and len(commits)==2
frappe.db.get_value=original_get_value
original_module_path=modules_pkg.get_module_path
modules_pkg.get_module_path=lambda *args: (_ for _ in ()).throw(RuntimeError("injected module path failure"))
try:installer.install_wholesale_only()
except RuntimeError as exc:assert "module path" in str(exc)
else:raise AssertionError("Missing module path rejected incorrectly")
assert len(rollbacks)==2 and len(commits)==2 and len(created_fields)==field_count
modules_pkg.get_module_path=original_module_path
def broken_import(*args,**kwargs):raise RuntimeError("injected import failure")
importer.import_file_by_path=broken_import
try:installer.install_wholesale_only()
except RuntimeError:pass
else:raise AssertionError("Import failure swallowed")
assert len(rollbacks)==3 and len(commits)==2
_installer_test_os.path.isdir=_installer_test_isdir
print("PASS: fresh module registration, idempotent rerun, strict module/path/import failures; three scoped imports")
