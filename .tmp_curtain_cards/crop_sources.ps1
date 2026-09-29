Add-Type -AssemblyName System.Drawing

$root = 'C:\Users\Yang\solua-home\sites\erpnext\outputs\curtain_color_cards_20260919'
$media = Join-Path $root 'extracted_sources\raw_xlsx_media'
$out = Join-Path $root 'extracted_sources\crops'
New-Item -ItemType Directory -Path $out -Force | Out-Null

function Save-Crop([string]$sourceName, [string]$outputName, [int]$x, [int]$y, [int]$w, [int]$h) {
    $source = Join-Path $media $sourceName
    $image = [System.Drawing.Bitmap]::new($source)
    try {
        $rect = [System.Drawing.Rectangle]::new($x, $y, $w, $h)
        $crop = $image.Clone($rect, $image.PixelFormat)
        try {
            $crop.Save((Join-Path $out $outputName), [System.Drawing.Imaging.ImageFormat]::Png)
        } finally {
            $crop.Dispose()
        }
    } finally {
        $image.Dispose()
    }
}

# SH151046 / B-DY. Source: Sheet1 G2:G11, xl/media/image1.png.
$dy = @(
    @('09', 24, 22, 140, 110), @('27', 207, 22, 140, 110),
    @('10', 24, 149, 140, 109), @('34', 207, 149, 140, 109),
    @('11', 24, 275, 140, 108), @('37', 207, 275, 140, 108),
    @('19', 24, 400, 140, 108), @('43', 207, 400, 140, 108),
    @('21', 24, 525, 140, 109), @('44', 207, 525, 140, 109)
)
foreach ($c in $dy) { Save-Crop 'image1.png' ("SH151046-color-{0}-source.png" -f $c[0]) $c[1] $c[2] $c[3] $c[4] }

# SH151060 / B-DR. Source: Sheet1 G12, xl/media/image3.png.
$dr = @(
    @('04', 47, 27, 164, 134), @('06', 214, 27, 164, 134), @('07', 381, 27, 159, 134),
    @('11', 47, 186, 164, 133), @('13', 214, 186, 164, 133), @('14', 381, 186, 159, 133),
    @('15', 47, 344, 164, 134), @('16', 214, 344, 164, 134), @('09', 381, 344, 159, 134),
    @('20', 47, 503, 164, 135)
)
foreach ($c in $dr) { Save-Crop 'image3.png' ("SH151060-color-{0}-source.png" -f $c[0]) $c[1] $c[2] $c[3] $c[4] }

Get-ChildItem -LiteralPath $out -File | Sort-Object Name | Select-Object Name,Length
