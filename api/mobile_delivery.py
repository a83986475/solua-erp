"""Read-only pending-delivery queue for the administrator mobile hub."""
import frappe
import json
import math
import requests
from frappe.utils import flt, nowdate
from solua_home.api.mobile import _require_admin, _defaults, _sales_order_relations_batch


def _route_waypoint(value):
    value = str(value or "").strip()
    if not value or len(value) > 500:
        frappe.throw("请填写有效的出发位置和送货位置（不超过 500 字）")
    parts = value.split(",")
    if len(parts) == 2:
        try:
            latitude, longitude = map(float, parts)
        except ValueError:
            pass
        else:
            if not (math.isfinite(latitude) and math.isfinite(longitude) and -90 <= latitude <= 90 and -180 <= longitude <= 180):
                frappe.throw("经纬度无效")
            return {"location": {"latLng": {"latitude": latitude, "longitude": longitude}}}
    return {"address": value}


def _optimized_route_result(payload, stop_count, return_to_origin):
    routes = payload.get("routes") or []
    if not routes:
        frappe.throw("Google 未找到可行的驾车路线，请核对送货位置")
    route = routes[0]
    intermediate_count = stop_count if return_to_origin else stop_count - 1
    indices = route.get("optimizedIntermediateWaypointIndex")
    if (not isinstance(indices, list) or any(type(index) is not int for index in indices)
            or sorted(indices) != list(range(intermediate_count))):
        frappe.throw("Google 返回的站点顺序不完整，原顺序已保留")
    order = indices if return_to_origin else indices + [stop_count - 1]
    try:
        seconds = float(str(route["duration"]).removesuffix("s"))
        distance = float(route["distanceMeters"])
        if not (math.isfinite(seconds) and seconds >= 0 and math.isfinite(distance) and distance >= 0):
            raise ValueError
    except (KeyError, TypeError, ValueError):
        frappe.throw("Google 返回的里程或时间无效，原顺序已保留")
    return {"order": order, "distance_meters": distance, "duration_seconds": seconds,
            "return_to_origin": bool(return_to_origin)}


@frappe.whitelist()
def get_route_optimization_status():
    _require_admin()
    return {"enabled": bool(frappe.conf.get("solua_google_routes_api_key")), "max_stops": 25}


@frappe.whitelist(methods=["POST"])
def optimize_delivery_route(origin, addresses, return_to_origin=0):
    _require_admin()
    key = frappe.conf.get("solua_google_routes_api_key")
    if not key:
        frappe.throw("尚未配置 Google Routes API，请先启用 Routes API、计费并配置服务器密钥")
    if isinstance(addresses, str):
        try:
            addresses = json.loads(addresses)
        except ValueError:
            frappe.throw("站点数据无效")
    if not isinstance(addresses, list) or not 2 <= len(addresses) <= 25 or any(not isinstance(item, str) for item in addresses):
        frappe.throw("每次自动优化需要选择 2–25 个有效站点")
    if str(return_to_origin) not in ("0", "1"):
        frappe.throw("路线终点设置无效")
    return_to_origin = str(return_to_origin) == "1"
    start = _route_waypoint(origin)
    points = [_route_waypoint(item) for item in addresses]
    body = {"origin": start, "destination": start if return_to_origin else points[-1],
            "intermediates": points if return_to_origin else points[:-1], "travelMode": "DRIVE",
            "routingPreference": "TRAFFIC_AWARE", "optimizeWaypointOrder": True}
    try:
        response = requests.post("https://routes.googleapis.com/directions/v2:computeRoutes",
            json=body, headers={"X-Goog-Api-Key": key,
                "X-Goog-FieldMask": "routes.optimizedIntermediateWaypointIndex,routes.duration,routes.distanceMeters"},
            timeout=25, allow_redirects=False)
    except requests.RequestException:
        frappe.throw("Google 路线服务连接失败，请稍后重试；原顺序已保留")
    if response.status_code != 200:
        frappe.throw("Google 路线请求失败，请检查 API 权限、计费、配额及位置；原顺序已保留")
    try:
        payload = response.json()
    except ValueError:
        frappe.throw("Google 路线响应无效，原顺序已保留")
    if not isinstance(payload, dict):
        frappe.throw("Google 路线响应无效，原顺序已保留")
    return _optimized_route_result(payload, len(addresses), return_to_origin)


def _pending_item(row):
    # ERPNext delivered_qty is in the order row's UOM, not stock_uom.
    pending = max(0, flt(row.get("qty")) - flt(row.get("delivered_qty")))
    return {**row, "pending_qty": pending}


def _address_info(name, source):
    from solua_home.api.mobile_locations import FIELDS
    address = frappe.db.get_value("Address", name,
        ["address_line1", "address_line2", "city", "state", "country", "phone", *FIELDS], as_dict=True) if name else None
    text = ", ".join(str(address.get(key) or "").strip() for key in
        ("address_line1", "address_line2", "city", "state", "country") if address and address.get(key))
    # A country/city alone is not a delivery location.
    if not address or not address.address_line1:
        text = ""
    return {"address": text, "address_name": name or "", "address_source": source,
            "phone": address.phone if address else "", "coordinates": address.get(FIELDS[1]) if address else "",
            "map_url": address.get(FIELDS[0]) if address else ""}


@frappe.whitelist()
@frappe.read_only()
def list_pending_deliveries(query=None, stage="all", page=1, page_length=20):
    _require_admin()
    defaults = _defaults()
    if not defaults["company"]:
        frappe.throw("没有可访问的公司", frappe.PermissionError)
    try:
        page, page_length = max(1, int(page or 1)), max(1, min(50, int(page_length or 20)))
    except (TypeError, ValueError):
        page, page_length = 1, 20
    filters = {"company": defaults["company"], "docstatus": 1,
               "status": ["not in", ["Closed", "Completed", "Cancelled"]], "per_delivered": ["<", 100]}
    if stage == "pending":
        filters["per_delivered"] = ["<=", 0]
    elif stage == "partial":
        filters["per_delivered"] = ["between", [0.000001, 99.999999]]
    elif stage == "due":
        filters["delivery_date"] = ["<=", nowdate()]
    query = str(query or "").strip()
    or_filters = [[field, "like", f"%{query}%"] for field in
                  ("name", "customer", "customer_name")] if query else None
    count = frappe.get_all("Sales Order", filters=filters, or_filters=or_filters,
                          fields=[{"COUNT": "name", "as": "total"}])[0].total
    page_count = max(1, (count + page_length - 1) // page_length)
    page = min(page, page_count)
    rows = frappe.get_all("Sales Order", filters=filters, or_filters=or_filters,
        fields=["name", "customer", "customer_name", "transaction_date", "delivery_date", "status",
                "per_delivered", "grand_total", "currency", "shipping_address_name", "customer_address"],
        order_by="delivery_date asc, transaction_date asc, name asc",
        limit_start=(page - 1) * page_length, limit_page_length=page_length)
    names = [row.name for row in rows]
    items_by_order = {}
    if names:
        for item in frappe.get_all("Sales Order Item",
            filters={"parent": ["in", names], "parenttype": "Sales Order"},
            fields=["parent", "item_code", "item_name", "qty", "delivered_qty", "uom"],
            order_by="parent asc, idx asc", limit_page_length=0):
            items_by_order.setdefault(item.parent, []).append(item)
    relations = _sales_order_relations_batch(names, {row.name: 1 for row in rows})
    for row in rows:
        items = items_by_order.get(row.name, [])
        row["items"] = [item for item in map(_pending_item, items) if item["pending_qty"] > 0]
        name = row.shipping_address_name or row.customer_address
        source = "订单送货地址" if row.shipping_address_name else "订单客户地址（请核对）"
        if not name:
            links = frappe.get_all("Dynamic Link", filters={"parenttype": "Address", "link_doctype": "Customer",
                "link_name": row.customer}, pluck="parent", limit_page_length=0)
            names = list(dict.fromkeys(links))
            if len(names) == 1:
                name, source = names[0], "客户建档地址（请核对）"
        row.update(_address_info(name, source))
        row["overdue"] = bool(row.delivery_date and str(row.delivery_date) < nowdate())
        row.update(relations.get(row.name, {}))
    return {"rows": rows, "row_count": count, "page": page, "page_count": page_count,
            "page_length": page_length, "has_prev": page > 1, "has_next": page < page_count}
