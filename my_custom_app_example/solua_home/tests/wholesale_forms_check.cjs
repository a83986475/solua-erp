// Run: node my_custom_app_example/solua_home/tests/wholesale_forms_check.cjs
const assert = require("node:assert/strict");
const fs = require("node:fs");
const vm = require("node:vm");
const path = require("node:path");
const handlers = {}, requests = [], dialogs = [];
const input = () => ({events:{}, on(event, fn){this.events[event]=fn;return this;}, off(event){delete this.events[event];return this;}, focus(){}});
class Dialog {
  constructor(options) {
    this.action=options.primary_action;
    this.values = {}; this.fields_dict = {}; this.$wrapper = input();
    for (const f of options.fields) {
      this.values[f.fieldname] = f.default ?? "";
      const field = {...f,df:{...f},$input:input(),$wrapper:{html(){},empty(){}}};
      if (f.fieldtype === "Table") field.grid={get data(){return field.df.data || [];},get_selected_children(){return this.data.filter(row=>row.__checked);},refresh(){}};
      this.fields_dict[f.fieldname] = field;
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
  ui:{Dialog, form:{on(dt, value){handlers[dt]={...(handlers[dt] || {}),...value};}}},
  utils:{escape_html:String},
  call(){return new Promise((resolve,reject)=>requests.push({resolve,reject}));},
  model:{async set_value(dt,name,key,value){
    await Promise.resolve();
    const row=rows.get(name);row[key]=value;
    if(key==="item_code"){row.warehouse="NATIVE-DEFAULT";row.qty=99;row.rate=999;}
  }},
  show_alert(){},msgprint(){},
};
const browser = {open(){}};
const script_scope = {frappe, __:s=>s, Number, String, Promise, URLSearchParams, window:browser};
vm.runInNewContext(fs.readFileSync(path.join(__dirname,"../public/js/wholesale_forms.js"),"utf8"), script_scope);
vm.runInNewContext(fs.readFileSync(path.join(__dirname,"../public/js/sales_invoice_print_options.js"),"utf8"), script_scope);
const salesTools = browser.solua_home_sales_order_tools;
const flush = () => new Promise(resolve=>setImmediate(resolve));
function form(dt,status=0){
 const frm={doctype:dt,doc:{docstatus:status,items:[],set_warehouse:"W1"},buttons:[],dirty(){},
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
	assert.equal(salesTools.is_positive_integer("2"),true);
	assert.equal(salesTools.is_positive_integer("2.5"),false);
	const selection=[{__checked:0},{__checked:1},{__checked:0}];
	salesTools.set_table_selection(selection,true);assert.deepEqual(selection.map(r=>r.__checked),[1,1,1]);
	salesTools.invert_table_selection(selection);assert.deepEqual(selection.map(r=>r.__checked),[0,0,0]);
	for(const dt of ["Purchase Receipt","Stock Reconciliation"]) assert.equal(form(dt,1).buttons.length,0);
	const salesOrder = form("Sales Order");
	salesOrder.buttons[0].fn();
	assert.equal(dialogs.at(-1).label, "查询颜色");
	const salesColor = dialogs.at(-1);
	salesColor.values.default_qty=4;
	salesColor.values.barcode="TPL";salesColor.fields_dict.barcode.$input.events.input();
	let salesLookup=salesColor.action();
	requests.at(-1).resolve({message:{has_template:true,variants:[
		{name:"red",item_code:"red",color_code:"01",item_name:"Red",available_qty:7,rate:430,warehouse:"W1"},
		{name:"blue",item_code:"blue",color_code:"02",item_name:"Blue",available_qty:5,rate:430,warehouse:"W1"},
	]}});
	await salesLookup;
	assert.equal(salesColor.fields_dict.variant_items.df.data.length,2);
	assert.deepEqual(salesColor.fields_dict.variant_items.df.data.map(row=>row.qty),[4,4]);
	salesColor.fields_dict.variant_select_all.$input.events["click.solua"]();
	assert.deepEqual(salesColor.fields_dict.variant_items.df.data.map(row=>row.__checked),[1,1]);
	salesColor.fields_dict.variant_invert.$input.events["click.solua"]();
	assert.deepEqual(salesColor.fields_dict.variant_items.df.data.map(row=>row.__checked),[0,0]);
	salesColor.fields_dict.variant_invert.$input.events["click.solua"]();
	salesColor.fields_dict.variant_items.df.data[0].qty=2;
	salesColor.fields_dict.variant_items.df.data[1].qty=3;
	salesColor.fields_dict.variant_items.df.data[0].__checked=1;
	const batchAdd=salesColor.action();
	requests.at(-1).resolve({message:{rows:[
		{item_code:"red",item_name:"Red",description:"Red desc",uom:"条",stock_uom:"条",rate:430,price_list_rate:430,warehouse:"W1",qty:2,custom_item_barcode:"BAR-RED"},
		{item_code:"blue",item_name:"Blue",description:"Blue desc",uom:"条",stock_uom:"条",rate:430,price_list_rate:430,warehouse:"W1",qty:3,custom_item_barcode:"BAR-BLUE"},
	]}});
	await batchAdd;
	assert.deepEqual(salesOrder.doc.items.map(row=>row.qty),[2,3]);
	assert.equal(salesColor.values.barcode,"");
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
 async function assert_print_switches(dt) {
  const submitted=form(dt,1);submitted.is_new=()=>false;
  submitted.fields_dict={custom_print_item_name:{},custom_print_sku:{},custom_print_color_code:{},custom_print_cor:{},custom_print_description:{},custom_print_color_images:{},custom_print_color_qr:{},...(dt === "Delivery Note" ? {custom_print_ordered_before:{}} : {})};
  let saved_changes;submitted.set_value=async changes=>{saved_changes=changes;};submitted.is_dirty=()=>true;
  let save_mode;submitted.save=async mode=>{save_mode=mode;};
  handlers[dt].refresh(submitted);
  assert.equal(submitted.buttons.length,1);
  submitted.buttons[0].fn();const print_dialog=dialogs.at(-1);print_dialog.hide=()=>{};
  await print_dialog.action({show_item_name:0,show_sku:1,show_color_code:0,show_cor:1,show_description:0,show_ordered_before:0,show_images:1,show_qr:0});
  assert.equal(save_mode,"Update");
  const expected={custom_print_item_name:0,custom_print_sku:1,custom_print_color_code:0,custom_print_description:0,custom_print_color_images:1,custom_print_color_qr:0};
  if(dt === "Sales Invoice") expected.custom_print_cor=1;
  if(dt === "Delivery Note") expected.custom_print_ordered_before=0;
  const stable=value=>JSON.stringify(Object.fromEntries(Object.entries(value).sort()));
  assert.equal(stable(saved_changes),stable(expected));
 }
 for (const dt of ["Sales Order","Sales Invoice","Delivery Note"]) await assert_print_switches(dt);
 await flush();console.log("PASS: retry, stale responses, explicit selection, reset, item+warehouse, append/replace, integer/zero/blank, double click, submitted guards");
})().catch(e=>{console.error(e);process.exitCode=1;});
