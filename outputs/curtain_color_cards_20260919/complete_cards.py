from pathlib import Path
from PIL import Image, ImageChops, ImageDraw, ImageFont
import json


ROOT = Path(__file__).parent
FINAL = ROOT / "final_white_square"
SOURCES = ROOT / "extracted_sources" / "crops"
STAGING = ROOT / "repair_completion_20260920_v2"
CARDS = STAGING / "cards"
THUMBS = STAGING / "thumbnails"
SWATCH_BOX = (245, 290, 1010, 1010)
LABEL_BOX = (285, 1048, 969, 1155)
FONT_PATH = Path(r"C:\Windows\Fonts\arialbd.ttf")


if STAGING.exists():
    raise SystemExit(f"Refusing to overwrite existing staging folder: {STAGING}")
CARDS.mkdir(parents=True)
THUMBS.mkdir()


def fit_crop(image: Image.Image, ratio: float) -> Image.Image:
    width, height = image.size
    current = width / height
    if current > ratio:
        new_width = round(height * ratio)
        left = (width - new_width) // 2
        return image.crop((left, 0, left + new_width, height))
    new_height = round(width / ratio)
    top = (height - new_height) // 2
    return image.crop((0, top, width, top + new_height))


def source_pixels(path: Path) -> Image.Image:
    with Image.open(path) as source:
        rgba = source.convert("RGBA")
        white = Image.new("RGBA", rgba.size, (255, 255, 255, 255))
        white.alpha_composite(rgba)
        return white.convert("RGB")


def trim_white_edges(image: Image.Image) -> Image.Image:
    difference = ImageChops.difference(image, Image.new("RGB", image.size, (255, 255, 255))).convert("L")
    content = difference.point(lambda value: 255 if value > 35 else 0).getbbox()
    return image.crop(content) if content else image


def replace_swatch(base_path: Path, sku: str, sample: Image.Image) -> Image.Image:
    card = Image.open(base_path).convert("RGB")
    left, top, right, bottom = SWATCH_BOX
    sample = fit_crop(sample, (right - left) / (bottom - top))
    sample = sample.resize((right - left, bottom - top), Image.Resampling.LANCZOS)
    card.paste(sample, (left, top))
    return card


def relabel(card: Image.Image, sku: str) -> Image.Image:
    draw = ImageDraw.Draw(card)
    draw.rectangle(LABEL_BOX, fill=(253, 253, 253))
    font = ImageFont.truetype(str(FONT_PATH), 92)
    bounds = draw.textbbox((0, 0), sku, font=font, stroke_width=1)
    width = bounds[2] - bounds[0]
    x = (card.width - width) // 2 - bounds[0]
    y = 1057 - bounds[1]
    draw.text((x + 2, y + 2), sku, font=font, fill=(169, 128, 79))
    draw.text((x, y), sku, font=font, fill=(239, 180, 90), stroke_width=1, stroke_fill=(207, 152, 72))
    return card


def save(card: Image.Image, sku: str) -> None:
    path = CARDS / f"{sku}.png"
    card.save(path, format="PNG", optimize=True)
    card.resize((160, 160), Image.Resampling.LANCZOS).save(THUMBS / f"{sku}.png", format="PNG", optimize=True)


# Extract only the upper physical swatch, then crop a square-ish textile area
# matching the established card window. This removes the adjacent color entirely.
upper_samples = {
    "SH151107-10": source_pixels(SOURCES / "SH151107-color-10-source.png").crop((113, 0, 267, 145)),
    "SH151107-11": source_pixels(SOURCES / "SH151107-color-11-source.png").crop((142, 0, 238, 90)),
}
for sku, sample in upper_samples.items():
    save(replace_swatch(FINAL / f"{sku}.png", sku, sample), sku)

# The color-43/-44 source pixels are used directly; no texture is generated.
for number in (43, 44):
    sku = f"SH151046-{number}"
    sample = trim_white_edges(source_pixels(SOURCES / f"SH151046-color-{number}-source.png"))
    save(replace_swatch(FINAL / f"{sku}.png", sku, sample), sku)

# SH151114 was explicitly confirmed to use the same numbered 18-swatch set as
# SH151107. Reuse each finished SH151107 card's exact swatch pixels and change
# only the SKU label. The repaired 10/11 cards above are the source for those two.
for number in range(1, 19):
    source_sku = f"SH151107-{number:02d}"
    target_sku = f"SH151114-{number:02d}"
    source_path = CARDS / f"{source_sku}.png" if source_sku in upper_samples else FINAL / f"{source_sku}.png"
    if source_sku not in upper_samples:
        card = Image.open(source_path).convert("RGB")
    else:
        card = Image.open(source_path).convert("RGB")
    save(relabel(card, target_sku), target_sku)

summary = {
    "staged_cards": len(list(CARDS.glob("*.png"))),
    "staged_thumbnails": len(list(THUMBS.glob("*.png"))),
    "dimensions": [list(size) for size in sorted({Image.open(path).size for path in CARDS.glob("*.png")})],
    "cards": sorted(path.name for path in CARDS.glob("*.png")),
    "source_set_for_SH151114": "SH151107-01..18 (user-confirmed same swatch set)",
    "swatch_pixel_sources": ["SH151107-color-10-source.png upper swatch", "SH151107-color-11-source.png upper swatch", "SH151046-color-43-source.png", "SH151046-color-44-source.png"],
}
(STAGING / "staging_summary.json").write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
print(json.dumps(summary, ensure_ascii=False))
