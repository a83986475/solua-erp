// Run: node my_custom_app_example/solua_home/tests/wholesale_forms_check.cjs
const assert = require("node:assert/strict");
const fs = require("node:fs");
const vm = require("node:vm");
const path = require("node:path");
// Check the real loading entrypoint as well as the form implementation.
const appRoot = path.resolve(__dirname, "..");
const hooksSource = fs.readFileSync(path.join(appRoot, "hooks.py"), "utf8");
const loaderPath = "public/js/wholesale_forms_additional_notes_loader_v17.js";
const salesInvoicePrintPath = "public/js/sales_invoice_print_options_v20261005.js";
for (const doctype of ["Sales Order", "Delivery Note", "Pick List"]) {
  const line = hooksSource.split("\n").find(line => line.trim().startsWith(`"${doctype}": [` ) && line.includes("public/js/"));
  assert.ok(line && line.includes(loaderPath), `${doctype}: loading entrypoint regressed; review loader changes before release`);
}
const salesInvoiceLine = hooksSource.split("\n").find(line => line.trim().startsWith('"Sales Invoice": ['));
assert.ok(salesInvoiceLine && salesInvoiceLine.includes(salesInvoicePrintPath), "Sales Invoice batch-print entrypoint regressed");
const loaderSource = fs.readFileSync(path.join(appRoot, loaderPath), "utf8");
assert.ok(loaderSource.includes("wholesale_forms_stock_entry_v20261006.js?v=stock-entry-tools-20261006a"), "Wholesale script cache version regressed");
const releaseFiles = fs.readFileSync(path.join(__dirname, "release_whitelist.txt"), "utf8");
assert.ok(releaseFiles.includes(`my_custom_app_example/solua_home/${loaderPath}`), "Active loader missing from release whitelist");
const handlers = {}, requests = [], dialogs = [];
const storage = new Map();
const defaultLists = new Map();
const datalists = new Map();
const localStorage = {getItem(key){return storage.has(key) ? storage.get(key) : null;},setItem(key,value){storage.set(key,String(value));}};
const input = () => ({events:{}, on(event, fn){this.events[event]=fn;return this;}, off(event){delete this.events[event];return this;}, focus(){}, setAttribute(key,value){this[key]=value;}, removeAttribute(key){delete this[key];}});
const document = {
  getElementById(id){return datalists.get(id) || null;},
  createElement(type){return {type,id:"",children:[],value:"",replaceChildren(){this.children=[];},appendChild(child){this.children.push(child);}};},
  body:{appendChild(node){datalists.set(node.id,node);}},
};
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
  hide(){this.hidden=true;}
  show(){}
}
const rows = new Map();
const frappe = {
  session:{user:"tester@example.com"},
  ui:{Dialog, form:{on(dt, value){handlers[dt]={...(handlers[dt] || {}),...value};}}},
  utils:{escape_html:String},
  call(options){
    if (options?.method === "solua_home.api.sales.get_customer_store_options") return Promise.resolve({message:[
      {name:"客户A-门店1",title:"客户A门店一",phone:"999"},
      {name:"客户A-门店2",title:"客户A门店二",phone:"998"},
    ]});
    return new Promise((resolve,reject)=>requests.push({resolve,reject}));
  },
  db:{
    get_list(doctype){return Promise.resolve(defaultLists.get(doctype) || []);},
    get_value(doctype, name){
      if (doctype === "Address" && String(name).includes("手工")) return Promise.resolve({message:{value:{phone:null}}});
      return Promise.resolve({message: doctype === "Driver" ? {full_name:"唯一司机",cell_number:"123"} : {value:{phone:"999"}}});
    },
  },
  model:{async set_value(dt,name,key,value){
    await Promise.resolve();
    const row=rows.get(name);row[key]=value;
    if(key==="item_code"){row.warehouse="NATIVE-DEFAULT";row.qty=99;row.rate=999;}
  }},
  show_alert(){},msgprint(){},
};
const browser = {open(){},localStorage};
const script_scope = {frappe, __:s=>s, Number, String, Promise, URLSearchParams, window:browser, document};
vm.runInNewContext(fs.readFileSync(path.join(__dirname,"../public/js/document_table_export_v20260930c.js"),"utf8"), script_scope);
const wholesaleSource = fs.readFileSync(path.join(__dirname,"../public/js/wholesale_forms_stock_entry_v20261006.js"),"utf8");
vm.runInNewContext(wholesaleSource, script_scope);
vm.runInNewContext(fs.readFileSync(path.join(__dirname,"../public/js/sales_invoice_print_options_v20261005.js"),"utf8"), script_scope);
const salesTools = browser.solua_home_sales_order_tools;
const flush = () => new Promise(resolve=>setImmediate(resolve));
function form(dt,status=0,purpose){
 const frm={doctype:dt,doc:{docstatus:status,company:"Solua Home, Lda",items:[],set_warehouse:"W1",from_warehouse:dt==="Stock Entry"?"W0":undefined,to_warehouse:dt==="Stock Entry"?"W2":undefined,purpose:purpose || (dt==="Stock Entry"?"Material Receipt":undefined)},fields_dict:{custom_store_name:{$input:input()}},buttons:[],dirty(){},
  set_value(key,value){this.doc[key]=value;return Promise.resolve(value);},
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
		{item_code:"blue",item_name:"Blue",description:"Blue desc",uom:"条",stock_uom:"条",rate:430,price_list_rate:430,warehouse:"W1",qty:3,custom_item_barcode:"BAR-BLUE",actual_qty:50,projected_qty:50,stock_qty:3},
	]}});
	await batchAdd;
	assert.deepEqual(salesOrder.doc.items.map(row=>row.qty),[2,3]);
	assert.equal(salesOrder.doc.items[1].actual_qty,50);
	assert.equal(salesOrder.doc.items[1].projected_qty,50);
	assert.equal(salesOrder.doc.items[1].stock_qty,3);
	// Stock Entry receipt tools are a separate extension, absent from older sales releases.
	// If its implementation exists, registration and every receipt assertion remain mandatory.
	if (wholesaleSource.includes("const is_stock_entry_form")) {
	assert.ok(handlers["Stock Entry"]?.refresh, "Stock Entry extension present but handler missing");
	const submittedStockEntry = form("Stock Entry",1);
	assert.equal(submittedStockEntry.buttons.length,0);
	assert.equal(form("Stock Entry",0,"Material Transfer").buttons.length,5);
	for (const purpose of ["Material Issue", "Material Transfer", "Material Consumption for Manufacture"]) {
		const outbound = form("Stock Entry",0,purpose);
		assert.equal(outbound.buttons.length,5);
		outbound.buttons[0].fn(); const d = dialogs.at(-1);
		assert.equal(d.values.warehouse,"W0");
		assert.equal(d.fields_dict.rate,undefined,"Outbound must use native valuation");
		await query(d,"OUT"); d.values.variant="red"; d.values.qty="3"; await d.action();
		assert.equal(outbound.doc.items[0].s_warehouse,"W0");
		assert.equal(outbound.doc.items[0].qty,3);
		assert.equal(outbound.doc.items[0].basic_rate,undefined);
	}
	const stockEntry = form("Stock Entry");
	assert.equal(stockEntry.buttons.length,5);
	stockEntry.buttons[0].fn();
	const stockDialog = dialogs.at(-1);
	assert.equal(stockDialog.label,"查询颜色");
	await query(stockDialog,"STOCK");
	stockDialog.values.variant="red";stockDialog.values.qty="2";stockDialog.values.rate=12;await stockDialog.action();
	assert.equal(stockEntry.doc.items.length,1);
	assert.equal(stockEntry.doc.items[0].t_warehouse,"W2");
	assert.equal(stockEntry.doc.items[0].basic_rate,12);
	stockEntry.buttons[2].fn();
	const stockBulk = dialogs.at(-1);
	assert.equal(stockBulk.fields_dict.results.df.fields.some((field) => field.fieldname === "rate"),true);
	requests.at(-1).resolve({message:{items:[]}});await flush();
	stockBulk.fields_dict.search_items.$input.events.click();
	requests.at(-1).resolve({message:{items:[{item_code:"bulk-red",item_name:"Bulk Red",warehouse:"W2"}]}});await flush();
	stockBulk.fields_dict.results.df.data[0].__checked=1;stockBulk.fields_dict.results.df.data[0].rate=9;
	const stockBulkAdd=stockBulk.action();
	requests.at(-1).resolve({message:{rows:[{item_code:"bulk-red",item_name:"Bulk Red",warehouse:"W2",qty:1,rate:9}]}});await stockBulkAdd;
	assert.equal(stockEntry.doc.items[1].t_warehouse,"W2");
	assert.equal(stockEntry.doc.items[1].basic_rate,9);
	} else {
		console.log("Stock Entry receipt extension not installed; sales and bulk quantity checks remain enabled");
	}
	const delivery = form("Delivery Note");
	delivery.doc.customer_address = "CHINA CASH AND CARRY-商店";
	handlers["Delivery Note"].refresh(delivery);
	assert.equal(delivery.doc.custom_store_name, "CHINA CASH AND CARRY-商店");
	defaultLists.set("Vehicle", [{name:"唯一车辆"}]);
	defaultLists.set("Driver", [{name:"唯一司机"}]);
	const defaultDelivery = form("Delivery Note");
	defaultDelivery.doc.shipping_address_name = "唯一地址";
	handlers["Delivery Note"].shipping_address_name(defaultDelivery);
	await flush();
	assert.equal(defaultDelivery.doc.vehicle_no, "唯一车辆");
	assert.equal(defaultDelivery.doc.driver, "唯一司机");
	assert.equal(defaultDelivery.doc.custom_store_phone, "999");
	defaultLists.set("Vehicle", [{name:"车辆1"},{name:"车辆2"}]);
	const manualDelivery = form("Delivery Note");
	manualDelivery.doc.vehicle_no = "手工车辆";
	await flush();
	assert.equal(manualDelivery.doc.vehicle_no, "手工车辆");
	delivery.doc.custom_store_name = "手工门店";
	delivery.doc.customer_address = "另一个地址";
	handlers["Delivery Note"].refresh(delivery);
	assert.equal(delivery.doc.custom_store_name, "手工门店");
	salesOrder.doc.customer_address = "RISING SUN TRADING SU, LDA-Preco Bom Center";
	handlers["Sales Order"].customer_address(salesOrder);
	await flush();
	assert.equal(salesOrder.doc.custom_store_name, "RISING SUN TRADING SU, LDA-Preco Bom Center");
	salesOrder.doc.customer = "客户A";
	handlers["Sales Order"].customer(salesOrder);
	await flush();
	assert.ok(salesOrder.fields_dict.custom_store_name.$input.list.startsWith("solua-store-options-"));
	assert.deepEqual(datalists.get(salesOrder.fields_dict.custom_store_name.$input.list).children.map((option) => option.value), ["客户A-门店1", "客户A-门店2"]);
	salesOrder.doc.custom_store_name = "客户A-门店1";
	handlers["Sales Order"].custom_store_name(salesOrder);
	await flush();
	assert.equal(salesOrder.doc.custom_store_phone, "999");
	assert.equal(salesOrder.doc.shipping_address_name, "客户A-门店1");
	assert.equal(salesOrder.doc.customer_address, "客户A-门店1");
	assert.equal(salesOrder.doc.custom_store_name, "客户A门店一");
	assert.equal(salesOrder.doc.custom_store_address, "客户A-门店1");
	salesOrder.doc.custom_store_name = "手工新门店";
	handlers["Sales Order"].custom_store_name(salesOrder);
	await flush();
	assert.equal(salesOrder.doc.custom_store_phone, "");
	assert.equal(salesOrder.doc.custom_store_address, "");
	assert.equal(salesOrder.doc.customer_address, "客户A-门店1");
	salesOrder.doc.custom_store_name = "客户A-门店2";
	salesOrder.doc.custom_store_phone = "人工电话";
	handlers["Sales Order"].custom_store_name(salesOrder);
	await flush();
	assert.equal(salesOrder.doc.custom_store_phone, "998");
	salesOrder.doc.custom_store_name = "手工门店";
	handlers["Sales Order"].custom_store_name(salesOrder);
	salesOrder.doc.shipping_address_name = "另一个门店";
	handlers["Sales Order"].shipping_address_name(salesOrder);
	await flush();
	assert.equal(salesOrder.doc.custom_store_name, "手工门店");
	const refreshStock = salesOrder.buttons.find((button) => button.label === "刷新库存").fn();
	requests.at(-1).resolve({message:{rows:[
		{item_code:"red",warehouse:"W1",actual_qty:10,projected_qty:10,stock_qty:2},
		{item_code:"blue",warehouse:"W1",actual_qty:50,projected_qty:50,stock_qty:3},
	]}});
	await refreshStock;
	assert.equal(salesOrder.doc.items[0].actual_qty,10);
	assert.equal(salesOrder.doc.items[0].projected_qty,10);
	salesOrder.buttons[2].fn();
	const bulkPicker = dialogs.at(-1);
	assert.equal(bulkPicker.fields_dict.template.df.get_query().filters.has_variants,1);
	requests.at(-1).resolve({message:{items:[
		{item_code:"rod-red",item_name:"Rod Red",available_qty:9,warehouse:"W1"},
		{item_code:"rod-blue",item_name:"Rod Blue",available_qty:9,warehouse:"W1"},
	]}});
	await flush();
 assert.equal(bulkPicker.get_value("default_qty"),1);
 assert.deepEqual(bulkPicker.fields_dict.results.df.data.map(row=>row.qty),[1,1]);
 bulkPicker.values.default_qty=4;
 bulkPicker.fields_dict.default_qty.$input.events["change.solua"]();
 assert.deepEqual(bulkPicker.fields_dict.results.df.data.map(row=>row.qty),[4,4]);
 bulkPicker.fields_dict.results.df.data.forEach(row=>{row.__checked=1;});
 const bulkAdd=bulkPicker.action();
 requests.at(-1).resolve({message:{rows:[
  {item_code:"rod-red",item_name:"Rod Red",warehouse:"W1",qty:4},
  {item_code:"rod-blue",item_name:"Rod Blue",warehouse:"W1",qty:4},
 ]}});
 await bulkAdd;
 assert.equal(bulkPicker.hidden,undefined);
 assert.equal(bulkPicker.get_value("warehouse"),"W1");
 assert.equal(bulkPicker.get_value("default_qty"),4);
 assert.equal(bulkPicker.fields_dict.results.df.data.length,0);
	const quantityUpdateButton = salesOrder.buttons.find((button) => button.label === "批量修改数量");
	assert.ok(quantityUpdateButton);
	quantityUpdateButton.fn();
	const quantityDialog = dialogs.at(-1);
	assert.deepEqual(quantityDialog.fields_dict.items.df.data.map((row) => row.current_qty), [2,3,4,4]);
	quantityDialog.fields_dict.select_all.$input.events.click();
	assert.deepEqual(quantityDialog.fields_dict.items.grid.get_selected_children().map((row) => row.item_code), ["red", "blue", "rod-red", "rod-blue"]);
	quantityDialog.values.new_qty = 8;
	const quantityApply = quantityDialog.action();
	await quantityApply;
	assert.equal(salesOrder.doc.items.find((row) => row.item_code === "red").qty, 8);
	assert.equal(salesOrder.doc.items.find((row) => row.item_code === "blue").qty, 8);
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
 submitted.fields_dict={custom_print_item_name:{},custom_print_sku:{},custom_print_color_code:{},custom_print_cor:{},custom_print_description:{},custom_print_color_images:{},custom_print_color_qr:{},...(dt !== "Delivery Note" ? {custom_print_merge_order_code:{}} : {}),...(dt === "Delivery Note" ? {custom_print_ordered_before:{},custom_print_current_remaining:{},custom_print_quantity:{},custom_print_traceability:{}} : {}),...(dt !== "Sales Invoice" ? {custom_print_additional_notes:{}} : {})};
  let saved_changes;submitted.set_value=async changes=>{saved_changes=changes;};submitted.is_dirty=()=>true;
  let save_mode;submitted.save=async mode=>{save_mode=mode;};
  handlers[dt].refresh(submitted);
  assert.equal(submitted.buttons.length,1);
  submitted.buttons[0].fn();const print_dialog=dialogs.at(-1);print_dialog.hide=()=>{};
 const selected={show_item_name:0,show_sku:1,show_color:0,merge_order_code:1,show_description:0,show_ordered_before:0,show_current_remaining:0,show_quantity:0,show_traceability:0,show_images:1,show_qr:0,show_additional_notes:0};
 const values=Object.fromEntries(Object.keys(print_dialog.values).map(key=>[key,selected[key]]));
 const print_action=print_dialog.action(values);
 if(dt !== "Sales Invoice") { await flush(); requests.at(-1).resolve({message:"TEST FORMAT"}); }
 await print_action;await flush();
  assert.equal(save_mode,"Update");
 const expected={custom_print_item_name:0,custom_print_sku:1,custom_print_color_code:0,custom_print_cor:0,custom_print_description:0,custom_print_color_images:1,custom_print_color_qr:0};
 if(dt === "Pick List") Object.keys(expected).forEach(key=>{if(key !== "custom_print_additional_notes") delete expected[key];});
 if(dt === "Sales Order" || dt === "Sales Invoice") expected.custom_print_merge_order_code=1;
 if(dt !== "Sales Invoice") expected.custom_print_additional_notes=0;
  if(dt === "Delivery Note") { expected.custom_print_ordered_before=0; expected.custom_print_current_remaining=0; expected.custom_print_quantity=0; expected.custom_print_traceability=0; }
  const stable=value=>JSON.stringify(Object.fromEntries(Object.entries(value).sort()));
  assert.equal(stable(saved_changes),stable(expected));
  const reopened=form(dt,1);reopened.is_new=()=>false;reopened.fields_dict=submitted.fields_dict;
  handlers[dt].refresh(reopened);reopened.buttons[0].fn();const remembered=dialogs.at(-1);
  assert.deepEqual(Object.fromEntries(Object.keys(values).map(key=>[key,remembered.values[key]])),values);
 }
 for (const dt of ["Sales Order","Sales Invoice","Delivery Note","Pick List"]) await assert_print_switches(dt);
 assert.equal(storage.size,4);
 await flush();console.log("PASS: retry, stale responses, explicit selection, reset, item+warehouse, append/replace, integer/zero/blank, double click, submitted guards");
})().catch(e=>{console.error(e);process.exitCode=1;});
