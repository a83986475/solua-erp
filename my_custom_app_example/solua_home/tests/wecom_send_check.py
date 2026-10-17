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
sys.modules["frappe"] = frappe
sys.modules["requests"] = Requests()

export = types.ModuleType("solua_home.api.export")
export.get_export_document = lambda doctype, name: types.SimpleNamespace(name=name)
export._render_document_pdf = lambda doc, print_format, merge_customer=False: b"PDF"
export._sales_order_customer_pdf_filename = lambda doc: "AN_LAN_0058_10-15.pdf"
export._customer_sales_order_table = lambda doc: [["货号", "数量"], ["AN-LAN", 1]]
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
assert module.send_sales_order_customer_xlsx_to_wechat("SAL-ORD-2026-00058") == {"filename": "AN_LAN_0058_10-15.xlsx"}
assert len(calls) == 4
assert calls[2][1]["files"]["media"][:2] == ("AN_LAN_0058_10-15.xlsx", b"XLSX")
assert calls[3][1]["json"] == {"msgtype": "file", "file": {"media_id": "MEDIA-1"}}
print("PASS: Sales Order PDF and XLSX upload and send through WeCom webhook")
