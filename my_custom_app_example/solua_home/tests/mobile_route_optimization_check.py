"""Validate Google route mapping and failures without credentials or API calls."""
import ast
import json
import math
from pathlib import Path
from types import SimpleNamespace

source = Path(__file__).resolve().parents[1] / "api" / "mobile_delivery.py"
functions = [node for node in ast.parse(source.read_text(encoding="utf-8")).body
             if isinstance(node, ast.FunctionDef) and node.name in
             ("_route_waypoint", "_optimized_route_result", "get_route_optimization_status", "optimize_delivery_route")]
for node in functions:
    node.decorator_list = []
calls = []
payload = {"routes": [{"optimizedIntermediateWaypointIndex": [1, 0], "distanceMeters": 12345, "duration": "1800s"}]}


def fail(message):
    raise ValueError(message)


def post(url, **kwargs):
    calls.append((url, kwargs))
    return SimpleNamespace(status_code=200, json=lambda: payload)


config = {"solua_google_routes_api_key": "TEST-ONLY-NOT-A-CREDENTIAL"}
namespace = {"frappe": SimpleNamespace(conf=config, throw=fail), "json": json, "math": math,
             "requests": SimpleNamespace(post=post, RequestException=OSError), "_require_admin": lambda: None}
exec(compile(ast.Module(body=functions, type_ignores=[]), str(source), "exec"), namespace)
optimize = namespace["optimize_delivery_route"]
result = optimize("Warehouse", ["A", "B"], 1)
assert result["order"] == [1, 0] and result["duration_seconds"] == 1800
assert calls[-1][1]["json"]["origin"] == calls[-1][1]["json"]["destination"]
assert calls[-1][1]["json"]["optimizeWaypointOrder"] is True
result = optimize("Warehouse", ["A", "B", "C"], 0)
assert result["order"] == [1, 0, 2]
assert calls[-1][1]["json"]["destination"] == {"address": "C"}
assert calls[-1][1]["timeout"] == 25
assert namespace["_route_waypoint"]("-25.9,32.5")["location"]["latLng"]["latitude"] == -25.9
for args in (("", ["A", "B"]), ("X", ["A"]), ("X", ["A"] * 26), ("X", ["A", ""]), ("X", ["A", "B"], 2)):
    try:
        optimize(*args)
        raise AssertionError("invalid input accepted")
    except ValueError:
        pass
for invalid in ([0, 0], [1, 9], [False, 1], None):
    payload["routes"][0]["optimizedIntermediateWaypointIndex"] = invalid
    try:
        optimize("X", ["A", "B"], 1)
        raise AssertionError("invalid permutation accepted")
    except ValueError:
        pass
config.clear()
assert namespace["get_route_optimization_status"]()["enabled"] is False
before = len(calls)
try:
    optimize("X", ["A", "B"])
    raise AssertionError("missing API key accepted")
except ValueError:
    pass
assert len(calls) == before
print("mobile route optimization checks passed (mock Google response)")
