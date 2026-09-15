// Candidate page rendering and route behavior without a site mutation.
const assert=require("node:assert/strict"),fs=require("node:fs"),vm=require("node:vm"),path=require("node:path");
const base=path.join(__dirname,".."),nodes=new Map(),roots=[];
function node(key){if(!nodes.has(key)) nodes.set(key,{content:"",html(v){this.content=v;return this;},text(v){this.content=v;return this;},val(){return "";},click(){},on(){return this;}});return nodes.get(key);}
function makeRoot(){const root={handlers:[],html(){return this;},find:node,on(event,selector,handler){this.handlers.push({event,selector,handler});return this;}};roots.push(root);return root;}
const calls=[],routes=[],newDocs=[],opened=[];
const data={state:"ok",company:"Company",currency:"MZN",permissions:{},
 invoiced_today:{state:"no_permission",amount:0},outstanding:{state:"no_permission",amount:0},
 orders_pending:{state:"no_permission",count:0},delivered_today:{state:"no_permission",amount:0},
 low_stock:{state:"no_permission",count:0},pending_purchase:{state:"no_permission"},
 overdue:{state:"no_permission"},item_data:{state:"no_permission"}};
const frappe={pages:{"solua-home":{}},ui:{make_app_page:()=>({main:makeRoot()})},utils:{escape_html:String},
 call:async()=>({message:data}),new_doc:(...args)=>newDocs.push(args),set_route:(...args)=>routes.push(args),msgprint:()=>{},route_options:null};
const context={frappe,__:s=>s,format_currency:(v,c)=>v+" "+c,window:{open:(...args)=>opened.push(args),solua_home:{
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
 data.permissions={new_item:true,new_stock_entry:true,new_stock_reconciliation:true,new_purchase_receipt:true,
  new_sales_order:true,new_delivery_note:true,read_item:true,read_customer:true,read_supplier:true,
  read_print_settings:true,read_print_format:true,new_pricing_rule:true,read_pos_closing:true};
 frappe.pages["solua-home"].on_page_load({});
 await new Promise(resolve=>setImmediate(resolve));root=roots.at(-1);
 const actions=node('[data-role="actions"]').content;
 for (const label of ["库存管理","标签打印","优惠/促销","新建物料","物料出库","领用（Material Issue）","损耗（Material Issue）","打印设置","打印设计","标签打印","优惠/促销管理","POS交班","xPos 现有入口"])
  assert(actions.includes(label),"missing homepage action: "+label);
 assert(actions.includes('data-new-doc="1"'));assert(actions.includes('data-purpose="Material Issue"'));
 const actionHandler=root.handlers.find(h=>h.selector.includes("solua-home-action")).handler;
 actionHandler.call({dataset:{doctype:"Item",newDoc:"1"}});assert.deepEqual(newDocs.pop(),["Item"]);
 actionHandler.call({dataset:{doctype:"Stock Entry",purpose:"Material Issue"}});assert.equal(frappe.route_options.purpose,"Material Issue");assert.deepEqual(newDocs.pop(),["Stock Entry"]);
 actionHandler.call({dataset:{utility:"print_settings"}});assert.deepEqual(routes.pop(),["Form","Print Settings"]);
 actionHandler.call({dataset:{utility:"print_designer"}});assert.deepEqual(routes.pop(),["print-designer"]);
 actionHandler.call({dataset:{utility:"label_print"}});actionHandler.call({dataset:{utility:"promotion"}});actionHandler.call({dataset:{utility:"pos_closing"}});
 assert.deepEqual(calls,["label","promotion","pos"]);
 actionHandler.call({dataset:{utility:"xpos"}});assert.equal(opened.at(-1)[0],"/desk/x-pos?sidebar=X%20POS");
 let current=[],target=null;
 const globals={boot:{solua_home:{}},provide(){},get_route:()=>current,set_route:value=>{target=value;},router:{on(){throw new Error("default route hook must not be registered");}}};
 const source=fs.readFileSync(path.join(base,"public/js/solua_home_global.js"),"utf8").split("\n(function () {")[0];
 vm.runInNewContext(source,{frappe:globals,$:fn=>fn()});assert.equal(target,null);
 for (const [file,id] of [["public/js/label_print.js","lp-float-btn"],["public/js/promotion_wizard.js","pm-float-btn"],["public/js/pos_custom.js","pos-closing-btn"]])
  assert(!fs.readFileSync(path.join(base,file),"utf8").includes(id),"floating entry remains: "+file);
 frappe.call=async()=>{throw new Error("network failure")};
 frappe.pages["solua-home"].on_page_load({});await new Promise(resolve=>setImmediate(resolve));
 assert.equal(node('[data-role="cards"]').content,"");assert(node('[data-role="state"]').content.includes("加载失败"));
 console.log("PASS: permission-gated grouped actions; native routes; tool entry preservation; no floaters; admin-safe default route; retry error state");
});
