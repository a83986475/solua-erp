import fs from 'node:fs/promises';
import { FileBlob, SpreadsheetFile } from '@oai/artifact-tool';

const path = 'D:/WeChat/xwechat_files/chenyangyang_7cef/msg/file/2026-09/莫桑比克色卡文档.xlsx';
const wb = await SpreadsheetFile.importXlsx(await FileBlob.load(path));
const summary = await wb.inspect({ kind: 'workbook,sheet,table,drawing', maxChars: 30000, tableMaxRows: 30, tableMaxCols: 20, tableMaxCellChars: 200 });
const sheets = [];
for (const sheet of wb.worksheets.items) {
  const used = sheet.getUsedRange();
  const values = used?.values ?? [];
  const formulas = used?.formulas ?? [];
  const formulaCells = [];
  for (let r = 0; r < formulas.length; r++) for (let c = 0; c < (formulas[r] ?? []).length; c++) if (formulas[r][c]) formulaCells.push({ row: r + 1, col: c + 1, formula: formulas[r][c], value: values?.[r]?.[c] ?? null });
  const rows = values.map((row, i) => ({ row: i + 1, values: row }));
  const drawings = await wb.inspect({ kind: 'drawing', sheetId: sheet.name, maxChars: 30000 });
  sheets.push({ name: sheet.name, usedAddress: String(used?.address ?? ''), rowCount: values.length, colCount: Math.max(0, ...values.map(r => (r ?? []).length)), rows, formulaCells, drawings: drawings.ndjson });
}
const out = { path, summary: summary.ndjson, sheets, createdAt: new Date().toISOString() };
await fs.writeFile('outputs/01a09c05-ffba-7b72-b03e-a93152caaa99/color_inspection.json', JSON.stringify(out, null, 2), 'utf8');
console.log(JSON.stringify({ sheets: sheets.map(s => ({ name: s.name, usedAddress: s.usedAddress, rowCount: s.rowCount, colCount: s.colCount, formulas: s.formulaCells.length })) }, null, 2));
