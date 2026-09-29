from pathlib import Path
from PIL import Image
import json

ROOT = Path(__file__).parent
MEDIA = ROOT / "extracted_sources" / "raw_xlsx_media"
CROPS = ROOT / "extracted_sources" / "crops"
CROPS.mkdir(parents=True, exist_ok=True)

def save_crop(src_name, color_numbers, boxes, sku):
    src = Image.open(MEDIA / src_name)
    for color, box in zip(color_numbers, boxes):
        out = CROPS / f"{sku}-color-{color:02d}-source.png"
        src.crop(box).save(out)

# The first two swatch sheets were already cropped by the previous run.
# SH151107 is the only remaining unambiguous sheet: each image contains six
# numbered rows, and the left sample is a clean representative of each color.
save_crop(
    "image7.jpeg", range(1, 7),
    [(45, 80, 425, 315), (45, 380, 425, 610), (45, 675, 425, 900),
     (45, 970, 425, 1195), (45, 1275, 425, 1510), (45, 1585, 425, 1835)],
    "SH151107",
)
save_crop(
    "image8.jpeg", range(7, 13),
    [(45, 150, 425, 455), (45, 500, 425, 805), (45, 850, 425, 1155),
     (45, 1200, 425, 1505), (45, 1550, 425, 1825), (45, 1840, 425, 2040)],
    "SH151107",
)
save_crop(
    "image9.jpeg", range(13, 19),
    [(0, 120, 410, 395), (0, 435, 410, 710), (0, 750, 410, 1025),
     (0, 1060, 410, 1335), (0, 1370, 410, 1645), (0, 1680, 410, 1914)],
    "SH151107",
)

manifest = {
    "source_workbook": "D:/WeChat/xwechat_files/chenyangyang_7cef/msg/file/2026-09/莫桑比克色卡文档.xlsx",
    "logo": "C:/Users/Yang/Desktop/SOLUA LOGO源文件.jpg",
    "template": "Solua Home wide black textured background, gold rounded border, official logo, one independent color per PNG",
    "clear_mappings": [
        {"sku": "SH151046", "colors": [9, 10, 11, 19, 21, 27, 34, 37, 43, 44], "source": "/extracted_sources/raw_xlsx_media/image1.png", "anchor": "Sheet1!G2:G11", "status": "clear"},
        {"sku": "SH151060", "colors": [4, 6, 7, 9, 11, 13, 14, 15, 16, 20], "source": "/extracted_sources/raw_xlsx_media/image3.png", "anchor": "Sheet1!G12", "status": "clear"},
        {"sku": "SH151107", "colors": list(range(1, 19)), "source": ["/extracted_sources/raw_xlsx_media/image7.jpeg", "/extracted_sources/raw_xlsx_media/image8.jpeg", "/extracted_sources/raw_xlsx_media/image9.jpeg"], "anchor": "Sheet1!G15:G48 (numbered 1-18)", "status": "clear"},
    ],
    "paused_mappings": [
        {"sku": "SH151114", "colors": list(range(1, 19)), "source": "/extracted_sources/raw_xlsx_media/image6.jpeg", "anchor": "Sheet1!A36:A43", "status": "needs-confirmation", "question": "SH151114 的 18 个色号没有对应的色卡/编号照片；image6 只显示 8 个无编号实物。请提供 SH151114 的色号对应照片，或确认 image6 从左到右、从上到下对应哪些色号。"}
    ],
}
(ROOT / "mapping_manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
print("prepared", len(list(CROPS.glob("SH151107-color-*-source.png"))), "SH151107 source crops")
