# Curtain rod item normalization — post-change verification

- Site: `erp.solua.one`
- Captured: `2026-09-19 23:54:53.529351`
- Rename method: Frappe native `frappe.rename_doc`; no SQL item-code rename
- User-confirmed physical color-card source recorded in the JSON audit only

## Final color and code mapping

| Formal suffix | Portuguese | English | Previous abbreviation |
|---|---|---|---|
| 1 | Vermelha | Red Antique | already numeric |
| 2 | Bronze Antigo | Antique Bronze | already numeric |
| 3 | Prateado | Silver | PT |
| 4 | Dourado | Gold | DR |
| 5 | Preto | Black | PR |

## Verification

- Items: 24 total = 4 templates + 20 variants.
- Native renames: 12; old PR/PT/DR suffix rows remaining: 0; new -3/-4/-5 rows: 12.
- Item Price: 20 rows covering 20 variants; no price write was performed.
- Barcodes: 4 template rows; variant/template relationships remain present.
- Images: 20/20 variants have images.
- POS visibility: 20/20 variants are enabled sales items.
- Bin: 40 rows; actual quantity 8040; stock value 2444640 MZN. These match the pre-change baseline.

## Custom fields

- `custom_color_abbreviation_item_code` — Color Abbreviation Item Code; `Item-custom_color_abbreviation_item_code`
- `custom_item_description_en` — English Item Description; `Item-custom_item_description_en`
- `custom_item_description_pt` — Portuguese Item Description; `Item-custom_item_description_pt`
- `custom_item_name_en` — English Item Name; `Item-custom_item_name_en`
- `custom_item_name_pt` — Portuguese Item Name; `Item-custom_item_name_pt`

Full item, attribute, barcode, price and Bin export is in `audit-post-verify.json`; the pre-rename export is in `audit-pre-rename.json`.

