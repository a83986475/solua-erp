const fs = require('fs');
const assert = require('assert');

const root = __dirname + '/../';
const html = fs.readFileSync(root + 'www/index.html', 'utf8');
const js = fs.readFileSync(root + 'public/js/public_home.js', 'utf8');

for (const marker of [
  '/assets/solua_home/css/public_home.css?v=20261016a',
  '/assets/solua_home/js/public_home.js?v=20261016b',
  'sem preços nesta fase',
]) assert(html.includes(marker), `missing homepage marker: ${marker}`);
assert(js.includes('/api/method/solua_home.api.color_card.get_public_catalog'), 'missing catalog API route');

for (const forbidden of ['standard_rate', 'price_list_rate', 'valuation_rate', 'Item Price']) {
  assert(!js.includes(forbidden), `public homepage must not expose ${forbidden}`);
}

console.log('PASS: public homepage uses catalog API and contains no price fields');
