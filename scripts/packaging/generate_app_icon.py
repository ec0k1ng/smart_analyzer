from __future__ import annotations

from pathlib import Path

from PIL import Image, ImageDraw, ImageFilter


ROOT = Path(__file__).resolve().parent
OUTPUT_ICON = ROOT / "assets" / "apex_insight.ico"


def _vertical_gradient(width: int, height: int, start: tuple[int, int, int], end: tuple[int, int, int]) -> Image.Image:
    gradient = Image.new("RGBA", (width, height))
    pixels = gradient.load()
    for y in range(height):
        ratio = y / max(height - 1, 1)
        red = int(start[0] + (end[0] - start[0]) * ratio)
        green = int(start[1] + (end[1] - start[1]) * ratio)
        blue = int(start[2] + (end[2] - start[2]) * ratio)
        for x in range(width):
            pixels[x, y] = (red, green, blue, 255)
    return gradient


def main() -> int:
    size = 512
    canvas = Image.new("RGBA", (size, size), (0, 0, 0, 0))

    card_mask = Image.new("L", (size, size), 0)
    mask_draw = ImageDraw.Draw(card_mask)
    mask_draw.rounded_rectangle((28, 28, 484, 484), radius=110, fill=255)

    card = _vertical_gradient(size, size, (11, 36, 63), (30, 87, 141))
    highlight = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    highlight_draw = ImageDraw.Draw(highlight)
    highlight_draw.ellipse((40, 24, 370, 240), fill=(120, 193, 255, 42))
    highlight = highlight.filter(ImageFilter.GaussianBlur(18))
    card = Image.alpha_composite(card, highlight)
    card.putalpha(card_mask)
    canvas.alpha_composite(card)

    shadow = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    shadow_draw = ImageDraw.Draw(shadow)
    shadow_draw.rounded_rectangle((48, 340, 464, 410), radius=34, fill=(4, 14, 28, 110))
    shadow = shadow.filter(ImageFilter.GaussianBlur(14))
    canvas.alpha_composite(shadow)

    draw = ImageDraw.Draw(canvas)

    base_bar = [(92, 356), (190, 190), (255, 190), (355, 356), (292, 356), (258, 296), (186, 296), (154, 356)]
    draw.polygon(base_bar, fill=(244, 248, 255, 255))

    inner_cut = [(196, 356), (222, 312), (224, 312), (242, 356)]
    draw.polygon(inner_cut, fill=(25, 77, 122, 255))
    inner_cut_right = [(268, 356), (290, 312), (292, 312), (318, 356)]
    draw.polygon(inner_cut_right, fill=(25, 77, 122, 255))

    chart_points = [(128, 318), (192, 272), (248, 290), (314, 220), (376, 246)]
    draw.line(chart_points, fill=(71, 214, 198, 255), width=24, joint="curve")
    for index, point in enumerate(chart_points):
        radius = 18 if index != len(chart_points) - 1 else 20
        fill = (253, 185, 78, 255) if index == len(chart_points) - 1 else (240, 249, 255, 255)
        outline = (8, 43, 73, 255) if index != len(chart_points) - 1 else (146, 83, 12, 255)
        draw.ellipse((point[0] - radius, point[1] - radius, point[0] + radius, point[1] + radius), fill=fill, outline=outline, width=7)

    road = [(112, 398), (400, 398), (430, 428), (82, 428)]
    draw.rounded_rectangle((82, 386, 430, 432), radius=22, fill=(10, 29, 49, 210))
    draw.line((160, 409, 220, 409), fill=(121, 177, 218, 255), width=10)
    draw.line((254, 409, 314, 409), fill=(121, 177, 218, 255), width=10)

    OUTPUT_ICON.parent.mkdir(parents=True, exist_ok=True)
    canvas.save(OUTPUT_ICON, format="ICO", sizes=[(256, 256), (128, 128), (96, 96), (64, 64), (48, 48), (32, 32), (24, 24), (16, 16)])
    print(OUTPUT_ICON)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
