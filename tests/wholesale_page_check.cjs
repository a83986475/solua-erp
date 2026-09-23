// Candidate page rendering and route behavior without a site mutation.
const assert=require("node:assert/strict"),fs=require("node:fs"),vm=require("node:vm"),path=require("node:path");
const base=path.join(__dirname,".."),nodes=new Map(),roots=[];
function node(key){if(!nodes.has(key)) nodes.set(key,{content:"",visible:true,classes:{},html(v){this.content=v;return this;},text(v){this.content=v;return this;},val(){return "";},click(){},on(){return this;},toggle(show){this.visible=!!show;return this;},toggleClass(cls,show){this.classes[cls]=show===undefined?!this.classes[cls]:!!show;return this;}});return nodes.get(key);}
function makeRoot(){const root={handlers:[],html(){return this;},find:node,on(event,selector,handler){this.handlers.push({event,selector,handler});return this;}};roots.push(root);return root;}
const calls=[],routes=[],newDocs=[],opened=[];
const data={state:"ok",company:"Company",currency:"MZN",permissions:{},
 stock_entry_types:{issue:"Material Issue",consumption:"Consumption",wastage:"Wastage"},
 invoiced_today:{state:"no_permission",amount:0},outstanding:{state:"no_permission",amount:0},
 orders_pending:{state:"no_permission",count:0},delivered_today:{state:"no_permission",amount:0},
 low_stock:{state:"no_permission",count:0},pending_purchase:{state:"no_permission"},
 overdue:{state:"no_permission"},item_data:{state:"no_permission",missing_image:null,missing_color_code:null}};
const dialogs=[],synced=[],docCalls=[];
function FakeDialog(options){dialogs.push(options);this.options=options;this.show=()=>{this.shown=true;};this.hide=()=>{this.hidden=true;};}
const frappe={pages:{"solua-home":{}},ui:{make_app_page:()=>({main:makeRoot()}),Dialog:FakeDialog},utils:{escape_html:String},
 model:{sync:(doc)=>synced.push(doc)},db:{exists:async()=>true},
 router:{slug:(value)=>String(value).toLowerCase().replace(/[^a-z0-9]+/g,"-")},
 workspaces:{selling:{name:"Selling"},stock:{name:"Stock"},buying:{name:"Buying"},invoicing:{name:"Invoicing"}},
 call:async()=>({message:data}),new_doc:(...args)=>newDocs.push(args),set_route:(...args)=>routes.push(args),msgprint:()=>{},route_options:null};
// __() interpolates {0} placeholders like Frappe does, so the assertions can read real text.
const tr=(text,args)=>Array.isArray(args)?args.reduce((out,value,index)=>out.replace(`{${index}}`,value),text):text;
const context={frappe,__:tr,format_currency:(v,c)=>v+" "+c,window:{open:(...args)=>opened.push(args),solua_home:{
 label_print:{open:()=>calls.push("label")},promotion_wizard:{open:()=>calls.push("promotion")},pos:{open_closing:()=>calls.push("pos")}}}};
const pageSource=fs.readFileSync(path.join(base,"solua_wholesale/page/solua_home/solua_home.js"),"utf8");
vm.runInNewContext(pageSource,context);
frappe.pages["solua-home"].on_page_load({});
setImmediate(async()=>{
 let root=roots.at(-1);
 const cards=node('[data-role="cards"]').content;
 assert(!cards.includes('value">0'));assert.equal((cards.match(/value">—/g)||[]).length,5);
 assert(!node('[data-role="actions"]').content.includes("Stock Reconciliation"));
 assert(node('[data-role="pending"]').content.includes("待到货采购订单"));
 const dataStatus=node('[data-role="data-status"]').content;
 assert(dataStatus.includes("商品资料")&&dataStatus.includes("无权限查看"));
 assert(dataStatus.includes("—")&&!dataStatus.includes("缺图片 0"));
 const listHandler=root.handlers.find(h=>h.selector.includes("solua-home-list-row")).handler;
 listHandler.call({dataset:{doctype:"Item"}});assert.deepEqual(routes.pop(),["List","Item",null]);
 // 资料准备 names the offending items and offers a list holding exactly those items.
 data.item_data={state:"ok",item_count:92,checked_count:84,template_count:8,missing_image:2,missing_color_code:1,issues:[
  {key:"missing_image",label:"缺图片",hint:"这些物料还没有商品图片",field:"image",count:2,truncated:false,
   items:[{name:"SH151138-2MS",item_name:"2米单杆螺旋头",item_group:"窗帘杆"},{name:"SH151145-2MD",item_name:"2米双杆螺旋头",item_group:"窗帘杆"}]},
  {key:"missing_color_code",label:"缺固定色号",hint:"这些物料有颜色属性但没有填固定色号",field:"custom_color_code",count:1,truncated:false,
   items:[{name:"SH151046",item_name:"暗影",item_group:"窗帘"}]},
  {key:"missing_barcode",label:"缺条码",hint:"这些物料还没有条码",field:"barcode",count:0,truncated:false,items:[]}]};
 frappe.pages["solua-home"].on_page_load({});await new Promise(resolve=>setImmediate(resolve));root=roots.at(-1);
 const issuePanel=node('[data-role="data-status"]').content;
 assert(issuePanel.includes("共 92 条启用物料，其中 84 条单品/变体参与检查，模板 8 条不计"),"the panel must state the checked scope");
 assert(issuePanel.includes("SH151138-2MS")&&issuePanel.includes("SH151046"),"every issue must name its items");
 assert(issuePanel.includes('data-issue-toggle="missing_image"')&&issuePanel.includes('data-issue-body="missing_image"'));
 assert(issuePanel.includes('data-name="SH151145-2MD"'),"an issue links straight to the item form");
 assert(issuePanel.includes("已齐全"),"a clean check reads as resolved instead of a fake zero");
 assert(issuePanel.includes('data-filters=')&&issuePanel.includes('[&quot;in&quot;')||issuePanel.includes('["in"'),"the drill-down carries an in-filter");
 const toggleHandler=root.handlers.find(h=>h.selector.includes("data-issue-toggle")).handler;
 toggleHandler.call({dataset:{issueToggle:"missing_image"},classList:{toggle(){}}});
 assert.equal(node('[data-issue-body="missing_image"]').classes["solua-home-issue-open"],true);
 const issueListHandler=root.handlers.find(h=>h.selector.includes("solua-home-list-row")).handler;
 frappe.route_options=null;
 issueListHandler.call({dataset:{doctype:"Item",filters:JSON.stringify({name:["in",["SH151138-2MS","SH151145-2MD"]]})}});
 assert.deepEqual(routes.pop(),["List","Item",null]);
 // JSON.parse runs inside the page context, so compare the shape, not the object identity.
 assert.equal(JSON.stringify(frappe.route_options),JSON.stringify({name:["in",["SH151138-2MS","SH151145-2MD"]]}));
 issueListHandler.call({dataset:{doctype:"Item",filters:"{not json"}});
 assert.equal(frappe.route_options,null);assert.deepEqual(routes.pop(),["List","Item",null]);
 data.permissions={new_item:true,new_stock_entry:true,new_stock_reconciliation:true,new_purchase_receipt:true,
  new_sales_order:true,new_delivery_note:true,read_item:true,read_customer:true,read_supplier:true,
  read_print_settings:true,read_print_format:true,new_pricing_rule:true,read_pos_closing:true,
  read_sales_order:true,read_delivery_note:true,read_sales_invoice:true,read_pos_invoice:true,read_quotation:true,
  read_stock_entry:true,read_warehouse:true,read_stock_reconciliation:true,read_purchase_receipt:true,
  new_purchase_order:true,read_purchase_order:true,read_purchase_invoice:true,
  new_payment_entry:true,read_payment_entry:true};
 frappe.pages["solua-home"].on_page_load({});
 await new Promise(resolve=>setImmediate(resolve));root=roots.at(-1);
 const actions=node('[data-role="actions"]').content;
 for (const label of ["销售","新建销售订单","销售订单","新建交货单","按销售订单开交货单","交货单","销售发票","POS 销售单","报价单","客户/门店","优惠/促销管理","库存","新建物料","物料列表","库存入库","物料出库","领用","损耗","出入库记录","手机扫码盘点","盘点单","仓库与库位","采购","新建采购订单","采购订单","采购收货","收货记录","采购发票","供应商","财务","新建收款单","收付款单","打印与标签","打印设置","打印设计","销售单格式","标签打印","其他入口","POS交班","公开色卡","xPos 收银台"])
  assert(actions.includes(label),"missing homepage action: "+label);
 // Group titles are the entrance to the module workspace, so each block is a one-click jump.
 for (const workspace of ["Selling","Stock","Buying","Invoicing"])
  assert(actions.includes('data-workspace="'+workspace+'"'),"missing workspace link: "+workspace);
 assert(actions.includes('class="solua-home-group-title solua-home-group-title-link"'));
 assert(actions.includes('data-doctype="Print Format" data-view="list"'));
 assert(actions.includes('data-doctype="Sales Order" data-name="" data-view="list"'));
 assert(actions.includes('data-doctype="POS Invoice" data-name="" data-view="list"'));
 assert(actions.includes('data-doctype="Stock Entry" data-name="" data-view="list"'));
 assert(actions.includes('data-new-doc="1"'));assert(actions.includes('data-purpose="Material Issue"'));
 assert(actions.includes('data-stock-entry-type="Consumption"'));assert(actions.includes('data-stock-entry-type="Wastage"'));
 const actionHandler=root.handlers.find(h=>h.selector.includes("solua-home-action")).handler;
 actionHandler.call({dataset:{doctype:"Item",newDoc:"1"}});assert.equal(frappe.route_options,null);assert.deepEqual(newDocs.pop(),["Item"]);
 for (const options of [
  {purpose:"Material Receipt",stockEntryType:"Material Receipt"},
  {purpose:"Material Issue",stockEntryType:"Material Issue"},
  {purpose:"Material Issue",stockEntryType:"Consumption"},
  {purpose:"Material Issue",stockEntryType:"Wastage"},
 ]) {
  actionHandler.call({dataset:{doctype:"Stock Entry",...options}});
  assert.equal(frappe.route_options.purpose,options.purpose);
  assert.equal(frappe.route_options.stock_entry_type,options.stockEntryType);
  assert.deepEqual(newDocs.pop(),["Stock Entry"]);
 }
 actionHandler.call({dataset:{utility:"print_settings"}});assert.deepEqual(routes.pop(),["Form","Print Settings"]);
 actionHandler.call({dataset:{utility:"print_designer"}});assert.deepEqual(routes.pop(),["print-designer"]);
 actionHandler.call({dataset:{utility:"label_print"}});actionHandler.call({dataset:{utility:"promotion"}});actionHandler.call({dataset:{utility:"pos_closing"}});
 assert.deepEqual(calls,["label","promotion","pos"]);
 actionHandler.call({dataset:{utility:"xpos"}});assert.equal(opened.at(-1)[0],"/desk/x-pos?sidebar=X%20POS");
 // Delivery Note entry lives once in the sales block, after the create-sales-order shortcut.
 assert.equal((actions.match(/新建交货单/g)||[]).length,1);
 const sellGroup=actions.indexOf("销售");
 assert(sellGroup>-1&&sellGroup<actions.indexOf("库存")&&actions.indexOf("新建交货单")>sellGroup);
 assert(actions.indexOf("新建交货单")>actions.indexOf("新建销售订单"));
 // Clicking a group title opens the module workspace; a missing workspace falls back to the list.
 const before=newDocs.length;
 actionHandler.call({dataset:{workspace:"Selling",fallbackView:"Sales Order"}});assert.deepEqual(routes.pop(),["selling"]);
 actionHandler.call({dataset:{workspace:"Assets",fallbackView:"Sales Order"}});assert.deepEqual(routes.pop(),["List","Sales Order",null]);
 // View buttons must always open a list, never a blank new document.
 actionHandler.call({dataset:{doctype:"Delivery Note",view:"list"}});assert.deepEqual(routes.pop(),["List","Delivery Note",null]);
 actionHandler.call({dataset:{doctype:"Stock Entry",view:"list"}});assert.deepEqual(routes.pop(),["List","Stock Entry",null]);
 assert.equal(newDocs.length,before);
 const savedCall=frappe.call;
 frappe.call=(opts)=>{docCalls.push(opts);if(opts.method.includes("make_delivery_note")) opts.callback({message:{doctype:"Delivery Note",name:"MAT-DN-CHECK"}});return Promise.resolve({message:data});};
 actionHandler.call({dataset:{utility:"wholesale_print_format"}});
 await new Promise(resolve=>setImmediate(resolve));
 assert.deepEqual(routes.pop(),["Form","Print Format","批发销售单（颜色版）"]);
 actionHandler.call({dataset:{utility:"delivery_from_order"}});
 assert.equal(dialogs.length,1);
 assert.equal(dialogs.at(-1).fields[0].fieldtype,"Link");
 assert.equal(dialogs.at(-1).fields[0].options,"Sales Order");
 const orderFilters=dialogs.at(-1).fields[0].get_query().filters;
 assert.equal(JSON.stringify(orderFilters.status),JSON.stringify(["not in",["Closed","Completed","Cancelled"]]));
 assert.equal(JSON.stringify(orderFilters.per_delivered),JSON.stringify(["<",100]));
 assert.equal(orderFilters.docstatus,1);
 dialogs.at(-1).primary_action({sales_order:"SO-CHECK"});
 assert.equal(docCalls.at(-1).method,"erpnext.selling.doctype.sales_order.sales_order.make_delivery_note");
 assert.equal(docCalls.at(-1).args.source_name,"SO-CHECK");
 assert.deepEqual(synced.at(-1),{doctype:"Delivery Note",name:"MAT-DN-CHECK"});
 assert.deepEqual(routes.pop(),["Form","Delivery Note","MAT-DN-CHECK"]);
 frappe.call=savedCall;
 let current=[],target=null;
 const globals={boot:{solua_home:{}},provide(){},get_route:()=>current,set_route:value=>{target=value;},router:{on(){throw new Error("default route hook must not be registered");}}};
 const source=fs.readFileSync(path.join(base,"public/js/solua_home_global.js"),"utf8").split("\n(function () {")[0];
 vm.runInNewContext(source,{frappe:globals,$:fn=>fn()});assert.equal(target,null);
 for (const [file,id] of [["public/js/label_print.js","lp-float-btn"],["public/js/promotion_wizard.js","pm-float-btn"],["public/js/pos_custom.js","pos-closing-btn"]])
  assert(!fs.readFileSync(path.join(base,file),"utf8").includes(id),"floating entry remains: "+file);
 // POS cashier mode: the till entries only, business panels hidden, no business payload used.
 const posData={state:"ok",home_mode:"pos",pos_profile:"收银方式1 - SH",company:"Company",currency:"MZN",
  query_time:"2026-09-21 12:00:00",permissions:{read_pos_closing:true,read_pos_invoice:true,read_item:true},stock_entry_types:{}};
 frappe.call=async()=>({message:posData});
 frappe.pages["solua-home"].on_page_load({});await new Promise(resolve=>setImmediate(resolve));
 root=roots.at(-1);
 const posActions=node('[data-role="actions"]').content;
 for (const label of ["收银","开始收银（xPos）","POS交班","POS 销售单"])
  assert(posActions.includes(label),"cashier homepage is missing: "+label);
 for (const label of ["新建销售订单","销售订单","交货单","新建物料","库存入库","盘点单","采购订单","新建收款单","打印设置","标签打印","客户/门店","优惠/促销管理","公开色卡"])
  assert(!posActions.includes(label),"cashier homepage must hide: "+label);
 // the fake find() keys by selector, so the combined selector is the toggled node
 assert.equal(node('[data-section="overview"], [data-section="pending"], [data-section="data-status"]').visible,false);
 assert.equal(node('[data-section="actions"]').visible,true);
 assert.equal(node('[data-section="search"]').visible,true);
 assert.equal(node('[data-role="actions-title"]').content,"收银");
 assert.equal(node(".solua-home-columns").classes["solua-home-columns-single"],true);
 assert.equal(node('[data-role="cards"]').content,"");
 assert.equal(node('[data-role="pending"]').content,"");
 assert.equal(node('[data-role="data-status"]').content,"");
 assert(node('[data-role="state"]').content.includes("收银方式1 - SH"),"cashier must see the POS profile");
 // an admin refresh afterwards must restore the full desk layout
 frappe.call=async()=>({message:data});
 frappe.pages["solua-home"].on_page_load({});await new Promise(resolve=>setImmediate(resolve));
 assert.equal(node('[data-section="overview"], [data-section="pending"], [data-section="data-status"]').visible,true);
 assert.equal(node(".solua-home-columns").classes["solua-home-columns-single"],false);
 assert.equal(node('[data-role="actions-title"]').content,"常用功能");
 frappe.call=async()=>{throw new Error("network failure")};
 frappe.pages["solua-home"].on_page_load({});await new Promise(resolve=>setImmediate(resolve));
 assert.equal(node('[data-role="cards"]').content,"");assert(node('[data-role="state"]').content.includes("加载失败"));
 console.log("PASS: permission-gated grouped actions with workspace headers and view shortcuts; 资料准备 drill-down names the offending items (templates excluded) and deep-links to just those items; cashier POS-only mode (business panels hidden, till entries only); native routes; tool entry preservation; no floaters; admin-safe default route; retry error state");
});
