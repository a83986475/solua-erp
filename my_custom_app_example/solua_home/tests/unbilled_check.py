"""No-site regression for already billed quantities, returns and invoice-backed deliveries."""
import importlib.util
import sys
import types
from pathlib import Path
frappe = types.ModuleType('frappe')
frappe.whitelist=frappe.read_only=lambda:lambda fn:fn
sys.modules['frappe']=frappe
utils=types.ModuleType('frappe.utils')
utils.flt=lambda value, *args:float(value or 0)
utils.date_diff=lambda *args:0
utils.nowdate=lambda:'2026-10-03'
sys.modules['frappe.utils']=utils
home=types.ModuleType('solua_home.api.home')
home._can_read=home._can_create=lambda dt:True
home._list=lambda *args,**kwargs:[]
sys.modules['solua_home.api.home']=home
spec=importlib.util.spec_from_file_location('unbilled',Path(__file__).resolve().parents[1]/'api/unbilled.py')
m=importlib.util.module_from_spec(spec)
spec.loader.exec_module(m)
row={'qty':10,'rate':100,'billed_amt':0}
assert m.pending_qty(row)==10
assert m.pending_qty(row,4,2)==4
assert m.pending_qty({**row,'billed_amt':600},10,0)==0  # price changes never become quantity
assert m.pending_qty({**row,'billed_amt':1200},0,1)==9
assert m.pending_qty({**row,'si_detail':'invoice-item'})==0
assert m.pending_qty(row,0,10)==0
assert m.pending_qty({**row,'rate':0})==10
assert m.price_adjustment({**row,'billed_amt':600},covered_qty=10)==400
assert m.price_adjustment({**row,'billed_amt':700},covered_qty=10)==300  # credit-note price adjustment stays separate
assert m.price_adjustment({**row,'billed_amt':1000},returned_qty=2,covered_qty=10)==0  # physical return is not a price adjustment
assert m.allocate_sales_order_qty([
    {'name':'DN2','parent':'DN2','qty':6,'posting_date':'2026-10-02','direct_invoiced_qty':0},
    {'name':'DN1','parent':'DN1','qty':4,'posting_date':'2026-10-01','direct_invoiced_qty':0},
], 6)=={'DN1':4,'DN2':2}
print('PASS: quantity billing, direct-SO FIFO, price changes, returns, pre-invoiced delivery and free items')

# Sales Order invoices count by quantity; credit notes do not create negative billable quantity.
class Doc:
    name='DN'; company='Co'; items=[types.SimpleNamespace(name='DN-ROW', so_detail='SO-ROW')]
m._submitted_invoice_rows=lambda company:[
    {'so_detail':'SO-ROW','qty':10,'is_return':0},
    {'so_detail':'SO-ROW','qty':-2,'is_return':1},
]
m._delivery_rows_by_so_detail=lambda company, details:{'SO-ROW':[{'name':'DN-ROW','parent':'DN','so_detail':'SO-ROW','qty':10,'posting_date':'2026-10-01'}]}
assert m.invoice_qty_map('Co',[Doc()])=={'DN':{'DN-ROW':10}}
print('PASS: submitted Sales Order invoice chain ignores credit-note quantity')

draft_item=types.SimpleNamespace(delivery_note='', so_detail='SO-ROW')
m._list=lambda *args,**kwargs:[types.SimpleNamespace(name='SO-DRAFT')]
m.frappe.get_doc=lambda *args:types.SimpleNamespace(name='SO-DRAFT', items=[draft_item])
assert m.linked_drafts('Co', {'DN'}, {'SO-ROW':['DN']})=={'DN':['SO-DRAFT']}
print('PASS: Sales Order draft is linked to the delivered row for duplicate protection')

# Existing drafts remain viewable to readers and never call the invoice mapper.
class Source:
    name='DN';company='Test';docstatus=1;is_return=0;status='To Bill'
    items=[]
    def check_permission(self, permission): assert permission=='read'
m.frappe.get_doc=lambda *args:Source()
m._can_create=lambda dt:False
m.linked_drafts=lambda *args:{'DN':['DRAFT']}
m.billing_module=lambda:types.SimpleNamespace(make_sales_invoice=lambda *args,**kw:(_ for _ in ()).throw(AssertionError('duplicate')),get_invoiced_qty_map=lambda dn:{},get_returned_qty_map=lambda dn:{})
assert m.prepare_invoice('DN')=={'draft_invoices':['DRAFT']}
print('PASS: existing draft opens for readers without generating a duplicate')
