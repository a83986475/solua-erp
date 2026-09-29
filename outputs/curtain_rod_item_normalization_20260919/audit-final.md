# Curtain rod item normalization — final audit

- Site: `erp.solua.one`
- Captured: `2026-09-19 23:57:34.410052`
- Full export is in `audit-final.json`; the pre-rename snapshot is in `audit-pre-rename.json`.
- Rename method: Frappe native `frappe.rename_doc`; no SQL item-code rename.

## Confirmed formal color codes

| Suffix | Portuguese | English | Previous abbreviation |
|---|---|---|---|
| 1 | Vermelha | Red Antique | already numeric |
| 2 | Bronze Antigo | Antique Bronze | already numeric |
| 3 | Prateado | Silver | PT |
| 4 | Dourado | Gold | DR |
| 5 | Preto | Black | PR |

The 3/4/5 mapping is based on the user-confirmed physical color card; the ERP `Cor` attribute independently confirms the existing abbreviations and 1/2 values.

## Fields

- `custom_color_abbreviation_item_code` — Color Abbreviation Item Code; Custom Field `Item-custom_color_abbreviation_item_code`
- `custom_item_description_en` — English Item Description; Custom Field `Item-custom_item_description_en`
- `custom_item_description_pt` — Portuguese Item Description; Custom Field `Item-custom_item_description_pt`
- `custom_item_name_en` — English Item Name; Custom Field `Item-custom_item_name_en`
- `custom_item_name_pt` — Portuguese Item Name; Custom Field `Item-custom_item_name_pt`

## Verification

- 24 Items: 4 templates and 20 variants; all variants retain a parent.
- 12 native renames completed; old PR/PT/DR count = 0; numeric 3/4/5 count = 12.
- 20 Standard Selling prices, 4 template barcodes, 20 variant images, and 20 enabled sales variants verified.
- 40 Bin rows; total actual quantity = 8040; total stock value = 2444640 MZN.
- No Item Price, Bin, Warehouse, or Barcode write was performed; quantity and value match the pre-change baseline.

## Backup

- Full site backup completed before the data changes; four files and SHA256 values are recorded in `audit-final.json`.

