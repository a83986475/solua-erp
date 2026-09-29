import fs from 'node:fs/promises';
import { FileBlob, SpreadsheetFile, Workbook } from '@oai/artifact-tool';

const outDir = 'C:/Users/Yang/solua-home/sites/erpnext/outputs/01a09c05-ffba-7b72-b03e-a93152caaa99';
const outputPath = `${outDir}/莫桑比克窗帘_ERPNext导入草稿.xlsx`;
const font = 'Arial';

const paths = {
  order: 'D:/WeChat/xwechat_files/chenyangyang_7cef/msg/file/2026-09/莫桑比克窗帘下单(1)(1).xlsx',
  packing: 'C:/Users/Yang/Desktop/Solua/LG2026.xlsx',
  quote: 'D:/WeChat/xwechat_files/chenyangyang_7cef/msg/file/2026-09/(已瘦身)SOLUA HOME窗帘报价单（HOME STORE版）(1).xlsx',
  quoteCalc: 'C:/Users/Yang/Desktop/Solua/SOLUA HOME窗帘报价计算单(2).xlsx',
  color: 'D:/WeChat/xwechat_files/chenyangyang_7cef/msg/file/2026-09/莫桑比克色卡文档.xlsx',
};

const clean = (v) => String(v ?? '').replace(/\r?\n/g, ' / ').replace(/\s+/g, ' ').trim();
const raw = (v) => (v === null || v === undefined ? '' : String(v));
const num = (v) => (typeof v === 'number' ? v : (String(v ?? '').match(/-?\d+(?:\.\d+)?/) ? Number(String(v).match(/-?\d+(?:\.\d+)?/)[0]) : null));
const colLetter = (n) => { let s = ''; while (n > 0) { const r = (n - 1) % 26; s = String.fromCharCode(65 + r) + s; n = Math.floor((n - 1) / 26); } return s; };
const splitSku = (v) => { const parts = String(v ?? '').split(/\r?\n/).map(s => s.trim()).filter(Boolean); return { spu: parts[0] ?? '', itemCode: parts[1] ?? parts[0] ?? '', display: clean(v) }; };
const baseName = (v) => String(v ?? '').split(/\r?\n/)[0].trim();
const retailHigh = (v) => { if (typeof v === 'number') return v; const m = String(v ?? '').match(/\d+(?:\.\d+)?/g) ?? []; return m.length ? Number(m[m.length - 1]) : null; };

const load = async (path) => SpreadsheetFile.importXlsx(await FileBlob.load(path));
const orderWb = await load(paths.order);
const packingWb = await load(paths.packing);
const quoteWb = await load(paths.quote);
const quoteCalcWb = await load(paths.quoteCalc);
const colorWb = await load(paths.color);
const values = (wb, sheetName) => wb.worksheets.getItem(sheetName).getUsedRange()?.values ?? [];
const orderRows = values(orderWb, 'Sheet1');
const packingRows = values(packingWb, 'Sheet1');
const quoteRows = values(quoteWb, 'Sheet1');
const quoteCalcRows = values(quoteCalcWb, 'Sheet1');
const colorRows = values(colorWb, 'Sheet1');

const orderProducts = orderRows.map((r, i) => ({ row: r, absRow: i + 1 })).filter(x => x.absRow >= 4 && x.row[16]);
const packingByCode = new Map(packingRows.map((r, i) => ({ row: r, absRow: i + 1 })).filter(x => x.absRow >= 4 && x.row[1]).map(x => [splitSku(x.row[1]).itemCode, x]));
const quoteByCode = new Map(quoteRows.map((r, i) => ({ row: r, absRow: i + 1 })).filter(x => x.absRow >= 3 && x.row[3]).map(x => [splitSku(x.row[3]).itemCode, x]));
const quoteCalcByCode = new Map(quoteCalcRows.map((r, i) => ({ row: r, absRow: i + 1 })).filter(x => x.absRow >= 2 && x.row[4]).map(x => [splitSku(x.row[4]).itemCode, x]));

const products = orderProducts.map(({ row: o, absRow: orderRow }) => {
  const sku = splitSku(o[16]);
  const p = packingByCode.get(sku.itemCode);
  const q = quoteByCode.get(sku.itemCode);
  const qc = quoteCalcByCode.get(sku.itemCode);
  if (!p || !q || !qc) throw new Error(`Unmatched product ${sku.itemCode}`);
  const qSku = splitSku(q.row[3]);
  return {
    itemCode: sku.itemCode,
    spu: sku.spu,
    orderSku: sku.display,
    packingSku: splitSku(p.row[1]).display,
    quoteSku: qSku.display,
    orderRow,
    packingRow: p.absRow,
    quoteRow: q.absRow,
    quoteCalcRow: qc.absRow,
    orderName: clean(o[2]),
    quoteName: clean(q.row[2]),
    name: baseName(q.row[2]) || baseName(o[2]),
    description: clean(q.row[2]),
    orderPieces: num(o[6]),
    estimatedCartons: num(o[9]),
    orderedQty: num(o[6]) * num(o[9]),
    sourceTotalQty: num(o[13]),
    actualQty: num(p.row[10]),
    cartons: num(p.row[5]),
    packingColor: clean(p.row[4]),
    orderColorInstruction: clean(o[7]),
    orderColor: clean(o[12]),
    specification: clean(p.row[3] || o[11]),
    barcode: raw(p.row[17] || q.row[4] || o[17]).trim(),
    cost: num(qc.row[13]),
    wholesale: num(q.row[5]),
    homeStore: num(q.row[6]),
    retailRaw: raw(q.row[9]).trim(),
    retail: retailHigh(q.row[9]),
    image: `${outDir}/报价单图片/${sku.itemCode}.png`,
  };
});

const productByCode = new Map(products.map(p => [p.itemCode, p]));
const colorGroups = [];
const colorNumber = (v) => { const m = String(v ?? '').match(/\d+/); return m ? m[0].padStart(2, '0') : ''; };
const variantCodeFor = (p, c) => `${p.itemCode}-${colorNumber(c.colorCode)}`;
let currentGroup = null;
for (let i = 1; i < colorRows.length; i++) {
  const r = colorRows[i] ?? [];
  if (r[1]) currentGroup = splitSku(r[1]).itemCode;
  if (!currentGroup || !r[4]) continue;
  colorGroups.push({ itemCode: currentGroup, row: i + 1, colorCode: clean(r[4]), orderQty: num(r[5]), explicit: /^\d+号/.test(clean(r[4])), source: `莫桑比克色卡文档.xlsx / Sheet1 / 行${i + 1}` });
}
const explicitColors = colorGroups.filter(x => x.explicit && productByCode.has(x.itemCode));
const colorCoverage = new Map();
for (const c of colorGroups) { if (!colorCoverage.has(c.itemCode)) colorCoverage.set(c.itemCode, []); colorCoverage.get(c.itemCode).push(c); }
const variantProducts = products.filter(p => (colorCoverage.get(p.itemCode) ?? []).some(c => c.explicit));
const variantProductCodes = new Set(variantProducts.map(p => p.itemCode));

const formulaErrorSource = 'LG2026 部分公式缓存为 Excel 名称未解析错误，已排除出最终计算';
const nameConflict = (p) => p.orderName !== p.quoteName;

const wb = Workbook.create();
const importSheet = wb.worksheets.add('导入数据');
const mappingSheet = wb.worksheets.add('来源映射');
const pendingSheet = wb.worksheets.add('待确认项');
const summarySheet = wb.worksheets.add('读取摘要');
for (const s of [importSheet, mappingSheet, pendingSheet, summarySheet]) { s.showGridLines = false; s.tabColor = '#1F4E78'; }

function title(sheet, endCol, text) {
  const r = sheet.getRange(`A1:${endCol}1`); r.merge(); r.values = [[text]]; r.format = { font: { name: font, size: 14, bold: true, color: '#1F2937' }, verticalAlignment: 'center' }; r.format.rowHeight = 26;
}
function note(sheet, endCol, text) {
  const r = sheet.getRange(`A2:${endCol}2`); r.merge(); r.values = [[text]]; r.format = { font: { name: font, size: 9, italic: true, color: '#4B5563' }, wrapText: false, verticalAlignment: 'center' }; r.format.rowHeight = 20;
}
function headers(sheet, row, endCol) {
  const r = sheet.getRange(`A${row}:${endCol}${row}`); r.format = { fill: '#1F4E78', font: { name: font, size: 10, bold: true, color: '#FFFFFF' }, wrapText: true, verticalAlignment: 'center', horizontalAlignment: 'center', borders: { preset: 'all', style: 'thin', color: '#D9E2F3' } }; r.format.rowHeight = 30;
}
function body(sheet, start, end, endCol) {
  if (end < start) return;
  const r = sheet.getRange(`A${start}:${endCol}${end}`); r.format = { font: { name: font, size: 10, color: '#1F2937' }, verticalAlignment: 'center', wrapText: false, borders: { insideHorizontal: { style: 'thin', color: '#E5E7EB' }, bottom: { style: 'thin', color: '#D1D5DB' } } }; r.format.rowHeight = 24;
}
function section(sheet, row, endCol, text) {
  const r = sheet.getRange(`A${row}:${endCol}${row}`); r.merge(); r.values = [[text]]; r.format = { fill: '#D9EAF7', font: { name: font, size: 10, bold: true, color: '#1F2937' }, verticalAlignment: 'center' }; r.format.rowHeight = 22;
}

title(importSheet, 'S', '莫桑比克窗帘 ERPNext 导入草稿');
note(importSheet, 'S', '仅为本地草稿。Item 模板、颜色 Variant、Item Price 分区列出；空字段表示源资料未唯一确定，不代表已导入。');
section(importSheet, 4, 'S', 'Item 字段（色卡明确款保留模板；其余款按混色普通 Item 直接导入）');
const itemHeaders = ['记录类型','ERP Item Code','Item Name','Description','Internal SPU','Item Group','Stock UOM','Has Variants','Variant Attribute','Barcode','Specification','Source Color / Packaging','Ordered Qty (条)','Actual Packed Qty (条)','Qty Difference (条)','Cartons','Image','Status','Source Reference'];
importSheet.getRange('A5:S5').values = [itemHeaders]; headers(importSheet, 5, 'S');
const itemStart = 6;
const itemValues = products.map(p => { const hasVariants = variantProductCodes.has(p.itemCode); return [hasVariants ? 'Item Template' : 'Item', p.itemCode, p.name, p.description, p.spu, '窗帘', '条', hasVariants ? 1 : 0, hasVariants ? 'Cor' : '', p.barcode, p.specification, p.packingColor, p.orderedQty, p.actualQty, null, p.cartons, p.image, `${hasVariants ? '可直接导入模板；颜色级库存已按件数×预估装箱数分配' : '可直接导入普通 Item；按混色销售，不区分颜色'}；描述采用对外报价单；图片已从 HOME STORE 报价单导出`, `订货表/Sheet1/${p.orderRow}; 装箱表/Sheet1/${p.packingRow}; 对外报价单/Sheet1/${p.quoteRow}`]; });
importSheet.getRange(`A${itemStart}:S${itemStart + itemValues.length - 1}`).values = itemValues;
importSheet.getRange(`O${itemStart}`).formulas = [['=N6-M6']]; importSheet.getRange(`O${itemStart}:O${itemStart + itemValues.length - 1}`).fillDown(); body(importSheet, itemStart, itemStart + itemValues.length - 1, 'S');
section(importSheet, 20, 'M', 'Variant 字段（仅色卡明确款；未生成任何自动色号或自动后缀）');
const variantHeaders = ['记录类型','Variant Item Code','Variant Of','Variant Item Name','Cor 色号','颜色','Barcode','Order Qty (条)','Actual Packed Qty (条)','UOM','Direct Import','Status','Source Reference'];
importSheet.getRange('A21:M21').values = [variantHeaders]; headers(importSheet, 21, 'M');
const variantRows = [];
const variantOrderTotals = new Map();
for (const p of variantProducts) {
  const colors = (colorCoverage.get(p.itemCode) ?? []).filter(c => c.explicit);
  variantOrderTotals.set(p.itemCode, colors.reduce((sum, c) => sum + (c.orderQty ?? 0), 0));
}
for (const p of variantProducts) {
  const colors = colorCoverage.get(p.itemCode) ?? [];
  const explicit = colors.filter(c => c.explicit);
  const packSize = p.actualQty / variantOrderTotals.get(p.itemCode);
  for (const c of explicit) {
    const cor = colorNumber(c.colorCode);
    variantRows.push(['Variant', variantCodeFor(p, c), p.itemCode, `${p.name} / ${cor}`, cor, cor, '', c.orderQty, c.orderQty * packSize, '条', '已按模板生成变体', '数量已按件数×预估装箱数计算；模板条码共用；变体 Barcode 留空', c.source]);
  }
}
const variantStart = 22;
importSheet.getRange(`A${variantStart}:M${variantStart + variantRows.length - 1}`).values = variantRows;
body(importSheet, variantStart, variantStart + variantRows.length - 1, 'M');
const priceSectionRow = variantStart + variantRows.length + 3;
section(importSheet, priceSectionRow, 'K', 'Item Price 字段（采用对外报价单 HOME STORE 价；同一款式不同颜色共用同一价格）');
const priceHeaderRow = priceSectionRow + 1;
const priceHeaders = ['记录类型','Item/Variant Item Code','Template Item Code','Price List','Price List Rate','Currency','UOM','Is Buying','Is Selling','Source Reference','Status'];
importSheet.getRange(`A${priceHeaderRow}:K${priceHeaderRow}`).values = [priceHeaders]; headers(importSheet, priceHeaderRow, 'K');
const priceRows = [];
for (const p of products) {
  const direct = !variantProductCodes.has(p.itemCode);
  const targets = direct ? [{ target: p.itemCode, template: '' }] : (colorCoverage.get(p.itemCode) ?? []).filter(c => c.explicit).map(c => ({ target: variantCodeFor(p, c), template: p.itemCode }));
  for (const { target, template } of targets) {
    const status = direct ? '可直接导入' : '按同款价格复制到各颜色变体';
    priceRows.push(['Item Price', target, template, 'Standard Buying', p.cost, 'MZN', '条', 1, 0, `报价计算单/Sheet1/${p.quoteCalcRow} 成本/MT`, status]);
    priceRows.push(['Item Price', target, template, 'Wholesale Selling', p.wholesale, 'MZN', '条', 0, 1, `对外报价单/Sheet1/${p.quoteRow} 批发价`, status]);
    priceRows.push(['Item Price', target, template, 'Standard Selling', p.homeStore, 'MZN', '条', 0, 1, `对外报价单/Sheet1/${p.quoteRow} HOME STORE价；建议零售价原文 ${p.retailRaw}`, status]);
  }
}
const priceStart = priceHeaderRow + 1;
importSheet.getRange(`A${priceStart}:K${priceStart + priceRows.length - 1}`).values = priceRows;
body(importSheet, priceStart, priceStart + priceRows.length - 1, 'K');
importSheet.getRange(`I${itemStart}:I${itemStart + itemValues.length - 1}`).format.numberFormat = '@';
importSheet.getRange(`J${itemStart}:J${itemStart + itemValues.length - 1}`).format.numberFormat = '0';
importSheet.getRange(`M${itemStart}:P${itemStart + itemValues.length - 1}`).format.numberFormat = '#,##0';
importSheet.getRange(`E${priceStart}:E${priceStart + priceRows.length - 1}`).format.numberFormat = '#,##0.00';
importSheet.getRange(`B${itemStart}:B${itemStart + itemValues.length - 1}`).format.numberFormat = '@';
importSheet.freezePanes.freezeRows(5);
for (const [range, width] of [['A:A',15],['B:B',18],['C:D',24],['E:E',14],['F:F',12],['G:I',14],['J:J',18],['K:K',15],['L:L',24],['M:O',15],['P:P',10],['Q:Q',12],['R:R',28],['S:S',42]]) importSheet.getRange(range).format.columnWidth = width;

title(mappingSheet, 'Z', '来源映射与差异');
note(mappingSheet, 'Z', '匹配优先使用货号/条码，并用名称与规格做交叉核对；行号为源工作表实际行号。');
section(mappingSheet, 4, 'Z', '产品级映射');
const mapHeaders = ['匹配键','内部SPU','ERP Item Code','条码','订货货号','订货工作表','订货行','订货数量(条)','订货颜色要求','装箱货号','装箱工作表','装箱行','实际装箱数量(条)','数量差异(条)','箱数','装箱颜色','报价货号','报价工作表','报价行','成本价','批发价','建议零售价原文','HOME STORE价','规格','描述核对','匹配状态','6.8件数','预估装箱数','源表总条数','数量核对'];
mappingSheet.getRange('A5:AD5').values = [mapHeaders]; headers(mappingSheet, 5, 'AD');
const mapStart = 6;
const mapValues = products.map(p => [p.itemCode, p.spu, p.itemCode, p.barcode, p.orderSku, 'Sheet1', p.orderRow, null, p.orderColorInstruction, p.packingSku, 'Sheet1', p.packingRow, p.actualQty, null, p.cartons, p.packingColor, p.quoteSku, 'Sheet1', p.quoteRow, p.cost, p.wholesale, p.retailRaw, p.homeStore, p.specification, p.orderName === p.quoteName ? '一致' : `以对外报价单为准；订货表：${p.orderName}；报价单：${p.quoteName}`, '唯一匹配', p.orderPieces, p.estimatedCartons, p.sourceTotalQty, p.orderedQty === p.sourceTotalQty ? '一致' : '待核对']);
mappingSheet.getRange(`A${mapStart}:AD${mapStart + mapValues.length - 1}`).values = mapValues;
mappingSheet.getRange(`H${mapStart}`).formulas = [['=AA6*AB6']]; mappingSheet.getRange(`H${mapStart}:H${mapStart + mapValues.length - 1}`).fillDown();
mappingSheet.getRange(`N${mapStart}`).formulas = [['=M6-H6']]; mappingSheet.getRange(`N${mapStart}:N${mapStart + mapValues.length - 1}`).fillDown(); body(mappingSheet, mapStart, mapStart + mapValues.length - 1, 'AD');
const colorSectionRow = mapStart + mapValues.length + 3;
section(mappingSheet, colorSectionRow, 'J', '色卡文档映射');
const colorHeaderRow = colorSectionRow + 1;
const colorHeaders = ['ERP Item Code','色卡货号','色卡工作表','色卡行','色号原文','色卡订货数量(条)','颜色名','匹配到产品','备注'];
mappingSheet.getRange(`A${colorHeaderRow}:I${colorHeaderRow}`).values = [colorHeaders]; headers(mappingSheet, colorHeaderRow, 'I');
const colorMapRows = colorGroups.map(c => [c.itemCode, productByCode.get(c.itemCode)?.orderSku ?? '', 'Sheet1', c.row, c.colorCode, c.orderQty, '', productByCode.has(c.itemCode) ? '是' : '否', c.explicit ? '固定色号来自文档' : '文档未给出具体色号']);
const colorMapStart = colorHeaderRow + 1;
if (colorMapRows.length) { mappingSheet.getRange(`A${colorMapStart}:I${colorMapStart + colorMapRows.length - 1}`).values = colorMapRows; body(mappingSheet, colorMapStart, colorMapStart + colorMapRows.length - 1, 'I'); }
mappingSheet.getRange(`H${mapStart}:N${mapStart + mapValues.length - 1}`).format.numberFormat = '#,##0';
mappingSheet.getRange(`D${mapStart}:D${mapStart + mapValues.length - 1}`).format.numberFormat = '0';
mappingSheet.getRange(`T${mapStart}:W${mapStart + mapValues.length - 1}`).format.numberFormat = '#,##0.00';
mappingSheet.getRange(`M${mapStart}:N${mapStart + mapValues.length - 1}`).format.numberFormat = '#,##0';
mappingSheet.getRange(`AA${mapStart}:AC${mapStart + mapValues.length - 1}`).format.numberFormat = '#,##0';
mappingSheet.freezePanes.freezeRows(5);
for (const [range, width] of [['A:A',14],['B:C',14],['D:D',18],['E:E',20],['F:F',12],['G:G',8],['H:H',14],['I:I',28],['J:J',18],['K:K',12],['L:L',8],['M:N',15],['O:O',8],['P:P',12],['Q:Q',18],['R:R',12],['S:S',8],['T:W',14],['X:X',15],['Y:Y',34],['Z:Z',14],['AA:AD',14]]) mappingSheet.getRange(range).format.columnWidth = width;

title(pendingSheet, 'H', '待确认项');
note(pendingSheet, 'H', '待确认项不会阻止草稿生成；完成补充后再形成可直接导入的 Variant / Item Price 文件。');
const pendingHeaders = ['编号','类别','影响范围','问题','当前处理','来源依据','需要确认/补充','状态'];
pendingSheet.getRange('A4:H4').values = [pendingHeaders]; headers(pendingSheet, 4, 'H');
const pendingRows = [];
pendingRows.push([1,'图片','全部12款','HOME STORE 报价单包含产品图片，已从 Excel 内嵌对象中提取每款主图','已导出每款主图并写入导入数据 Image 栏；每款的其他细节图也已保存在图片文件夹','对外报价单 Sheet1 / 产品图片对象','如需更换主图或补充颜色细节图，再提供新的图片','已完成']);
pendingRows.push([2,'来源公式','LG2026.xlsx','装箱表部分公式缓存为 Excel 名称未解析错误；实际装箱数量、箱数等数值字段可读取','不使用错误公式结果，只使用明确数值列','LG2026.xlsx / Sheet1 / 公式与缓存值','接受当前明确数值；如需复核，再修复 Excel 源公式','待确认']);
pendingRows.push([3,'二级批发价','全部产品','HOME STORE 价作为最高级批发价；中间二级批发价暂未提供','二级批发价字段留空，不影响采购价、最终批发价和 HOME STORE 价','最终对外报价单；项目价格规则','后续确定二级批发价后补录','待后续']);
pendingSheet.getRange(`A5:H${4 + pendingRows.length}`).values = pendingRows; body(pendingSheet, 5, 4 + pendingRows.length, 'H');
pendingSheet.getRange('A5:A20').format.numberFormat = '0';
pendingSheet.freezePanes.freezeRows(4);
for (const [range, width] of [['A:A',8],['B:B',14],['C:C',22],['D:D',48],['E:E',40],['F:F',42],['G:G',42],['H:H',12]]) pendingSheet.getRange(range).format.columnWidth = width;

title(summarySheet, 'H', '读取摘要');
note(summarySheet, 'H', '四份本地 Excel 只读解析结果。未连接 qq、ERP 或 WSL，未修改任何源文件。');
summarySheet.getRange('A4:H4').values = [['项目','值','依据/说明','','','','','']]; headers(summarySheet, 4, 'H');
const summaryRows = [
  ['唯一匹配产品数', products.length, '以货号/条码连接，名称与规格交叉核对'],
  ['未匹配产品数', 0, '12/12 货号均在订货、装箱、报价三表出现'],
  ['色卡明确固定色号行数', explicitColors.length, '来自莫桑比克色卡文档 Sheet1'],
  ['色卡覆盖货号数', new Set(colorGroups.map(c => c.itemCode)).size, 'B-DY、B-DR、B-ST、B-SW；仅3款有明确色号'],
  ['混色普通 Item 数', products.length - variantProducts.length, '未提供具体色号的9款按混色售卖，不生成模板变体'],
  ['订货总数量(条)', products.reduce((a, p) => a + (p.orderedQty ?? 0), 0), '订货表 6.8件数 × 预估装箱数'],
  ['实际装箱总数量(条)', products.reduce((a, p) => a + (p.actualQty ?? 0), 0), 'LG2026.xlsx 总数量（条）'],
  ['数量差异(条)', products.reduce((a, p) => a + (p.actualQty ?? 0) - (p.orderedQty ?? 0), 0), '实际装箱 - 订货'],
  ['源公式状态', formulaErrorSource, '输出未引用源文件异常公式结果'],
  ['价格规则', '成本价+批发价+HOME STORE价', '成本价取报价计算单；最终报价单批发价为最终批发价；HOME STORE为最高级批发价；同款不同颜色共用价格；二级批发价暂空'],
  ['库存数量规则', '采用实际装箱数量', '普通 Item 采用商品总数量；Variant 按色号件数 × 对应商品预估装箱数分配，已导入 Receiving'],
  ['Item Group', '窗帘', '当前生产规则；历史“窗帘成品”已删除，不再使用'],
];
summarySheet.getRange(`A5:C${4 + summaryRows.length}`).values = summaryRows;
body(summarySheet, 5, 4 + summaryRows.length, 'C');
summarySheet.getRange('A17:H17').merge(); summarySheet.getRange('A17').values = [['源工作表读取明细']]; summarySheet.getRange('A17:H17').format = { fill: '#D9EAF7', font: { name: font, size: 10, bold: true }, verticalAlignment: 'center' };
summarySheet.getRange('A18:H18').values = [['文件','工作表','Used Range','行数','公式单元格','图片对象','合并范围','备注']]; headers(summarySheet, 18, 'H');
const sourceDetails = [
  ['莫桑比克窗帘下单(1)(1).xlsx','Sheet1','A1:S59',59,16,18,'A1:S1; A2:C2; D2:S2; 分组行合并','订货字段与色号/颜色要求'],
  ['莫桑比克窗帘下单(1)(1).xlsx','Sheet2','A3:A11',9,0,0,'无','唛头文本'],
  ['LG2026.xlsx','Sheet1','A1:R22',22,40,16,'A1:R1; A2:H2; K2:R2','实际装箱数量、箱数、条码'],
  ['(已瘦身)SOLUA HOME窗帘报价单（HOME STORE版）(1).xlsx','Sheet1','A1:L15',15,0,46,'无','对外商品名称、批发价、HOME STORE价、建议零售价、产品图片'],
  ['SOLUA HOME窗帘报价计算单(2).xlsx','Sheet1','A1:R13',13,10,11,'无','成本/MT；用于采购价'],
  ['莫桑比克色卡文档.xlsx','Sheet1','A1:G48',48,0,9,'E12:F12; A2:A11; A13:A30; A31:A48; B2:B11; B13:B30; B31:B48; D/G分组','色号、色卡图片、色卡订货数量'],
  ['莫桑比克色卡文档.xlsx','Sheet2','A1',1,0,0,'无','空/占位工作表'],
  ['莫桑比克色卡文档.xlsx','Sheet3','A1',1,0,0,'无','空/占位工作表'],
];
summarySheet.getRange(`A19:H${18 + sourceDetails.length}`).values = sourceDetails; body(summarySheet, 19, 18 + sourceDetails.length, 'H');
summarySheet.getRange('D19:F26').format.numberFormat = '#,##0';
summarySheet.freezePanes.freezeRows(18);
for (const [range, width] of [['A:A',36],['B:B',22],['C:C',22],['D:F',14],['G:G',64],['H:H',34]]) summarySheet.getRange(range).format.columnWidth = width;

wb.recalculate();
const checks = [];
for (const [sheetName, range] of [['导入数据', `A1:S${priceStart + priceRows.length - 1}`], ['来源映射', `A1:AD${colorMapStart + colorMapRows.length - 1}`], ['待确认项', `A1:H${4 + pendingRows.length}`], ['读取摘要', `A1:H${18 + sourceDetails.length}`]]) {
  const c = await wb.inspect({ kind: 'table', range: `${sheetName}!${range}`, include: 'values,formulas', tableMaxRows: 8, tableMaxCols: 12, maxChars: 6000 });
  checks.push({ sheetName, range, ndjson: c.ndjson });
}
const errors = await wb.inspect({ kind: 'match', searchTerm: '#REF!|#DIV/0!|#VALUE!|#NAME\\?|#N/A|#NUM!|#NULL!|#SPILL!|#CALC!', options: { useRegex: true, maxResults: 300 }, summary: 'final formula error scan' });
await fs.writeFile(`${outDir}/verification.json`, JSON.stringify({ checks, formulaErrors: errors.ndjson }, null, 2), 'utf8');
for (const sheet of [importSheet, mappingSheet, pendingSheet, summarySheet]) {
  const preview = await wb.render({ sheetName: sheet.name, autoCrop: 'all', scale: 1, format: 'png' });
  await fs.writeFile(`${outDir}/preview_${sheet.name}.png`, new Uint8Array(await preview.arrayBuffer()));
}
const xlsx = await SpreadsheetFile.exportXlsx(wb);
await xlsx.save(outputPath);

const reopened = await SpreadsheetFile.importXlsx(await FileBlob.load(outputPath));
const savedCheck = await reopened.inspect({ kind: 'sheet,table', maxChars: 5000, tableMaxRows: 5, tableMaxCols: 10 });
await fs.writeFile(`${outDir}/saved_verification.json`, JSON.stringify({ outputPath, summary: savedCheck.ndjson }, null, 2), 'utf8');
await fs.writeFile(`${outDir}/erp_import_payload.json`, JSON.stringify({
  generatedAt: new Date().toISOString(),
  itemGroup: '窗帘',
  stockUom: '条',
  priceLists: ['Standard Buying', 'Wholesale Selling', 'Standard Selling'],
  products,
  variants: variantRows.map(r => ({
    itemCode: r[1], variantOf: r[2], itemName: r[3], colorCode: r[4], color: r[5],
    barcode: r[6], orderQty: r[7], actualQty: r[8], uom: r[9],
  })),
  prices: priceRows.map(r => ({
    itemCode: r[1], templateItemCode: r[2], priceList: r[3], rate: r[4],
    currency: r[5], uom: r[6], buying: r[7], selling: r[8],
  })),
}, null, 2), 'utf8');
console.log(JSON.stringify({ outputPath, products: products.length, explicitColors: explicitColors.length, variantRows: variantRows.length, priceRows: priceRows.length, formulaErrors: errors.ndjson }, null, 2));
