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
utils.flt = lambda value, precision=None: round(float(value or 0), precision) if precision is not None else float(value or 0)
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
'Payment Entry':[Row(name='PE',posting_date='2026-10-03',party='C',party_type='Customer',payment_type='Receive',base_received_amount=40,unallocated_amount=6),Row(name='REFUND',posting_date='2026-10-03',party='C',party_type='Customer',payment_type='Pay',base_paid_amount=7,unallocated_amount=0)]}
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
delivery_docs = {'DN': types.SimpleNamespace(name='DN', base_grand_total=42, base_net_total=42,
                                             items=[types.SimpleNamespace(name='DNI', qty=2, base_net_amount=42)])}
frappe.get_doc = lambda dt, name: delivery_docs[name]
for package in ('erpnext', 'erpnext.stock', 'erpnext.stock.doctype', 'erpnext.stock.doctype.delivery_note'):
    sys.modules.setdefault(package, types.ModuleType(package))
delivery_note_module = types.ModuleType('erpnext.stock.doctype.delivery_note.delivery_note')
delivery_note_module.get_returned_qty_map = lambda name: {'DNI': 1}
sys.modules['erpnext.stock.doctype.delivery_note.delivery_note'] = delivery_note_module
assert m.get_total('delivered')['amount'] == 21
assert m._order_total_result(Row(name='Test', default_currency='MZN'), '2026-10-03', '2026-10-03', 'today')['amount'] == 100
assert m.get_total('invoices')['amount'] == 75
assert m.get_total('receivable')['amount'] == 20
assert m.get_total('paid')['amount'] == 40
assert m.get_total('paid')['unallocated_amount'] == 6
# A partly delivered taxed/discounted order uses item quantities, not per_delivered.
docs = {'SO': types.SimpleNamespace(name='SO', transaction_date='2026-10-03', customer='C', status='To Deliver and Bill',
                  base_total=100, base_grand_total=90, items=[Row(name='SOI', qty=10, delivered_qty=4, base_amount=100)])}
frappe.get_doc = lambda dt, name: docs[name]
assert m.get_total('pending_delivery')['amount'] == 54
# The list filters must exclude closed/completed/cancelled orders.
saved_list = m._list
def checked_list(dt, filters, fields, **kw):
    if dt == 'Payment Entry':
        assert filters['payment_type'] == 'Receive'
        assert filters['party_type'] == 'Customer'
        assert filters['posting_date'] == ['between', ['2026-10-01', '2026-10-03']]
    if dt == 'Sales Order' and 'status' in filters:
        if filters['status'] == 'Closed':
            assert filters['custom_replaced_by'] == ['is', 'not set']
            return []
        assert filters['status'] == ['not in', ['Closed', 'Completed', 'Cancelled']]
    if dt == 'Delivery Note': return []
    return saved_list(dt, filters, fields, **kw)
m._list = checked_list
unbilled = types.ModuleType('solua_home.api.unbilled')
unbilled.get_rows = lambda *args: [dict(doctype='Delivery Note', name='DN', date='2026-10-03', customer='C', amount=0, price_adjustment=3)]
sys.modules['solua_home.api.unbilled'] = unbilled
assert m.get_total('paid')['amount'] == 40
assert m.METRICS['orders'] == '净订单金额'
assert m.METRICS['invoices'] == '开票净额'
assert m.METRICS['receivable'] == '净应收款'
assert m.METRICS['paid'] == '实际收款金额'
assert m.get_total('orders')['amount'] == 129
reconciliation = m.get_reconciliation()
assert reconciliation['amount'] == 25
assert sum(group['amount'] for group in reconciliation['groups']) == 25
assert reconciliation['groups'][-1]['label'].startswith('其他差额')  # residual is visible, never silently discarded
home._can_read = m._can_read = lambda dt: False
assert m.get_total('paid')['state'] == 'no_permission'
assert m.get_total('paid')['amount'] is None
assert m.get_total('pending_delivery')['amount'] is None
assert m.get_reconciliation()['state'] == 'no_permission'
print('PASS: week/quarter/year/custom, invalid dates, totals, FX, actual customer receipts and permission boundary')
