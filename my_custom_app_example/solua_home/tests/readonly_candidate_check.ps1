# All candidates travel over stdin, remain in memory, use a read-only transaction.
$appRoot = Split-Path $PSScriptRoot -Parent
$payload = @{}
foreach ($pair in @(
    @("home", "api/home.py"), @("printing", "printing/wholesale.py"),
    @("stock", "api/stock.py"), @("boot", "boot.py"), @("install", "install.py"), @("hooks", "hooks.py"),
    @("page_js", "solua_wholesale/page/solua_home/solua_home.js"),
    @("page_css", "solua_wholesale/page/solua_home/solua_home.css"),
    @("so", "print_format/sales_order_wholesale_color/sales_order_wholesale_color.json"),
    @("dn", "print_format/delivery_note_guia_remessa/delivery_note_guia_remessa.json")
)) { $payload[$pair[0]] = Get-Content -Raw (Join-Path $appRoot $pair[1]) }
$payloadBase64 = [Convert]::ToBase64String([Text.Encoding]::UTF8.GetBytes(($payload | ConvertTo-Json -Compress)))
$script = @'
import base64,json,sys,types,io,os
from unittest.mock import patch
import frappe
payload=json.loads(base64.b64decode("PAYLOAD"))
frappe.init(site="erp.solua.one",sites_path="/home/frappe/frappe-bench/sites")
frappe.connect()
try:
 frappe.db.sql("SET TRANSACTION READ ONLY")
 frappe.set_user("yangyang7920@gmail.com")
 home=types.ModuleType("candidate_home")
 exec(compile(payload["home"],"candidate_home.py","exec"),home.__dict__)
 dashboard=home.get_dashboard_data()
 print("DASHBOARD",json.dumps({k:dashboard.get(k) for k in ("state","company","invoiced_today","outstanding","permissions")},ensure_ascii=False,default=str))
 print("SEARCH",home.search_items("__SOLUA_READONLY_NO_MATCH__"))
 printing=types.ModuleType("candidate_printing")
 exec(compile(payload["printing"],"candidate_printing.py","exec"),printing.__dict__)
 candidates={}
 for key,name in (("home","solua_home.api.home"),("stock","solua_home.api.stock"),("printing","solua_home.printing.wholesale"),("boot","solua_home.boot"),("install","solua_home.install")):
  candidate=types.ModuleType(name)
  exec(compile(payload[key],name,"exec"),candidate.__dict__)
  sys.modules[name]=candidate
  candidates[key]=candidate
 hooks={}
 exec(compile(payload["hooks"],"candidate_hooks.py","exec"),hooks)
 methods=[]
 for events in hooks["doc_events"].values():
  for value in events.values():
   methods.extend(value if isinstance(value,list) else [value])
 methods.extend(hooks["jinja"]["methods"])
 methods.extend(hooks["override_whitelisted_methods"].values())
 methods.append(hooks["extend_bootinfo"])
 for method in methods:
  assert callable(frappe.get_attr(method)),method
 print("HOOK_IMPORTS",len(methods),"PASS")
 bootinfo={}
 candidates["boot"].extended_bootinfo(bootinfo)
 assert "home_page" not in bootinfo
 print("BOOT_HOME_PAGE","not injected; native desktop:home_page remains authoritative")
 print("API_HOME_PAGE_HELPER",home.get_home_page(frappe.session.user))
 from frappe.utils.jinja import get_jenv
 env=get_jenv()
 env.globals["get_wholesale_print_data"]=printing.get_wholesale_print_data
 env.globals["get_delivery_invoice_names"]=lambda name: []
 env.globals["get_color_card_qr_img"]=lambda code: ""
 frozen={"version":1,"company":{"name":"Solua Home","nuit":"COMPANY","address":"AV. DO TRABALHO","phone":"1"},"customer":{"name":"Memory only","nuit":"CUSTOMER","address":"Memory address","store":"A","contact":"Contact","phone":"2"},"order":{"name":"MEMORY-SO"},"transport":{"departure_time":"2026-09-15 10:00:00","source_address":"Origin","vehicle_no":"ABC","driver_name":"Driver","driver_phone":"3"},"invoice_plan":"Invoice after delivery","payment_method":"COD","deposit":0,"balance_due_date":"","items":[{"item_code":"MEMORY","item_name":"Curtain","order_code":"MEMORY","color":"Red","color_code":"01","image":"","template_code":"","uom":"Unit","qty":2,"rate":10,"amount":20,"ordered_qty":5,"delivered_before_qty":1,"remaining_qty":2,"batch_no":"","serial_no":"","serial_and_batch_bundle":""}]}
 for key,dt in (("so","Sales Order"),("dn","Delivery Note")):
  fmt=json.loads(payload[key]);doc=frappe.get_doc({"doctype":dt,"name":"MEMORY-ONLY","docstatus":0,"currency":"MZN","grand_total":20,"transaction_date":"2026-09-15","posting_date":"2026-09-15","custom_wholesale_snapshot":json.dumps(frozen)})
  output=env.from_string(fmt["html"]).render(doc=doc)
  assert "Curtain" in output and "COMPANY" in output
  print("FRAPPE_JINJA",dt,"PASS",len(output))
 module=types.ModuleType("solua_home.solua_wholesale")
 module.__file__="/home/frappe/frappe-bench/apps/solua_home/solua_wholesale/__init__.py"
 module.__path__=[os.path.dirname(module.__file__)];sys.modules[module.__name__]=module
 frappe.local.module_app["solua_wholesale"]="solua_home"
 module_path=frappe.get_module_path("Solua Wholesale");page_path=os.path.join(module_path,"page","solua_home")
 virtual={os.path.join(page_path,"solua_home.js"):payload["page_js"],os.path.join(page_path,"solua_home.css"):payload["page_css"]}
 original_open=open;original_exists=os.path.exists;original_listdir=os.listdir
 def read_virtual(path,*args,**kwargs):
  return io.StringIO(virtual[os.fspath(path)]) if os.fspath(path) in virtual else original_open(path,*args,**kwargs)
 page=frappe.get_doc({"doctype":"Page","name":"solua-home","module":"Solua Wholesale"})
 with patch("builtins.open",read_virtual),patch("os.path.exists",lambda p:p in virtual or original_exists(p)),patch("os.listdir",lambda p:["solua_home.js","solua_home.css"] if p==page_path else original_listdir(p)):
  page.load_assets()
 assert "new_stock_reconciliation" in page.script and "solua-home" in page.style
 print("MODULE_AND_PAGE_VIRTUAL_ASSETS",module_path,"PASS (candidate in memory, not installed)")
 print("NAVBAR_LOGO",frappe.db.get_single_value("Navbar Settings","app_logo"))
finally:
 frappe.db.rollback();frappe.destroy()
'@
$script.Replace("PAYLOAD", $payloadBase64) | ssh qq 'sudo -u frappe -H bash -lc "cd /home/frappe/frappe-bench && env/bin/python"'
if ($LASTEXITCODE -ne 0) { throw "Read-only candidate check failed: $LASTEXITCODE" }
