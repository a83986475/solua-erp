"""Runnable lifecycle/quantity/permission/reason regression without site writes."""
import importlib.util
import sys
import types
from pathlib import Path

class Row(dict):
    __getattr__ = dict.get

def fail(message, *args):
    raise ValueError(message)

frappe = types.ModuleType("frappe")
frappe.whitelist = frappe.read_only = lambda: lambda fn: fn
frappe.throw = fail
frappe.parse_json = __import__("json").loads
sys.modules["frappe"] = frappe
utils = types.ModuleType("frappe.utils")
utils.flt = lambda value: float(value or 0)
utils.escape_html = __import__("html").escape
sys.modules["frappe.utils"] = utils
home = types.ModuleType("solua_home.api.home")
home._can_read = lambda dt: True
home._list = lambda *args, **kwargs: []
sys.modules["solua_home.api.home"] = home
spec = importlib.util.spec_from_file_location("order_status", Path(__file__).resolve().parents[1] / "api/order_status.py")
m = importlib.util.module_from_spec(spec)
spec.loader.exec_module(m)

class Order:
    docstatus = 1
    status = "Closed"
    name = "SO"
    company = "Co"
    items = [Row(name="ROW", qty=10, conversion_factor=1, uom="条")]
    def get(self, key): return getattr(self, key, None)
    def check_permission(self, permission): assert permission in ("read", "submit")
    def check_modified_date(self): pass
    def db_set(self, *args, **kwargs): writes.append((args, kwargs))
    def update_status(self, status): self.status = status
    def add_comment(self, *args): writes.append(args)

order = Order()
delivered = [Row(so_detail="ROW", stock_qty=10, is_return=0), Row(so_detail="ROW", stock_qty=-2, is_return=1)]
invoices = [Row(so_detail="ROW", parent="SI", stock_qty=8, is_return=0, update_stock=0, outstanding_amount=80),
            Row(so_detail="ROW", parent="CREDIT", stock_qty=-8, is_return=1, update_stock=0, outstanding_amount=0)]
r = m.summarize(order, delivered, invoices)
assert r["status_label"] == "已结束" and r["end_reason"] == "未记录"
assert "有退货" in r["delivery_label"] and "不再交付" in r["delivery_label"]
assert r["quantities"][0] == {"uom":"条", "ordered":10, "delivered":10, "returned":2, "net":8, "remaining":2}
assert r["billing_label"] == "已开票" and r["payment_label"] == "未收齐"
order.status = "To Deliver and Bill"
assert not m.summarize(order, delivered, invoices)["ended"]
assert m.summarize(order, delivered, invoices)["status_label"] == "进行中"
order.status = "Completed"
assert m.summarize(order, delivered, invoices)["status_label"] == "已完成"
assert m.summarize(order, delivered, invoices)["payment_label"] == "未收齐"  # Completed is not paid.
order.status = "Closed"
assert m.summarize(order, [], [])["delivery_label"] == "未交货 · 剩余不再交付"
r = m.summarize(order, delivered, invoices, False, False)
assert r["quantities"] == [] and r["billing_label"] == "开票情况无权限"
order.items = [Row(name="ROW", qty=2, conversion_factor=12, uom="箱")]
r = m.summarize(order, [Row(so_detail="ROW", stock_qty=12, is_return=0)], [])
assert r["quantities"][0]["delivered"] == 1 and r["quantities"][0]["remaining"] == 1
writes = []
order.status = "To Deliver and Bill"
for reason in (None, "   ", "x" * 501):
    try: m._end_order(order, reason)
    except ValueError: pass
    else: raise AssertionError("missing/oversized reason accepted")
assert writes == []
m._end_order(order, "客户取消剩余 <理由>")
assert order.status == "Closed" and "&lt;理由&gt;" in writes[-1][1]
assert writes[0][1] == {"update_modified": False}
for names in ([], ["SO"] * 51, [None], "{}"):
    try: m.get_order_statuses(names)
    except ValueError: pass
    else: raise AssertionError("invalid names accepted")
frappe.get_doc = lambda *args: types.SimpleNamespace(check_permission=lambda permission: fail("no permission"))
try: m.get_order_statuses(["OTHER-COMPANY"])
except ValueError: pass
else: raise AssertionError("permission bypass")
print("PASS: ended/complete distinction, gross/return/net quantities, boxes, price-credit quantity independence, unpaid completion, permissions, required reason and escaped audit comment")
