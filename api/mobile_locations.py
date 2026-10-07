"""Administrator-managed delivery pins on customer Address records."""
import math
import re
from urllib.parse import urlparse, parse_qs, unquote, urljoin

import frappe
import requests

FIELDS = ("custom_delivery_map_url", "custom_delivery_coordinates")


def ensure_location_fields():
    from frappe.custom.doctype.custom_field.custom_field import create_custom_fields
    create_custom_fields({"Address": [
        {"fieldname": FIELDS[0], "label": "送货地图链接", "fieldtype": "Small Text", "insert_after": "address_line2"},
        {"fieldname": FIELDS[1], "label": "送货经纬度（纬度,经度）", "fieldtype": "Data", "insert_after": FIELDS[0]},
    ]}, update=False)


def coordinates(value):
    value = str(value or "").strip()
    if not value:
        return ""
    try:
        lat, lng = map(float, value.split(","))
        if not (math.isfinite(lat) and math.isfinite(lng) and -90 <= lat <= 90 and -180 <= lng <= 180):
            raise ValueError
    except (ValueError, TypeError):
        frappe.throw("经纬度无效，请按 纬度,经度 填写")
    return f"{lat:.6f},{lng:.6f}"


def validate_map_url(value):
    value = str(value or "").strip()
    if not value:
        return ""
    try:
        parsed = urlparse(value)
        port = parsed.port
    except ValueError:
        frappe.throw("地图链接格式无效")
    hosts = {"www.google.com", "google.com", "maps.google.com", "maps.app.goo.gl", "goo.gl", "www.google.co.mz", "www.google.pt"}
    if (len(value) > 2048 or parsed.scheme != "https" or parsed.hostname not in hosts
            or parsed.username or parsed.password or port not in (None, 443)):
        frappe.throw("请填写有效的 HTTPS Google Maps 地点分享链接")
    if parsed.hostname not in ("maps.app.goo.gl",) and not parsed.path.startswith("/maps"):
        frappe.throw("只支持 Google Maps 地点链接")
    return value


def _extract_coordinates(value):
    parsed = urlparse(value)
    query = parse_qs(parsed.query)
    candidates = [query.get(key, [""])[0] for key in ("query", "q", "destination")]
    text = unquote(value)
    pin = re.search(r"!3d(-?\d+(?:\.\d+)?)!4d(-?\d+(?:\.\d+)?)", text)
    if pin:
        candidates.insert(0, f"{pin[1]},{pin[2]}")
    place = re.search(r"/place/(-?\d+(?:\.\d+)?),\s*(-?\d+(?:\.\d+)?)", unquote(parsed.path))
    if place:
        candidates.append(f"{place[1]},{place[2]}")
    for candidate in candidates:
        if re.fullmatch(r"\s*-?\d+(?:\.\d+)?\s*,\s*-?\d+(?:\.\d+)?\s*", candidate):
            return coordinates(candidate)
    # @lat,lng is a camera centre, not necessarily the selected destination.
    return ""


@frappe.whitelist(methods=["POST"])
def resolve_map_location(map_url):
    from solua_home.api.mobile import _require_admin
    _require_admin()
    original = validate_map_url(map_url)
    current = original
    for _ in range(5):
        pin = _extract_coordinates(current)
        if pin:
            return {"map_url": original, "coordinates": pin}
        if urlparse(current).hostname not in ("maps.app.goo.gl", "goo.gl"):
            break
        try:
            response = requests.head(current, allow_redirects=False, timeout=5)
        except requests.RequestException:
            break
        if response.status_code not in (301, 302, 303, 307, 308) or not response.headers.get("Location"):
            break
        current = validate_map_url(urljoin(current, response.headers["Location"]))
    return {"map_url": original, "coordinates": "", "message": "链接中没有明确地点坐标，请在 Google Maps 长按收货点复制坐标，或到店使用手机定位。"}


@frappe.whitelist()
def get_customer_locations(customer):
    from solua_home.api.mobile import _require_admin, _customer
    _require_admin()
    customer = _customer(customer)
    names = frappe.get_all("Dynamic Link", filters={"parenttype": "Address", "link_doctype": "Customer", "link_name": customer.name}, pluck="parent", limit_page_length=0)
    if not names:
        return []
    return frappe.get_list("Address", filters={"name": ["in", names]},
        fields=["name", "address_title", "address_line1", "city", *FIELDS], order_by="name asc", limit_page_length=0)


@frappe.whitelist(methods=["POST"])
def save_customer_location(customer, address, map_url=None, pin=None):
    from solua_home.api.mobile import _require_admin, _customer, _validate_order_address
    _require_admin()
    customer = _customer(customer)
    address = _validate_order_address(customer.name, address)
    if not address:
        frappe.throw("请先为客户建立门店地址，再保存收货位置")
    url = validate_map_url(map_url)
    point = coordinates(pin)
    if not point and url:
        point = resolve_map_location(url)["coordinates"]
    doc = frappe.get_doc("Address", address)
    doc.check_permission("write")
    doc.set(FIELDS[0], url)
    doc.set(FIELDS[1], point)
    doc.save()
    return {"address": doc.name, "map_url": url, "coordinates": point}
