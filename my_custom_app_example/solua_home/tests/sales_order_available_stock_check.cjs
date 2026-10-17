const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");

const source = fs.readFileSync(path.join(__dirname, "..", "public", "js", "sales_order_available_stock_v20261008.js"), "utf8");
assert.match(source, /flt\(doc\.actual_qty\)\s*-\s*flt\(doc\.reserved_qty\)/);
assert.match(source, /flt\(doc\.stock_qty\)\s*-\s*flt\(doc\.delivered_qty\)/);
assert.match(source, /remaining\s*<=\s*available\s*\?\s*"green"\s*:\s*"orange"/);
console.log("PASS: Sales Order indicator uses available stock");
