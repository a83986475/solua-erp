# Curtain rod item normalization audit — pre-rename

- Site: `erp.solua.one`
- Captured: `2026-09-19 23:52:07.808558`
- Stage: read-only scope export after idempotent field creation, before any Item rename
- User-confirmed color-card source: `C:\Users\Yang\AppData\Local\Temp\codex-clipboard-ae8a6144-8d10-4f2e-9dac-0b47c03cee89.png`

## Scope and baseline

- 4 templates and 20 variants, covering 2m/3m single and double curtain rods.
- 20 Item Price rows covering 20 variants.
- 4 template barcode rows covering 4 templates; variants currently have no independent Item Barcode rows.
- 40 Bin rows; total actual quantity 8040 and total stock value 2444640 MZN.

| Current item_code | variant_of | Type | Chinese item_name | Image | Abbreviation backup |
|---|---|---|---|---|---|
| SH151138-2MS |  | template | 2米单杆螺旋头  |  |  |
| SH151138-2MS-1 | SH151138-2MS | variant | 2米单杆螺旋头  / 红古 | /assets/solua_home/images/curtain_cards/curtain-swatch-single-vermelha-v2.png |  |
| SH151138-2MS-2 | SH151138-2MS | variant | 2米单杆螺旋头  / 青古 | /assets/solua_home/images/curtain_cards/curtain-swatch-single-bronze-antigo-v2.png |  |
| SH151138-2MS-DR | SH151138-2MS | variant | 2米单杆螺旋头  / 金色 | /assets/solua_home/images/curtain_cards/curtain-swatch-dourado.png | SH151138-2MS-DR |
| SH151138-2MS-PR | SH151138-2MS | variant | 2米单杆螺旋头  / 黑色 | /assets/solua_home/images/curtain_cards/curtain-swatch-preto.png | SH151138-2MS-PR |
| SH151138-2MS-PT | SH151138-2MS | variant | 2米单杆螺旋头  / 银色 | /assets/solua_home/images/curtain_cards/curtain-swatch-prata.png | SH151138-2MS-PT |
| SH151145-2MD |  | template | 2米双杆螺旋头  |  |  |
| SH151145-2MD-1 | SH151145-2MD | variant | 2米双杆螺旋头  / 红古 | /assets/solua_home/images/curtain_cards/curtain-swatch-dual-vermelha-v2.png |  |
| SH151145-2MD-2 | SH151145-2MD | variant | 2米双杆螺旋头  / 青古 | /assets/solua_home/images/curtain_cards/curtain-swatch-dual-bronze-antigo-v2.png |  |
| SH151145-2MD-DR | SH151145-2MD | variant | 2米双杆螺旋头  / 金色 | /assets/solua_home/images/curtain_cards/curtain-swatch-dual-dourado-v2.png | SH151145-2MD-DR |
| SH151145-2MD-PR | SH151145-2MD | variant | 2米双杆螺旋头  / 黑色 | /assets/solua_home/images/curtain_cards/curtain-swatch-dual-preto-v2.png | SH151145-2MD-PR |
| SH151145-2MD-PT | SH151145-2MD | variant | 2米双杆螺旋头  / 银色 | /assets/solua_home/images/curtain_cards/curtain-swatch-dual-prata-v2.png | SH151145-2MD-PT |
| SH151152-3MS |  | template | 3米单杆螺旋头  |  |  |
| SH151152-3MS-1 | SH151152-3MS | variant | 3米单杆螺旋头  / 红古 | /assets/solua_home/images/curtain_cards/curtain-swatch-single-vermelha-v2.png |  |
| SH151152-3MS-2 | SH151152-3MS | variant | 3米单杆螺旋头  / 青古 | /assets/solua_home/images/curtain_cards/curtain-swatch-single-bronze-antigo-v2.png |  |
| SH151152-3MS-DR | SH151152-3MS | variant | 3米单杆螺旋头  / 金色 | /assets/solua_home/images/curtain_cards/curtain-swatch-dourado.png | SH151152-3MS-DR |
| SH151152-3MS-PR | SH151152-3MS | variant | 3米单杆螺旋头  / 黑色 | /assets/solua_home/images/curtain_cards/curtain-swatch-preto.png | SH151152-3MS-PR |
| SH151152-3MS-PT | SH151152-3MS | variant | 3米单杆螺旋头  / 银色 | /assets/solua_home/images/curtain_cards/curtain-swatch-prata.png | SH151152-3MS-PT |
| SH151169-3MD |  | template | 3米双杆螺旋头  |  |  |
| SH151169-3MD-1 | SH151169-3MD | variant | 3米双杆螺旋头  / 红古 | /assets/solua_home/images/curtain_cards/curtain-swatch-dual-vermelha-v2.png |  |
| SH151169-3MD-2 | SH151169-3MD | variant | 3米双杆螺旋头  / 青古 | /assets/solua_home/images/curtain_cards/curtain-swatch-dual-bronze-antigo-v2.png |  |
| SH151169-3MD-DR | SH151169-3MD | variant | 3米双杆螺旋头  / 金色 | /assets/solua_home/images/curtain_cards/curtain-swatch-dual-dourado-v2.png | SH151169-3MD-DR |
| SH151169-3MD-PR | SH151169-3MD | variant | 3米双杆螺旋头  / 黑色 | /assets/solua_home/images/curtain_cards/curtain-swatch-dual-preto-v2.png | SH151169-3MD-PR |
| SH151169-3MD-PT | SH151169-3MD | variant | 3米双杆螺旋头  / 银色 | /assets/solua_home/images/curtain_cards/curtain-swatch-dual-prata-v2.png | SH151169-3MD-PT |

## Confirmed color mapping

| Formal suffix | Portuguese | English | Evidence |
|---|---|---|---|
| 1 | Vermelha | Red Antique | ERP Item Attribute Cor and user-confirmed color card |
| 2 | Bronze Antigo | Antique Bronze | ERP Item Attribute Cor and user-confirmed color card |
| 3 | Prateado | Silver | user-confirmed physical color card |
| 4 | Dourado | Gold | user-confirmed physical color card |
| 5 | Preto | Black | user-confirmed physical color card |

The physical color card is the highest-priority business evidence for the 3/4/5 mapping. The ERP `Cor` attribute independently confirms `Vermelha=1`, `Bronze Antigo=2`, `Prata=PT`, `Dourado=DR`, and `Preto=PR`.

## Fields created/reused

- `custom_color_abbreviation_item_code` — Color Abbreviation Item Code (Data); Custom Field document `Item-custom_color_abbreviation_item_code`
- `custom_item_description_en` — English Item Description (Data); Custom Field document `Item-custom_item_description_en`
- `custom_item_description_pt` — Portuguese Item Description (Data); Custom Field document `Item-custom_item_description_pt`
- `custom_item_name_en` — English Item Name (Data); Custom Field document `Item-custom_item_name_en`
- `custom_item_name_pt` — Portuguese Item Name (Data); Custom Field document `Item-custom_item_name_pt`

## Planned native renames

- 12 variants: `PR` → `5`, `PT` → `3`, `DR` → `4`.
- `1` and `2` already use the confirmed formal numeric suffixes.
- No SQL item-code update is permitted; all renames will use Frappe `rename_doc` after target-collision checks.

## Backup

- Full site backup completed before data changes; see `backup` in the JSON and the four hashed files under the remote site's private backup directory.

