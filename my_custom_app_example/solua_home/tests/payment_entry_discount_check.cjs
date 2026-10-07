const assert = require("node:assert/strict");
const { calculate_pronto_pagamento } = require("../public/js/payment_entry_labels.js");

assert.deepEqual(calculate_pronto_pagamento(154500), { discount: 4635, net: 149865 });
assert.deepEqual(calculate_pronto_pagamento(86000), { discount: 2580, net: 83420 });
console.log("payment entry discount check passed");
