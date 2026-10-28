import importlib.util
import json
import sys
import types
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
calls = []


class Response:
    status_code = 200

    def __init__(self, payload):
        self.payload = payload

    def json(self):
        return self.payload


class Requests:
    def post(self, url, **kwargs):
        calls.append((url, kwargs))
        return Response({"errcode": 0, "media_id": "MEDIA-1"} if "upload_media" in url else {"errcode": 0})


frappe = types.ModuleType("frappe")
frappe.conf = {"solua_wecom_webhook_url": "https://qyapi.weixin.qq.com/cgi-bin/webhook/send?key=secret"}
frappe.whitelist = lambda *args, **kwargs: (lambda function: function)
frappe.throw = lambda message: (_ for _ in ()).throw(ValueError(message))
frappe.log_error = lambda *args, **kwargs: None
sys.modules["frappe"] = frappe
sys.modules["requests"] = Requests()

export = types.ModuleType("solua_home.api.export")
sales_order = types.SimpleNamespace(name="SAL-ORD-2026-00058", doctype="Sales Order", custom_print_merge_order_code=1)
sales_order.get = lambda key, default=None: getattr(sales_order, key, default)
export.get_export_document = lambda doctype, name: sales_order if doctype == "Sales Order" else types.SimpleNamespace(name=name, doctype=doctype)
render_calls = []
export._render_document_pdf = lambda doc, print_format, merge_customer=False, doctype=None: (render_calls.append(merge_customer) or b"PDF")
export._sales_order_customer_pdf_filename = lambda doc: "AN_LAN_0058_10-15.pdf"
table_calls = []
export._customer_sales_order_table = lambda doc, merge_customer=True: (table_calls.append(merge_customer) or [["货号", "数量"], ["AN-LAN", 1]])
export.build_table = lambda doc: [["单号", doc.name], ["货号", "TEST"]]
export._xlsx_bytes = lambda table, sheet_name: b"XLSX"
sys.modules["solua_home.api.export"] = export
designer = types.ModuleType("solua_home.api.a4_designer")
designer._active_print_format = lambda doctype: "ORDER CONFIRMACAO(PT）"
sys.modules["solua_home.api.a4_designer"] = designer

spec = importlib.util.spec_from_file_location("wecom_candidate", ROOT / "api/wecom.py")
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)

assert module.send_sales_order_customer_pdf_to_wechat("SAL-ORD-2026-00058") == {"filename": "AN_LAN_0058_10-15.pdf"}
assert len(calls) == 2
assert calls[0][1]["files"]["media"][0] == "AN_LAN_0058_10-15.pdf"
assert calls[1][1]["json"] == {"msgtype": "file", "file": {"media_id": "MEDIA-1"}}
assert render_calls[-1] is True
sales_order.custom_print_merge_order_code = 0
assert module.send_sales_order_customer_pdf_to_wechat("SAL-ORD-2026-00058") == {"filename": "AN_LAN_0058_10-15.pdf"}
assert render_calls[-1] is False
assert module.send_sales_order_customer_xlsx_to_wechat("SAL-ORD-2026-00058") == {"filename": "AN_LAN_0058_10-15.xlsx"}
assert len(calls) == 6
assert calls[4][1]["files"]["media"][:2] == ("AN_LAN_0058_10-15.xlsx", b"XLSX")
assert calls[5][1]["json"] == {"msgtype": "file", "file": {"media_id": "MEDIA-1"}}
assert table_calls[-1] is False
sales_order.custom_print_merge_order_code = 1
assert module.send_sales_order_customer_xlsx_to_wechat("SAL-ORD-2026-00058") == {"filename": "AN_LAN_0058_10-15.xlsx"}
assert table_calls[-1] is True
assert module.send_document_pdf_to_wechat("Delivery Note", "MAT-DN-2026-00062") == {"filename": "MAT-DN-2026-00062.pdf"}
assert calls[8][1]["files"]["media"][:2] == ("MAT-DN-2026-00062.pdf", b"PDF")
assert module.send_document_xlsx_to_wechat("Pick List", "STO-PICK-2026-00020") == {"filename": "STO-PICK-2026-00020.xlsx"}
assert calls[10][1]["files"]["media"][:2] == ("STO-PICK-2026-00020.xlsx", b"XLSX")
assert module.send_document_pdf_to_wechat("Sales Invoice", "ACC-SINV-2026-00109") == {"filename": "ACC-SINV-2026-00109.pdf"}

class DB:
    def __init__(self):
        self.values = []

    def get_value(self, *args, **kwargs):
        return "不合并货号"

    def set_value(self, *args, **kwargs):
        self.values.append((args, kwargs))

    def commit(self):
        pass


frappe.db = DB()
frappe.utils = types.SimpleNamespace(now_datetime=lambda: "2026-10-24 12:00:00")
frappe.get_meta = lambda doctype: types.SimpleNamespace(has_field=lambda fieldname: True)
order_draft = types.SimpleNamespace(
    doctype="Sales Order",
    customer="HOME STORE, LDA",
    custom_print_merge_order_code=None,
    is_new=lambda: True,
    has_value_changed=lambda fieldname: False,
)
order_draft.get = lambda key, default=None: getattr(order_draft, key, default)
module.apply_customer_print_preference(order_draft)
assert order_draft.custom_print_merge_order_code == 0

sales_order.docstatus = 1
frappe.get_doc = lambda *args, **kwargs: sales_order
enqueue_calls = []
frappe.enqueue = lambda *args, **kwargs: enqueue_calls.append((args, kwargs))
module.enqueue_sales_order_submit_send(sales_order)
assert enqueue_calls[0][0][0] == "solua_home.api.wecom.send_submitted_sales_order_to_wechat"
assert enqueue_calls[0][1]["enqueue_after_commit"] is True
module.send_sales_order_customer_pdf_to_wechat = lambda name: {"filename": "order.pdf"}
module.send_sales_order_customer_xlsx_to_wechat = lambda name: {"filename": "order.xlsx"}
result = module.send_submitted_sales_order_to_wechat(sales_order.name)
assert result["status"] == "sent"
assert frappe.db.values[-1][0][2]["custom_wecom_send_status"] == "已发送"
print("PASS: WeCom PDF and XLSX upload/send for all supported documents")
