"""Fast local checks for the shared Solua print layout contract."""

import importlib
import json
import sys
import types
from pathlib import Path

from jinja2 import Environment

ROOT = Path(__file__).resolve().parents[3]
APP = ROOT / "my_custom_app_example" / "solua_home"
FORMATS = APP / "print_format"


class _DB:
    values = {}

    def get_single_value(self, doctype, field):
        assert doctype == "Print Settings"
        return self.values.get(field)


db = _DB()
fake_frappe = types.ModuleType("frappe")
fake_frappe.db = db
fake_frappe._ = lambda value: value
fake_frappe.throw = lambda message: (_ for _ in ()).throw(ValueError(message))
sys.modules.setdefault("frappe", fake_frappe)

sys.path.insert(0, str(ROOT / "my_custom_app_example"))
wholesale = importlib.import_module("solua_home.printing.wholesale")


def check_json_formats():
    files = sorted(FORMATS.glob("*/*.json"))
    assert len(files) == 5, files
    for path in files:
        data = json.loads(path.read_text(encoding="utf-8-sig"))
        assert data.get("doctype") == "Print Format", path
        Environment().parse(data.get("html") or data.get("raw_commands") or "")
        if data.get("name") != "价格标签 50x30":
            assert "get_solua_print_css()" in data.get("html", ""), path
        else:
            assert "get_solua_print_css()" in data.get("raw_commands", ""), path


def check_settings():
    db.values.clear()
    css = str(wholesale.get_solua_print_css())
    assert "10pt" in css and "1.12" in css and "3px 4px" in css
    db.values.update({"custom_solua_print_font_size": "14", "custom_solua_print_density": "标准", "custom_solua_print_item_borders": "1"})
    css = str(wholesale.get_solua_print_css())
    assert "14pt" in css and "1.35" in css and "6px 6px" in css and "--solua-item-border: 1px solid" in css
    db.values["custom_solua_print_item_borders"] = "0"
    css = str(wholesale.get_solua_print_css())
    assert "--solua-item-border: 0" in css


def check_delivery_switches():
    data = json.loads((FORMATS / "delivery_note_guia_remessa/delivery_note_guia_remessa.json").read_text(encoding="utf-8-sig"))
    html = data["html"]
    for token in (
        "custom_print_current_remaining",
        "custom_print_traceability",
        "show_current_remaining",
        "show_traceability",
        "p.get('has_traceability')",
        "show_current_remaining + show_traceability",
    ):
        assert token in html, token
    assert "col-traceability" in html and "col-sku" in html and "col-description" in html


def check_source_syntax():
    import ast

    for path in (APP / "printing/wholesale.py", APP / "install.py"):
        ast.parse(path.read_text(encoding="utf-8-sig"), filename=str(path))
    assert "custom_solua_print_item_borders" in (APP / "install.py").read_text(encoding="utf-8-sig")


if __name__ == "__main__":
    check_json_formats()
    check_settings()
    check_delivery_switches()
    check_source_syntax()
    print("print layout checks passed")
