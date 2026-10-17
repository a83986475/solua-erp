const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");

const base = path.join(__dirname, "..");
const source = fs.readFileSync(path.join(base, "public/js/solua_home_global.js"), "utf8");
const hooks = fs.readFileSync(path.join(base, "hooks.py"), "utf8");

assert(source.includes('.form-links .document-link'));
assert(source.includes('anchor.href = `/app/${slug}'));
assert(source.includes('new MutationObserver'));
assert(source.includes('frm.dashboard?.data?.fieldnames?.[doctype]'));
assert(hooks.includes('/assets/solua_home/js/solua_home_global.js?v=related-links-new-tab-20261008b'));

console.log("related links new-tab check passed");
