"""Parse pins and reject unsafe links without network or production writes."""
import ast
import math
import re
import sys
from pathlib import Path
from types import SimpleNamespace, ModuleType
from urllib.parse import urlparse, parse_qs, unquote, urljoin


def fail(message):
    raise ValueError(message)


source = Path(__file__).resolve().parents[1] / "api" / "mobile_locations.py"
functions = [node for node in ast.parse(source.read_text(encoding="utf-8")).body
             if isinstance(node, ast.FunctionDef) and node.name in ("coordinates", "validate_map_url", "_extract_coordinates", "resolve_map_location", "save_customer_location")]
for function in functions:
    function.decorator_list = []
namespace = {"frappe": SimpleNamespace(throw=fail), "math": math, "re": re,
             "urlparse": urlparse, "parse_qs": parse_qs, "unquote": unquote, "urljoin": urljoin,
             "QQ_MAP_HOSTS": {"map.qq.com"},
             "GOOGLE_MAP_HOSTS": {"www.google.com", "google.com", "maps.google.com", "maps.app.goo.gl", "goo.gl", "www.google.co.mz", "www.google.pt"}}
exec(compile(ast.Module(body=functions, type_ignores=[]), str(source), "exec"), namespace)
point, validate, extract = [namespace[name] for name in ("coordinates", "validate_map_url", "_extract_coordinates")]
assert point("0,0") == "0.000000,0.000000"
assert point("-25.9692,32.5732") == "-25.969200,32.573200"
assert extract("https://www.google.com/maps?q=-25.9%2C32.5") == "-25.900000,32.500000"
assert extract("https://www.google.com/maps/place/Shop/@1,2,14z/data=!3d-25.9!4d32.5") == "-25.900000,32.500000"
assert extract("https://www.google.com/maps/@-25.9,32.5,15z") == ""
qq_url = "https://map.qq.com/?addr=Super+Asia&pointx=32.460083&pointy=-25.949830&type=marker"
assert validate(qq_url)
assert extract(qq_url) == "-25.949830,32.460083"
assert validate("https://maps.app.goo.gl/Abc")
assert validate("https://goo.gl/maps/Abc")
for bad in ("https://google.com.evil.test/maps?q=1,2", "http://127.0.0.1/maps", "https://www.google.com:123/maps", "https://x@www.google.com/maps", "https://www.google.com/url?q=https://127.0.0.1", "https://www.google.com:x/maps"):
    try:
        validate(bad)
        raise AssertionError("unsafe URL accepted")
    except ValueError:
        pass
for bad in ("nan,1", "91,1", "1,181", "1", "1,2,3"):
    try:
        point(bad)
        raise AssertionError("invalid coordinates accepted")
    except ValueError:
        pass
print("mobile location parsing checks passed")

mobile = ModuleType("solua_home.api.mobile")
mobile._require_admin = lambda: None
mobile._customer = lambda name: SimpleNamespace(name=name)
mobile._validate_order_address = lambda customer, address: address if customer == "C" and address == "A" else fail("address belongs to another customer")
sys.modules["solua_home.api.mobile"] = mobile
heads = []
namespace["requests"] = SimpleNamespace(RequestException=OSError, head=lambda url, **kwargs: (
    heads.append(url) or SimpleNamespace(status_code=302, headers={"Location":"https://www.google.com/maps?q=-25.9%2C32.5"})))
assert namespace["resolve_map_location"]("https://maps.app.goo.gl/Test")["coordinates"] == "-25.900000,32.500000"
assert len(heads) == 1
doc_values = {}
permissions = []
doc = SimpleNamespace(name="A", check_permission=lambda action: permissions.append(action), set=lambda key,value: doc_values.update({key:value}), save=lambda: None)
namespace["frappe"].get_doc = lambda doctype,name: doc
namespace["FIELDS"] = ("custom_delivery_map_url", "custom_delivery_coordinates")
namespace["save_customer_location"]("C", "A", "https://www.google.com/maps?q=-25.9%2C32.5")
assert doc_values["custom_delivery_coordinates"] == "-25.900000,32.500000"
assert permissions == ["write"]
try:
    namespace["save_customer_location"]("OTHER", "A", pin="1,2")
    raise AssertionError("cross-customer address accepted")
except ValueError:
    pass
assert len(permissions) == 1
print("mobile location save permission and short-link checks passed")
