import fs from 'node:fs/promises';
import { FileBlob, SpreadsheetFile } from '@oai/artifact-tool';

const sources = [
  { id: 'order', path: 'D:/WeChat/xwechat_files/chenyangyang_7cef/msg/file/2026-09/莫桑比克窗帘下单(1)(1).xlsx' },
  { id: 'packing', path: 'C:/Users/Yang/Desktop/Solua/LG2026.xlsx' },
  { id: 'quote', path: 'C:/Users/Yang/Desktop/Solua/SOLUA HOME窗帘报价计算单(2).xlsx' },
];

const out = { sources: [], createdAt: new Date().toISOString() };
for (const source of sources) {
  const wb = await SpreadsheetFile.importXlsx(await FileBlob.load(source.path));
  const summary = await wb.inspect({ kind: 'workbook,sheet,table,drawing', maxChars: 12000, tableMaxRows: 8, tableMaxCols: 12, tableMaxCellChars: 120 });
  const sheets = [];
  for (const sheet of wb.worksheets.items) {
    const used = sheet.getUsedRange();
    let values = [];
    let formulas = [];
    let address = '';
    if (used) {
      values = used.values ?? [];
      formulas = used.formulas ?? [];
      address = String(used.address ?? '');
    }
    const formulaCells = [];
    for (let r = 0; r < formulas.length; r++) {
      for (let c = 0; c < (formulas[r] ?? []).length; c++) {
        const f = formulas[r][c];
        if (f) formulaCells.push({ row: r + 1, col: c + 1, formula: f, value: values?.[r]?.[c] ?? null });
      }
    }
    const nonEmpty = [];
    for (let r = 0; r < values.length; r++) {
      const row = values[r] ?? [];
      if (row.some(v => v !== null && v !== undefined && v !== '')) nonEmpty.push({ row: r + 1, values: row });
    }
    const drawings = await wb.inspect({ kind: 'drawing', sheetId: sheet.name, maxChars: 8000 });
    sheets.push({ name: sheet.name, usedAddress: address, rowCount: values.length, colCount: Math.max(0, ...values.map(r => (r ?? []).length)), nonEmptyRows: nonEmpty, formulaCells, drawings: drawings.ndjson });
  }
  out.sources.push({ ...source, summary: summary.ndjson, sheets });
}
await fs.writeFile('outputs/01a09c05-ffba-7b72-b03e-a93152caaa99/source_inspection.json', JSON.stringify(out, null, 2), 'utf8');
console.log(JSON.stringify(out.sources.map(s => ({ id: s.id, sheets: s.sheets.map(x => ({ name: x.name, usedAddress: x.usedAddress, rowCount: x.rowCount, colCount: x.colCount, nonEmptyRows: x.nonEmptyRows.length, formulas: x.formulaCells.length })) })), null, 2));
