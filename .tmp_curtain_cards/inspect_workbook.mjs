import fs from "node:fs/promises";
import path from "node:path";
import { FileBlob, SpreadsheetFile } from "@oai/artifact-tool";

const source = "D:/WeChat/xwechat_files/chenyangyang_7cef/msg/file/2026-09/莫桑比克色卡文档.xlsx";
const outDir = "C:/Users/Yang/solua-home/sites/erpnext/outputs/curtain_color_cards_20260919";
const workbook = await SpreadsheetFile.importXlsx(await FileBlob.load(source));

const overviewInspect = await workbook.inspect({
  kind: "workbook,sheet,table,drawing,definedName",
  maxChars: 100000,
  tableMaxRows: 15,
  tableMaxCols: 20,
  options: { maxResults: 1000 },
});

const result = {
  source,
  overviewNdjson: overviewInspect.ndjson,
  sheets: [],
};

for (const sheet of workbook.worksheets.items) {
  const used = sheet.getUsedRange();
  const address = used ? used.address : null;
  const tableInspect = address ? await workbook.inspect({
    kind: "table",
    sheetId: sheet.name,
    range: address,
    include: "values,formulas",
    tableMaxRows: 500,
    tableMaxCols: 100,
    tableMaxCellChars: 1000,
    maxChars: 300000,
  }) : null;
  const drawingInspect = await workbook.inspect({
    kind: "drawing",
    sheetId: sheet.name,
    maxChars: 100000,
    options: { maxResults: 1000 },
  });
  result.sheets.push({
    name: sheet.name,
    usedRange: address,
    values: used ? used.values : [],
    formulas: used ? used.formulas : [],
    tableNdjson: tableInspect?.ndjson || "",
    drawingNdjson: drawingInspect.ndjson,
  });
  if (address) {
    const preview = await workbook.render({ sheetName: sheet.name, autoCrop: "all", scale: 1.5, format: "png" });
    const safe = sheet.name.replace(/[\\/:*?"<>|]/g, "_");
    await fs.writeFile(path.join(outDir, "sheet_previews", `${safe}.png`), new Uint8Array(await preview.arrayBuffer()));
  }
}

await fs.writeFile(path.join(outDir, "artifact_inspection.json"), JSON.stringify(result, null, 2), "utf8");
console.log(JSON.stringify({ sheets: result.sheets.map(s => ({ name: s.name, usedRange: s.usedRange, drawings: s.drawingNdjson.split("\n").filter(Boolean).length })), output: path.join(outDir, "artifact_inspection.json") }, null, 2));
