// Run: node my_custom_app_example/solua_home/tests/wholesale_forms_check.cjs
const assert = require("node:assert/strict");
const fs = require("node:fs");
const vm = require("node:vm");
const path = require("node:path");
const handlers = {}, requests = [], dialogs = [];
const input = () => ({events:{}, on(event, fn){this.events[event]=fn;return this;}, focus(){}});
class Dialog {
  constructor(options) {
    this.action=options.primary_action;
    this.values = {}; this.fields_dict = {}; this.$wrapper = input();
    for (const f of options.fields) {
      this.values[f.fieldname] = f.default ?? "";
      this.fields_dict[f.fieldname] = {...f,$input:input(), $wrapper:{html(){},empty(){}}};
    }
    dialogs.push(this);
  }
  get_value(key){return this.values[key];}
  async set_value(key, value){this.values[key]=value;}
  set_df_property(key, property, value){this.fields_dict[key][property]=value;}
  set_primary_action(label, fn){this.label=label;this.action=()=>{
    // v16 validates required fields even when hidden.
    for(const [key,field] of Object.entries(this.fields_dict)){
      const value=this.values[key];
      if(field.reqd && (value==null || String(value).trim()==="")) return;
    }
    return fn();
  };}
  show(){}
}
const rows = new Map();
const frappe = {
  ui:{Dialog, form:{on(dt, value){handlers[dt]=value;}}},
  utils:{escape_html:String},
  call(){return new Promise((resolve,reject)=>requests.push({resolve,reject}));},
  model:{async set_value(dt,name,key,value){
    await Promise.resolve();
    const row=rows.get(name);row[key]=value;
    if(key==="item_code"){row.warehouse="NATIVE-DEFAULT";row.qty=99;row.rate=999;}
  }},
  show_alert(){},msgprint(){},
};
vm.runInNewContext(fs.readFileSync(path.join(__dirname,"../public/js/wholesale_forms.js"),"utf8"),
  {frappe, __:s=>s, Number, String, Promise, URLSearchParams, window:{open(){}}});
const flush = () => new Promise(resolve=>setImmediate(resolve));
function form(dt,status=0){
 const frm={doctype:dt,doc:{docstatus:status,items:[],set_warehouse:"W1"},buttons:[],
  add_custom_button(label,fn){this.buttons.push({label,fn});},refresh_field(){},
  add_child(){const row={doctype:"Row",name:String(rows.size+1)};rows.set(row.name,row);this.doc.items.push(row);return row;},
  dashboard:{add_comment(){}},is_new(){return true;}};
 handlers[dt].refresh(frm);return frm;
}
const data = {message:{templates:[{variants:[{name:"red",item_code:"red",color_code:"01",image:"/red.png"},{name:"blue",item_code:"blue"}]}]}};
async function query(d,code="A"){
 d.values.barcode=code;d.fields_dict.barcode.$input.events.input();
 const p=d.action();requests.at(-1).resolve(data);await p;
}
(async()=>{
 for(const dt of ["Purchase Receipt","Stock Reconciliation"]) assert.equal(form(dt,1).buttons.length,0);
 const receipt=form("Purchase Receipt");receipt.buttons[0].fn();const d=dialogs.at(-1);
 d.values.barcode="missing";let p=d.action();requests.at(-1).resolve({message:{templates:[]}});await p;
 assert.equal(d.label,"查询颜色");
 p=d.action();requests.at(-1).reject(new Error("offline"));await p;assert.equal(d.label,"查询颜色");
 await query(d);assert.equal(d.get_value("variant"),"");assert.equal(d.fields_dict.variant.options[0].value,"");
 d.values.variant="red";d.values.qty="0";d.values.rate=12;await d.action();assert.equal(receipt.doc.items.length,0);
 d.values.qty="1.5";await d.action();assert.equal(receipt.doc.items.length,0);
 d.values.qty="2";const add=d.action();const double=d.action();await Promise.all([add,double]);
 assert.equal(receipt.doc.items.length,1);assert.equal(receipt.doc.items[0].qty,2);
 assert.equal(receipt.doc.items[0].warehouse,"W1");assert.equal(receipt.doc.items[0].rate,12);
 assert.equal(d.values.qty,"");assert.equal(d.values.rate,"");assert.equal(d.values.barcode,"");
 await query(d);d.values.variant="red";d.values.qty="3";d.values.rate=12;d.values.duplicate_mode="append";await d.action();
 assert.equal(receipt.doc.items[0].qty,5);
 await query(d);d.values.variant="red";d.values.qty="1";d.values.rate=12;d.values.duplicate_mode="replace";await d.action();
 assert.equal(receipt.doc.items[0].qty,1);
 await query(d);d.values.variant="red";d.values.qty="1";d.values.rate=12;d.values.warehouse="W2";await d.action();
 assert.equal(receipt.doc.items.length,2);
 d.values.barcode="old";p=d.action();const old=requests.at(-1);
 d.values.barcode="new";d.fields_dict.barcode.$input.events.input();const newer=d.action();const recent=requests.at(-1);
 recent.resolve(data);await newer;old.resolve({message:{templates:[]}});await p;
 assert.equal(d.label,"加入单据");assert.equal(d.fields_dict.variant.options.length,3);
 d.values.barcode="changed";d.fields_dict.barcode.$input.events.input();assert.equal(d.values.variant,"");assert.equal(d.label,"查询颜色");
 const count=form("Stock Reconciliation");count.buttons[0].fn();const c=dialogs.at(-1);
 await query(c);c.values.variant="red";
 for(const invalid of ["","1.5","-1"]){c.values.qty=invalid;await c.action();assert.equal(count.doc.items.length,0);}
 c.values.qty="0";await c.action();assert.equal(count.doc.items.length,1);assert.equal(count.doc.items[0].qty,0);
 const submitted=form("Sales Order",1);submitted.is_new=()=>false;
 submitted.fields_dict={custom_print_color_images:{},custom_print_color_qr:{}};
 submitted.set_value=async()=>{};submitted.is_dirty=()=>true;
 let save_mode;submitted.save=async mode=>{save_mode=mode;};
 handlers["Sales Order"].refresh(submitted);
 assert.equal(submitted.buttons.length,1);
 submitted.buttons[0].fn();const print_dialog=dialogs.at(-1);print_dialog.hide=()=>{};
 await print_dialog.action({show_images:1,show_qr:0});assert.equal(save_mode,"Update");
 submitted.buttons=[];handlers["Sales Order"].refresh(submitted);assert.equal(submitted.buttons.length,1);
 await flush();console.log("PASS: retry, stale responses, explicit selection, reset, item+warehouse, append/replace, integer/zero/blank, double click, submitted guards");
})().catch(e=>{console.error(e);process.exitCode=1;});
