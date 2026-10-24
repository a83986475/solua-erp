import importlib.util
import sys
import types
from pathlib import Path
import json


class _FakeFrappe:
    def whitelist(self, **_kwargs):
        return lambda function: function


sys.modules["frappe"] = _FakeFrappe()
spec = importlib.util.spec_from_file_location(
    "fuel_cost", Path(__file__).resolve().parents[1] / "api" / "fuel_cost.py"
)
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)

html = """
<h2>Maputo</h2><div>Gasolina</div><span>93.69 Mt</span>
<div>Gasóleo</div><span>116.25 Mt</span>
<h2>Beira</h2><div>Gasolina</div><span>93.25 Mt</span>
<div>Gasóleo</div><span>116.25 Mt</span>
"""
prices = module.parse_petromoc_prices(html)
assert prices["Maputo"] == {"gasoline": 93.69, "diesel": 116.25}
assert prices["Beira"]["gasoline"] == 93.25
source = Path(__file__).resolve().parents[1]
api_source = (source / "api" / "fuel_cost.py").read_text(encoding="utf-8")
assert "def get_fuel_records" in api_source
assert "def get_available_vehicles" in api_source
assert "def save_fuel_record" in api_source
assert "frappe.session.user == \"Guest\"" in api_source
doctype = json.loads((source / "solua_wholesale" / "doctype" / "solua_fuel_cost_log" / "solua_fuel_cost_log.json").read_text(encoding="utf-8"))
assert {field["fieldname"] for field in doctype["fields"]} >= {"vehicle", "reading_date", "odometer_km", "liters", "fuel_price", "full_tank"}
vehicle_field = next(field for field in doctype["fields"] if field["fieldname"] == "vehicle")
assert vehicle_field["fieldtype"] == "Link" and vehicle_field["options"] == "Vehicle"
print("PASS: Petromoc fuel-price parser handles city gasoline/diesel values")
