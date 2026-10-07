const assert = require("node:assert/strict");
const { calculate_pronto_pagamento } = require("../public/js/payment_entry_labels_v20261004.js");

// 折扣刚好整除：抹零不改变结果
assert.deepEqual(calculate_pronto_pagamento(154500), { discount: 4635, net: 149865 });
assert.deepEqual(calculate_pronto_pagamento(86000), { discount: 2580, net: 83420 });
assert.deepEqual(calculate_pronto_pagamento(1000), { discount: 30, net: 970 });

// 抹零 = 截断小数（不是四舍五入）：114840 × 97% = 111394.8 → 111394，零头 0.8 并入折扣
assert.deepEqual(calculate_pronto_pagamento(114840), { discount: 3446, net: 111394 });
assert.deepEqual(calculate_pronto_pagamento(101), { discount: 4, net: 97 });
// 毛额带小数时，实收截断、折扣补足差额，保证 实收 + 折扣 = 毛额
assert.deepEqual(calculate_pronto_pagamento(114840.5), { discount: 3445.5, net: 111395 });

for (const gross of [0, 9, 101, 999.99, 1000, 86000, 114840, 114840.5, 154500]) {
	const { discount, net } = calculate_pronto_pagamento(gross);
	assert.equal(Math.round((net + discount) * 100) / 100, gross, `实收 + 折扣 必须等于毛额 (${gross})`);
	assert.ok(Number.isInteger(net), `实收必须已抹零为整数 (${gross})`);
	assert.ok(net <= gross, `实收不能大于毛额 (${gross})`);
}

console.log("payment entry discount check passed");
