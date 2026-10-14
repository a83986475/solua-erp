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
    "SI-1": Doc(name="SI-1", posting_date="2026-09-30", customer_name="发票客人"),
}
pdf_options = []
print_calls = []
multi_rendered_html = []


class FakePdfWriter:
    def __init__(self):
        self.parts = []

    def write(self, target):
        target.write(b"".join(self.parts))

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


def get_pdf(html, options, output=None):
    pdf_options.append(options)
    if output is not None:
        multi_rendered_html.append(html)
        output.parts.append(html.encode("utf-8"))
        return output
    return html.encode("utf-8")


pdf.get_pdf = get_pdf
sys.modules["frappe"] = frappe
sys.modules["frappe.utils"] = frappe.utils
sys.modules["frappe.utils.pdf"] = pdf
pypdf = types.ModuleType("pypdf")
pypdf.PdfWriter = FakePdfWriter
sys.modules["pypdf"] = pypdf

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
    "Pick List": "拣货单",
    "Sales Invoice": "FACTURA A4",
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
assert all(json.loads(bulk_options)[key] == "8mm" for key in ("margin-top", "margin-bottom", "margin-left", "margin-right"))
module.download_pdf("Sales Order", "SO-1", format="客户订单确认单（颜色版）")
assert all(pdf_options[-1][key] == "8mm" for key in ("margin-top", "margin-bottom", "margin-left", "margin-right"))
assert pdf_options[-1]["zoom"] == module.SOLUA_PDF_ZOOM
assert frappe.local.response.filename == "SO-1.pdf"
module.download_pdf("Sales Order", "SO-1", format="客户订单确认单（颜色版）", mobile=1)
assert pdf_options[-1]["zoom"] == module.SOLUA_MOBILE_PDF_ZOOM
module.download_pdf("Sales Invoice", "SI-1", mobile=1)
assert pdf_options[-1]["zoom"] == "0.90"
original_get_print = frappe.get_print
frappe.get_print = lambda doctype, name, *args, **kwargs: (
    print_calls.append(kwargs) or '<table class="items"></table>'
)
mobile_pdf = module._render_document_pdf(
    docs["SO-1"], "客户订单确认单（颜色版）", merge_customer=True, doctype="Sales Order", mobile=True
)
assert b"table-layout:fixed" not in mobile_pdf
assert b"<colgroup>" not in mobile_pdf
assert print_calls[-1]["doc"]["custom_print_color_images"] == 1
assert pdf_options[-1]["zoom"] == module.SOLUA_MOBILE_PDF_ZOOM
desktop_pdf = module._render_document_pdf(
    docs["SO-1"], "客户订单确认单（颜色版）", merge_customer=False, doctype="Sales Order"
)
frappe.get_print = original_get_print
assert b"table-layout:fixed" not in desktop_pdf
module.download_sales_order_pdfs(json.dumps(["SO-1", "SO-2"], ensure_ascii=False))

assert all(pdf_options[0][key] == "8mm" for key in ("margin-top", "margin-bottom", "margin-left", "margin-right"))
with ZipFile(io.BytesIO(frappe.local.response.filecontent)) as archive:
    assert archive.namelist() == [
        "20260930_SO-1_客人_一_客户确认单.pdf",
        "20260930_SO-2_客人二_客户确认单.pdf",
    ]
    first_pdf = archive.read(archive.namelist()[0])
    assert first_pdf.startswith(b"<html>SO-1</html>")

module.download_document_pdfs("Delivery Note", json.dumps(["DN-1"], ensure_ascii=False))
with ZipFile(io.BytesIO(frappe.local.response.filecontent)) as archive:
    assert archive.namelist() == ["20260930_DN-1_交货客人_交货单.pdf"]

module.download_document_pdfs("Pick List", json.dumps(["PL-1"], ensure_ascii=False))
with ZipFile(io.BytesIO(frappe.local.response.filecontent)) as archive:
    assert archive.namelist() == ["20260930_PL-1_拣货客人_拣货单.pdf"]

original_get_print = frappe.get_print
frappe.get_print = lambda doctype, name, *args, **kwargs: f'<html><img src="{source}">{name}</html>'
module.download_multi_pdf(
    "Sales Order",
    json.dumps(["SO-1", "SO-2"], ensure_ascii=False),
    format="客户订单确认单（颜色版）",
)
frappe.get_print = original_get_print
assert len(multi_rendered_html) == 2
assert all("data:image/jpeg;base64," in html for html in multi_rendered_html)
assert b"data:image/jpeg;base64," in frappe.local.response.filecontent

core_multi_calls = []
print_format.download_multi_pdf = lambda *args: core_multi_calls.append(args) or "core-pdf"
assert module.download_multi_pdf("Other DocType", "[]") == "core-pdf"
assert core_multi_calls

print("PASS: separate PDF ZIP output for Sales Order, Delivery Note, and Pick List")
