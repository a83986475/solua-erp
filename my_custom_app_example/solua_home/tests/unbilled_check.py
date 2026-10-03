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
assert m.pending_qty({**row,'billed_amt':600},4,2)==2  # also accounts for invoices made directly from SO
assert m.pending_qty({**row,'billed_amt':1200},0,1)==0
assert m.pending_qty({**row,'si_detail':'invoice-item'})==0
assert m.pending_qty(row,0,10)==0
assert m.pending_qty({**row,'rate':0})==10
print('PASS: partial billing, direct-SO billing, returns, overbilling, pre-invoiced delivery and free items')
