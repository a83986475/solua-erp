"""Public fuel-price lookup used by the transport-cost calculator."""

from html.parser import HTMLParser
from datetime import datetime, timezone
import math
import re
import urllib.error
import urllib.request

import frappe


SOURCE_URL = "https://www.petromoc.co.mz/precos-de-combustivel/"
CACHE_KEY = "solua_home:fuel_cost:petromoc_prices"
PRICE_CACHE_SECONDS = 6 * 60 * 60
ERROR_CACHE_SECONDS = 10 * 60
MAX_RESPONSE_BYTES = 2_000_000
CITIES = (
    "Inhambane / Maxixe",
    "Maputo",
    "Matola",
    "Xai-Xai",
    "Beira",
    "Chimoio",
    "Tete",
    "Quelimane",
    "Nampula",
    "Nacala",
    "Pemba",
    "Lichinga",
)
RECORD_FIELDS = ("name", "vehicle", "reading_date", "odometer_km", "liters", "fuel_price", "full_tank")


class _TextParser(HTMLParser):
    def __init__(self):
        super().__init__()
        self.parts = []

    def handle_data(self, data):
        value = " ".join(str(data).split())
        if value:
            self.parts.append(value)


def parse_petromoc_prices(raw_html):
    parser = _TextParser()
    parser.feed(raw_html)
    text = " ".join(parser.parts)
    prices = {}
    for city in CITIES:
        start = text.find(city)
        if start < 0:
            continue
        end_candidates = [text.find(other, start + len(city)) for other in CITIES if other != city]
        end_candidates = [value for value in end_candidates if value >= 0]
        block = text[start : min(end_candidates) if end_candidates else len(text)]
        gasoline = re.search(r"Gasolina\s+(\d+[.,]\d+)", block)
        diesel = re.search(r"Gasóleo\s+(\d+[.,]\d+)", block)
        if gasoline and diesel:
            prices[city] = {
                "gasoline": float(gasoline.group(1).replace(",", ".")),
                "diesel": float(diesel.group(1).replace(",", ".")),
            }
    if not prices:
        raise ValueError("Petromoc price table could not be parsed")
    return prices


def _fetch_prices():
    request = urllib.request.Request(
        SOURCE_URL,
        headers={"User-Agent": "SoluaHomeFuelCost/1.0", "Accept": "text/html"},
    )
    try:
        with urllib.request.urlopen(request, timeout=10) as response:
            raw = response.read(MAX_RESPONSE_BYTES + 1)
    except (urllib.error.HTTPError, urllib.error.URLError, TimeoutError) as exc:
        raise RuntimeError("Petromoc price source is unavailable") from exc
    if len(raw) > MAX_RESPONSE_BYTES:
        raise RuntimeError("Petromoc price source response is too large")
    return parse_petromoc_prices(raw.decode("utf-8", errors="replace"))


def _require_authenticated():
    if frappe.session.user == "Guest":
        frappe.throw("请先登录后保存或读取加油记录", frappe.PermissionError)


def _number(value, label, allow_zero=False):
    try:
        result = float(value)
    except (TypeError, ValueError):
        result = 0
    if not math.isfinite(result) or (result < 0 if allow_zero else result <= 0):
        frappe.throw(f"{label}必须是有效数字")
    return result


def _record_rows():
    rows = frappe.get_all(
        "Solua Fuel Cost Log",
        filters={"owner": frappe.session.user},
        fields=list(RECORD_FIELDS),
        order_by="reading_date asc, odometer_km asc",
        limit_page_length=500,
    )
    return [
        {
            "name": row["name"],
            "vehicle": row["vehicle"],
            "date": str(row["reading_date"]),
            "odometer": float(row["odometer_km"]),
            "liters": float(row["liters"]),
            "price": float(row["fuel_price"]) if row.get("fuel_price") is not None else None,
            "fullTank": bool(row["full_tank"]),
        }
        for row in rows
    ]


@frappe.whitelist()
def get_available_vehicles():
    _require_authenticated()
    if not frappe.has_permission("Vehicle", "read"):
        frappe.throw("当前账号没有读取车辆资料的权限", frappe.PermissionError)
    return {
        "ok": True,
        "vehicles": frappe.get_list(
            "Vehicle",
            fields=["name", "license_plate", "make", "model", "fuel_type", "last_odometer"],
            order_by="license_plate asc",
            limit_page_length=500,
        ),
    }


@frappe.whitelist()
def get_fuel_records():
    _require_authenticated()
    return {"ok": True, "records": _record_rows()}


@frappe.whitelist()
def save_fuel_record(vehicle, reading_date, odometer_km, liters, fuel_price=None, full_tank=1):
    _require_authenticated()
    vehicle = str(vehicle or "").strip()
    reading_date = str(reading_date or "").strip()
    if not vehicle or len(vehicle) > 80 or not re.fullmatch(r"\d{4}-\d{2}-\d{2}", reading_date):
        frappe.throw("请填写有效的车辆和日期")
    odometer_km = _number(odometer_km, "里程表")
    liters = _number(liters, "加油升数")
    fuel_price = None if fuel_price in (None, "", "null") else _number(fuel_price, "油价", allow_zero=True)
    full_tank = 1 if str(full_tank).lower() in {"1", "true", "yes", "on"} else 0
    frappe.get_doc(
        {
            "doctype": "Solua Fuel Cost Log",
            "vehicle": vehicle,
            "reading_date": reading_date,
            "odometer_km": odometer_km,
            "liters": liters,
            "fuel_price": fuel_price,
            "full_tank": full_tank,
        }
    ).insert(ignore_permissions=True)
    return {"ok": True, "records": _record_rows()}


@frappe.whitelist(allow_guest=True)
def get_latest_fuel_prices():
    cached = frappe.cache().get_value(CACHE_KEY)
    if cached:
        return cached
    try:
        payload = {
            "ok": True,
            "source": "Petromoc",
            "source_url": SOURCE_URL,
            "fetched_at": datetime.now(timezone.utc).isoformat(),
            "prices": _fetch_prices(),
        }
        frappe.cache().set_value(CACHE_KEY, payload, expires_in_sec=PRICE_CACHE_SECONDS)
        return payload
    except Exception:
        frappe.log_error(frappe.get_traceback(), "Fuel price lookup failed")
        payload = {
            "ok": False,
            "source": "Petromoc",
            "source_url": SOURCE_URL,
            "error": "暂时无法读取最新油价，请手动输入价格。",
        }
        frappe.cache().set_value(CACHE_KEY, payload, expires_in_sec=ERROR_CACHE_SECONDS)
        return payload
