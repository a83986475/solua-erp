const fs = require('fs');
const assert = require('assert');

const root = __dirname + '/../';
const html = fs.readFileSync(root + 'www/index.html', 'utf8');
const js = fs.readFileSync(root + 'public/js/public_home.js', 'utf8');
const colors = fs.readFileSync(root + 'www/colors/index.html', 'utf8');

for (const marker of [
  '/assets/solua_home/css/public_home.css?v=20261017c',
  '/assets/solua_home/js/public_home.js?v=20261017a',
  'Os preços não estão publicados nesta fase.',
]) assert(html.includes(marker), `missing homepage marker: ${marker}`);
assert(js.includes('/api/method/solua_home.api.color_card.get_public_catalog'), 'missing catalog API route');
assert(js.includes("SH151077: 'BLACKOUT 100%'"), 'missing 100% light mapping');
assert(js.includes("SH151022: 'MUITO ESCURO 95%'"), 'missing 95% light mapping');
assert(html.includes('class="brand-logo"'), 'homepage must use the official logo');
assert(html.includes('/files/solua-logo.jpg'), 'homepage must load the official logo asset');
assert(html.includes('/files/SH15107700ad5d00ad5d.png'), 'homepage must use an ERP curtain template image');
assert(!html.includes('public_home_room.svg'), 'homepage should not use the room placeholder');
for (const marker of ['Cartela de cores', 'Pesquisar', 'Referência:', 'Código de cor:']) {
  assert(colors.includes(marker), `missing Portuguese colors-page marker: ${marker}`);
}
for (const forbidden of ['窗帘色卡', '查询', '款式货号', '色号']) {
  assert(!colors.includes(forbidden), `colors page still contains Chinese UI text: ${forbidden}`);
}

for (const forbidden of ['standard_rate', 'price_list_rate', 'valuation_rate', 'Item Price']) {
  assert(!js.includes(forbidden), `public homepage must not expose ${forbidden}`);
}

console.log('PASS: public homepage uses catalog API and contains no price fields');
