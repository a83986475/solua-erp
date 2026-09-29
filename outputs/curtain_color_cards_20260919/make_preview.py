from pathlib import Path
from PIL import Image, ImageDraw
import json

ROOT = Path(__file__).parent
cards = sorted((ROOT / "cards").glob("*.png"))
assert len(cards) == 38, len(cards)
sizes = {Image.open(p).size for p in cards}
assert len(sizes) == 1, sizes
width, height = next(iter(sizes))
assert width > height and width / height > 1.4, (width, height)

thumb_w, thumb_h = 420, 236
cols = 4
rows = (len(cards) + cols - 1) // cols
preview = Image.new("RGB", (cols * thumb_w, rows * thumb_h), "#111111")
for i, path in enumerate(cards):
    im = Image.open(path).convert("RGB")
    im.thumbnail((thumb_w - 12, thumb_h - 12))
    x = (i % cols) * thumb_w + (thumb_w - im.width) // 2
    y = (i // cols) * thumb_h + (thumb_h - im.height) // 2
    preview.paste(im, (x, y))
preview.save(ROOT / "thumbnail_preview.png")

summary = {
    "generated_cards": len(cards),
    "dimensions": [width, height],
    "files": [p.name for p in cards],
    "preview": "thumbnail_preview.png",
    "mapping_manifest": "mapping_manifest.json",
}
(ROOT / "generation_summary.json").write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
print(json.dumps(summary, ensure_ascii=False))
