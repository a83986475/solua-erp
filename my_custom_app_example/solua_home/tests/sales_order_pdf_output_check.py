"""Small isolated check for separate Sales Order PDF ZIP output."""
import importlib.util
import base64
import io
import json
import sys
import types
from contextlib import contextmanager
from pathlib import Path
from zipfile import ZipFile

from PIL import Image

ROOT = Path(__file__).resolve().parents[1]


class Doc(dict):
    __getattr__ = dict.__getitem__
    __setattr__ = dict.__setitem__


docs = {
    "SO-1": Doc(name="SO-1", transaction_date="2026-09-30", customer_name="客人/一"),
    "SO-2": Doc(name="SO-2", transaction_date="2026-09-30", customer_name="客人二"),
    "DN-1": Doc(name="DN-1", posting_date="2026-09-30", customer_name="交货客人"),
    "PL-1": Doc(name="PL-1", creation="2026-09-30 08:30:00", customer_name="拣货客人"),
}
pdf_options = []
print_calls = []

frappe = types.ModuleType("frappe")
frappe._ = lambda text: text
frappe.PermissionError = PermissionError
frappe.whitelist = lambda *args, **kwargs: (lambda function: function)
frappe.concurrent_limit = lambda *args, **kwargs: (lambda function: function)
frappe.parse_json = json.loads
frappe.as_json = json.dumps
frappe.db = types.SimpleNamespace(get_value=lambda doctype, name, field: "Solua Wholesale")
frappe.get_meta = lambda doctype: types.SimpleNamespace(default_print_format="客户订单确认单（颜色版）")
frappe.get_doc = lambda doctype, name: docs[name]
frappe.has_permission = lambda *args, **kwargs: True
frappe.get_print = lambda doctype, name, *args, **kwargs: (
    print_calls.append(kwargs) or f"<html>{name}</html>"
)
frappe.throw = lambda message, exc=None: (_ for _ in ()).throw((exc or ValueError)(message))
frappe.local = types.SimpleNamespace(response=types.SimpleNamespace())
frappe.utils = types.ModuleType("frappe.utils")
frappe.utils.cint = lambda value: int(value or 0)
frappe.utils.flt = lambda value: float(value or 0)
frappe.utils.nowdate = lambda: "2026-09-30"
pdf = types.ModuleType("frappe.utils.pdf")


def get_pdf(html, options):
    pdf_options.append(options)
    return html.encode("utf-8")


pdf.get_pdf = get_pdf
sys.modules["frappe"] = frappe
sys.modules["frappe.utils"] = frappe.utils
sys.modules["frappe.utils.pdf"] = pdf

translate = types.ModuleType("frappe.translate")


@contextmanager
def print_language(language):
    yield


translate.print_language = print_language
sys.modules["frappe.translate"] = translate

print_format = types.ModuleType("frappe.utils.print_format")
print_format.validate_print_permission = lambda doc: None
sys.modules["frappe.utils.print_format"] = print_format

designer = types.ModuleType("solua_home.api.a4_designer")
designer._active_print_format = lambda doctype: {
    "Sales Order": "客户订单确认单（颜色版）",
    "Delivery Note": "Guia de Remessa",
    "Pick List": "拣货单（简版）",
}[doctype]
sys.modules["solua_home.api.a4_designer"] = designer

spec = importlib.util.spec_from_file_location("export_candidate", ROOT / "api/export.py")
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)

source_image = io.BytesIO()
Image.effect_noise((1600, 1600), 100).save(source_image, format="PNG")
source = "data:image/png;base64," + base64.b64encode(source_image.getvalue()).decode("ascii")
optimized_html = module._optimize_pdf_images(f'<img class="photo" src="{source}">')
optimized_source = optimized_html.split('src="', 1)[1].split('"', 1)[0]
optimized_payload = base64.b64decode(optimized_source.split(",", 1)[1])
with Image.open(io.BytesIO(optimized_payload)) as optimized_image:
    assert optimized_source.startswith("data:image/jpeg;base64,")
    assert max(optimized_image.size) <= module.PDF_IMAGE_MAX_PX
assert len(optimized_payload) < len(source_image.getvalue())

bulk_options = module._with_solua_bulk_pdf_margins(
    "Sales Order", "客户订单确认单（颜色版）", json.dumps({"page-size": "A4"})
)
assert json.loads(bulk_options)["margin-top"] == "12mm"
module.download_pdf("Sales Order", "SO-1", format="客户订单确认单（颜色版）")
assert pdf_options[-1]["margin-top"] == "12mm"
assert frappe.local.response.filename == "SO-1.pdf"
module.download_sales_order_pdfs(json.dumps(["SO-1", "SO-2"], ensure_ascii=False))

assert pdf_options[0]["margin-top"] == "12mm"
with ZipFile(io.BytesIO(frappe.local.response.filecontent)) as archive:
    assert archive.namelist() == [
        "20260930_SO-1_客人_一_客户确认单.pdf",
        "20260930_SO-2_客人二_客户确认单.pdf",
    ]
    assert archive.read(archive.namelist()[0]) == b"<html>SO-1</html>"

module.download_document_pdfs("Delivery Note", json.dumps(["DN-1"], ensure_ascii=False))
with ZipFile(io.BytesIO(frappe.local.response.filecontent)) as archive:
    assert archive.namelist() == ["20260930_DN-1_交货客人_交货单.pdf"]

module.download_document_pdfs("Pick List", json.dumps(["PL-1"], ensure_ascii=False))
with ZipFile(io.BytesIO(frappe.local.response.filecontent)) as archive:
    assert archive.namelist() == ["20260930_PL-1_拣货客人_拣货单.pdf"]

print("PASS: separate PDF ZIP output for Sales Order, Delivery Note, and Pick List")
