// Exercise the actual form/list extension without changing an ERP document.
const assert = require('node:assert/strict'), fs = require('node:fs'), vm = require('node:vm'), path = require('node:path');
const forms = {}, calls = [], buttons = [], removed = [], indicators = [], sections = [];
let prompt, previousOnload = 0, dashboardShown = 0;
const frappe = {utils:{escape_html:value=>String(value).replaceAll('<','&lt;').replaceAll('>','&gt;')},
  listview_settings:{'Sales Order':{onload(){previousOnload++;}}},
  provide(){}, model:{can_submit:()=>true}, ui:{form:{on:(dt,events)=>forms[dt]=events}},
  msgprint(){}, show_alert(){}, prompt:(fields,done,title)=>prompt={fields,done,title},
  call:async args=>{calls.push(args);const names=JSON.parse(args.args?.names||'[]');return {message:Object.fromEntries(names.map(name=>[name,{status_label:'已结束',delivery_label:'已交货 · 有退货 · 剩余不再交付',billing_label:'已开票',payment_label:'未收齐',quantities:[{uom:'条',delivered:10,returned:2,net:8,remaining:2}],ended:true,end_reason:'<历史未记录>'}]))};}};
const context={frappe,solua_home:{},__:value=>value,$:()=>({text:()=> 'Close'})};
vm.runInNewContext(fs.readFileSync(path.join(__dirname,'../public/js/order_status_v20261009d.js'),'utf8'),context);
const settings=frappe.listview_settings['Sales Order'];
assert.equal(settings.get_indicator({status:'Closed',docstatus:1})[0],'已结束');
assert.equal(settings.get_indicator({status:'Closed',docstatus:1})[2],'status,=,Closed');
const frm={doc:{name:'SO',modified:'1',docstatus:1,status:'Closed'},page:{set_indicator:(...args)=>indicators.push(args)},
 toggle_display(){}, remove_custom_button:(...args)=>removed.push(args),add_custom_button:(...args)=>buttons.push(args),
 is_new:()=>false,reload_doc(){},dashboard:{show:()=>dashboardShown++,add_section:html=>{sections.push(html);return {closest:()=>({remove(){}})};}}};
forms['Sales Order'].refresh(frm);
setImmediate(async()=>{
 assert.equal(dashboardShown,1);assert.equal(indicators[0][0],'已结束');assert.equal(buttons.length,0);
 assert(sections[0].includes('净交付 8')&&sections[0].includes('不再交付 2'));
 assert(sections[0].includes('&lt;历史未记录&gt;')&&!sections[0].includes('<历史未记录>'));
 frm.doc.status='To Deliver';forms['Sales Order'].refresh(frm);
 assert(buttons[0][0].includes('结束订单'));buttons[0][1]();
 assert.equal(prompt.fields[0].reqd,1);assert(prompt.title.includes('不再交付'));
 await prompt.done({reason:'客户取消剩余'});
 assert(calls.at(-1).method.endsWith('close_or_unclose_sales_orders'));
 assert.equal(calls.at(-1).args.reason,'客户取消剩余');assert.equal(calls.at(-1).args.status,'Closed');
 const list={setup_columns(){this.columns=[{df:{fieldname:'grand_total'}},{df:{fieldname:'per_billed'}},{df:{fieldname:'per_delivered'}}];},render_header(){},after_render(){},refresh(){},get_checked_items:()=>['SO'],page:{actions:{find:()=>({filter:()=>({remove(){}})})},add_action_item(){}}};
 settings.onload(list);assert.equal(previousOnload,1);assert.deepEqual(Array.from(list.columns, c=>c.df.fieldname),['grand_total']);
 list.start=0;list.data=Array.from({length:51},(_,i)=>({name:'SO-'+i}));list.$result={find:()=>({remove(){},each(){}})};
 const start=calls.length;list.after_render();await new Promise(resolve=>setImmediate(resolve));
 assert.deepEqual(calls.slice(start).map(c=>JSON.parse(c.args.names).length),[50,1]);
 const cached=calls.length;list.after_render();await new Promise(resolve=>setImmediate(resolve));
 assert.equal(calls.length,cached);
 list.data.push({name:'SO-51'},{name:'SO-52'});const added=calls.length;list.after_render();await new Promise(resolve=>setImmediate(resolve));
 assert.deepEqual(calls.slice(added).map(c=>JSON.parse(c.args.names).length),[2]);
 const reset=calls.length;list.refresh();list.after_render();await new Promise(resolve=>setImmediate(resolve));
 assert.deepEqual(calls.slice(reset).map(c=>JSON.parse(c.args.names).length),[50,3]);
 console.log('PASS: original list actions preserved, lifecycle badge uses raw filters, ended form summary, escaped reason and required closure dialog');
});
