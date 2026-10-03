"""Small runnable check for periods, permissions, FX and cash collection sources."""
import importlib.util
import sys
import types
from datetime import date
from pathlib import Path

class Row(dict):
    __getattr__ = dict.get

def fail(message, *args):
    raise ValueError(message)
frappe = types.ModuleType('frappe')
frappe.whitelist = frappe.read_only = lambda: lambda fn: fn
frappe.throw = fail
utils = types.ModuleType('frappe.utils')
utils.flt = lambda value: float(value or 0)
utils.getdate = lambda value: date.fromisoformat(str(value))
utils.nowdate = lambda: '2026-10-03'
sys.modules['frappe'] = frappe
sys.modules['frappe.utils'] = utils
home = types.ModuleType('solua_home.api.home')
home._can_read = lambda dt: True
home._resolve_company = lambda company: Row(name='Test', default_currency='MZN')
home._invoice_specs = lambda company, period: [('Sales Invoice', {'posting_date':period}), ('POS Invoice', {'posting_date':period, 'consolidated_invoice':['is','not set']})]
rows = {'Sales Order':[Row(name='SO',transaction_date='2026-10-03',customer='C',base_grand_total=100)],
'Sales Invoice':[Row(name='SI',posting_date='2026-10-03',customer='C',base_grand_total=80,outstanding_amount=10,conversion_rate=2,base_paid_amount=30)],
'POS Invoice':[Row(name='POS',posting_date='2026-10-03',customer='C',base_grand_total=-5,outstanding_amount=0,conversion_rate=1,base_paid_amount=-5)],
'Payment Entry':[Row(name='PE',posting_date='2026-10-03',party='C',payment_type='Receive',base_received_amount=40),Row(name='REFUND',posting_date='2026-10-03',party='C',payment_type='Pay',base_paid_amount=7)]}
home._list = lambda dt, filters, fields, **kw: rows[dt]
sys.modules['solua_home.api.home'] = home
spec = importlib.util.spec_from_file_location('totals',Path(__file__).resolve().parents[1]/'api/business_totals.py')
m = importlib.util.module_from_spec(spec)
spec.loader.exec_module(m)
assert m.date_range('week') == ('2026-09-28','2026-10-03')
assert m.date_range('本季度') == ('2026-10-01','2026-10-03')
assert m.date_range('year') == ('2026-01-01','2026-10-03')
assert m.date_range('custom','2026-01-01','2026-06-30') == ('2026-01-01','2026-06-30')
for args in [('bad',),('custom',),('custom','2026-10-03','2026-10-01')]:
    try: m.date_range(*args)
    except ValueError: pass
    else: raise AssertionError(args)
rows['Delivery Note']=[Row(name='DN',posting_date='2026-10-03',customer='C',base_grand_total=42)]
assert m.get_total('delivered')['amount'] == 42
assert m.get_total('orders')['amount'] == 100
assert m.get_total('invoices')['amount'] == 75
assert m.get_total('receivable')['amount'] == 20
assert m.get_total('paid')['amount'] == 55
home._can_read = m._can_read = lambda dt: False
assert m.get_total('paid')['state'] == 'no_permission'
assert m.get_total('paid')['amount'] is None
print('PASS: week/quarter/year/custom, invalid dates, totals, FX, invoice settlement/POS/returns and permission boundary')
