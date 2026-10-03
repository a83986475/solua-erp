const assert = require('node:assert/strict');
const fs = require('node:fs');
const vm = require('node:vm');
const path = require('node:path');
const values = {metric:'orders',period:'本月',from_date:'',to_date:''};
const saved = new Map();
const frappe = {query_reports:{},session:{user:'test'},defaults:{get_user_default:()=> 'Test'}};
vm.runInNewContext(fs.readFileSync(path.join(__dirname,'../solua_wholesale/report/solua_business_totals/solua_business_totals.js'),'utf8'),{frappe,__:x=>x,localStorage:{getItem:key=>saved.get(key),setItem:(key,value)=>saved.set(key,value)}});
const report = {solua_initialized:true,get_filter_value:key=>values[key],page:{set_title(){}},refresh(){this.refreshes=(this.refreshes||0)+1;},set_filter_value(update){Object.assign(values,update);return Promise.resolve();}};
const settings=frappe.query_reports['Solua Business Totals'];
const filter=name=>settings.filters.find(row=>row.fieldname===name);
values.period='本周';filter('period').on_change(report);
values.metric='invoices';filter('metric').on_change(report);
assert.equal(values.period,'本周');
values.period='自定义';values.from_date='2026-09-01';values.to_date='2026-09-30';filter('period').on_change(report);
values.metric='paid';filter('metric').on_change(report);
assert.equal(values.period,'自定义');assert.equal(values.from_date,'2026-09-01');assert.equal(values.to_date,'2026-09-30');
assert.equal(JSON.parse(saved.get('solua-business-period:test:paid')).from_date,'2026-09-01');
assert.equal(report.refreshes,4);
console.log('PASS: switching metrics retains week/custom ranges and refreshes; new metric saves identical dates');

(async () => {
 const original = JSON.stringify({period:'本月',from_date:'',to_date:''});
 saved.set('solua-business-period:test:orders', original);
 report.page.main = {off(){return this;},on(){return this;}};
 report.set_filter_value = (field, value) => {
  Object.assign(values, typeof field === 'string' ? {[field]:value} : field);
  return Promise.resolve();
 };
 Object.assign(values,{metric:'orders',period:'本周',use_route_period:1});
 await settings.onload(report);
 assert.equal(values.period,'本周');
 assert.equal(values.use_route_period,0);
 assert.equal(saved.get('solua-business-period:test:orders'),original);
 await settings.onload(report);
 assert.equal(values.period,'本月');
 console.log('PASS: explicit homepage period overrides this visit without replacing independent preferences');
})().catch(error => {console.error(error);process.exitCode=1;});
