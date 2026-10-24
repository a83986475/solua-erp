const fs = require('fs');
const assert = require('assert');

const root = __dirname + '/../';
const html = fs.readFileSync(root + 'www/fuel_cost/index.html', 'utf8');
const py = fs.readFileSync(root + 'www/fuel_cost/index.py', 'utf8');

for (const marker of [
  'data-input="distance"',
  'data-input="consumption"',
  'data-input="fuelPrice"',
  'data-input="roundTrip"',
  'data-log-input="odometer"',
  'data-log-input="liters"',
  'data-log-input="fullTank"',
  'get_fuel_records',
  'save_fuel_record',
  '服务器，并随账号同步',
  'getSegments',
  '/api/method/solua_home.api.fuel_cost.get_latest_fuel_prices',
  '使用实测值',
  'data-output="cost"',
  '燃油费 = 实际公里数 ÷ 100 × 百公里油耗 × 每升油价',
  '总成本 = 燃油费 + 过路费 + 人工 + 维修折旧 + 固定费用',
  'const cost = fuel + toll + driver + maintenanceCost + fixed;',
  'const quote = cost * (1 + margin);',
]) assert(html.includes(marker), `missing fuel-cost marker: ${marker}`);
assert(py.includes('context.no_cache = 1'), 'fuel-cost page should avoid stale calculations');
assert(!html.includes('valuation_rate'), 'public tool must not expose ERP valuation data');
console.log('PASS: fuel-cost page contains the calculator contract and public-safe fields');
