// Candidate page rendering and default-route behavior without a site mutation.
const assert=require("node:assert/strict"),fs=require("node:fs"),vm=require("node:vm"),path=require("node:path");
const base=path.join(__dirname,".."),nodes=new Map();
function node(key){if(!nodes.has(key)) nodes.set(key,{content:"",html(v){this.content=v;return this;},text(v){this.content=v;return this;},on(){return this;}});return nodes.get(key);}
const data={state:"ok",company:"Company",currency:"MZN",permissions:{},
 invoiced_today:{state:"no_permission",amount:0},outstanding:{state:"no_permission",amount:0},
 orders_pending:{state:"no_permission",count:0},delivered_today:{state:"no_permission",amount:0},
 low_stock:{state:"no_permission",count:0},pending_purchase:{state:"no_permission"},
 overdue:{state:"no_permission"},item_data:{state:"no_permission"}};
const root={html(){},find:node,on(){}};
const frappe={pages:{"solua-home":{}},ui:{make_app_page:()=>({main:root})},utils:{escape_html:String},
 call:async()=>({message:data})};
vm.runInNewContext(fs.readFileSync(path.join(base,"solua_wholesale/page/solua_home/solua_home.js"),"utf8"),
 {frappe,__:s=>s,format_currency:(v,c)=>v+" "+c});
frappe.pages["solua-home"].on_page_load({});
setImmediate(async()=>{
 const cards=node('[data-role="cards"]').content;
 assert(!cards.includes('value">0'));assert.equal((cards.match(/value">—/g)||[]).length,5);
 assert(!node('[data-role="actions"]').content.includes("Stock Reconciliation"));
 assert(node('[data-role="pending"]').content.includes("待到货采购订单"));
 let current=[],target=null,listener;
 const globals={boot:{solua_home:{default_page:"solua-home"}},provide(){},get_route:()=>current,
 set_route:value=>{target=value;},router:{on(event,fn){listener=fn;}}};
 const source=fs.readFileSync(path.join(base,"public/js/solua_home_global.js"),"utf8").split("\n(function () {")[0];
 vm.runInNewContext(source,{frappe:globals,$:fn=>fn()});
 assert.equal(target,"solua-home");
 target=null;current=["Form","Sales Order","SO-1"];listener();assert.equal(target,null);
 current=["desktop"];listener();assert.equal(target,"solua-home");
 globals.boot.solua_home.default_page=null;target=null;listener();assert.equal(target,null);
 frappe.call=async()=>{throw new Error("network failure");};
 frappe.pages["solua-home"].on_page_load({});
 await new Promise(resolve=>setImmediate(resolve));
 assert.equal(node('[data-role="cards"]').content,"");
 assert(node('[data-role="state"]').content.includes("加载失败"));
 console.log("PASS: no-permission cards show no zero; create permission; pending details; employee default and preserved deep links");
});
