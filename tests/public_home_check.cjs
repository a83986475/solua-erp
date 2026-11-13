const assert = require("node:assert/strict");
const { readFileSync } = require("node:fs");
const { join } = require("node:path");

const read = (path) => readFileSync(join(__dirname, "..", path), "utf8");
const home = read("www/index.html");
const colors = read("www/colors/index.html");
const js = read("public/js/storefront.js");

for (const page of [home, colors]) {
  assert.match(page, /<html lang="pt-MZ">/);
  assert.match(page, /href="\/assets\/solua_home\/css\/storefront\.css"/);
  assert.match(page, /src="\/assets\/solua_home\/js\/storefront\.js"/);
  assert.doesNotMatch(page, /(?:href|src)="[^"]*[?&](?:v|version)=/i);
}
assert.match(home, /rel="canonical" href="https:\/\/home\.solua\.one\/"/);
assert.match(colors, /action="\/colors" method="get"/);
assert.match(colors, /id="q" name="q"/);
assert.match(js, /\/api\/method\/solua_home\.api\.color_card\./);
assert.match(js, /request\("get_public_catalog"/);
assert.match(js, /request\("get_public_color_card"/);
assert.doesNotMatch(js, /standard_rate|price_list_rate|valuation_rate|Item Price/);
console.log("PASS: clean storefront URLs, public colour-card endpoints, and no price fields");
