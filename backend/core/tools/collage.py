"""a grid collage of several pictures, and cutting one picture into equal tiles."""
from __future__ import annotations

import math
from dataclasses import dataclass

from PIL import Image, ImageOps

from .common import MAX_PIXELS, flatten, hex_to_rgb

RATIOS = {"1:1": (1, 1), "4:3": (4, 3), "3:4": (3, 4), "3:2": (3, 2), "2:3": (2, 3), "16:9": (16, 9), "9:16": (9, 16)}
MAX_IMAGES = 60
MAX_SIDE = 16000


@dataclass
class CollageOptions:
    columns: int = 0                 # 0 = pick a nice number
    cell_width: int = 600
    ratio: str = "1:1"
    fit: str = "cover"               # cover crops to fill the cell, contain shows the whole picture
    gap: int = 12
    margin: int = 12
    background: str = "#ffffff"
    transparent: bool = False
    fmt: str = "jpg"                 # jpg | png
    quality: int = 90

    @classmethod
    def from_dict(cls, raw: dict | None) -> "CollageOptions":
        raw = raw or {}
        options = cls()
        for key in ("columns", "cell_width", "gap", "margin", "quality"):
            setattr(options, key, int(round(float(raw.get(key, getattr(options, key))))))
        options.ratio, options.fit = str(raw.get("ratio", options.ratio)), str(raw.get("fit", options.fit))
        options.background, options.fmt = str(raw.get("background", options.background)), str(raw.get("fmt", options.fmt))
        options.transparent = bool(raw.get("transparent", options.transparent))
        if options.ratio not in RATIOS:
            raise ValueError("Unknown cell shape")
        if options.fit not in ("cover", "contain") or options.fmt not in ("jpg", "png"):
            raise ValueError("Unknown fit or format")
        options.columns = min(12, max(0, options.columns))
        options.cell_width = min(2000, max(60, options.cell_width))
        options.gap, options.margin = min(200, max(0, options.gap)), min(400, max(0, options.margin))
        options.quality = min(100, max(1, options.quality))
        hex_to_rgb(options.background)
        if options.transparent and options.fmt == "jpg":
            options.fmt = "png"  # jpg has no transparency
        return options


def make_collage(pictures: list[Image.Image], options: CollageOptions) -> Image.Image:
    if len(pictures) < 2:
        raise ValueError("Choose at least two pictures.")
    if len(pictures) > MAX_IMAGES:
        raise ValueError(f"A collage can have up to {MAX_IMAGES} pictures.")
    count = len(pictures)
    columns = options.columns or math.ceil(math.sqrt(count))
    columns = min(columns, count)
    rows = math.ceil(count / columns)
    ratio_w, ratio_h = RATIOS[options.ratio]
    cell_w = options.cell_width
    cell_h = max(1, round(cell_w * ratio_h / ratio_w))
    width = columns * cell_w + (columns - 1) * options.gap + 2 * options.margin
    height = rows * cell_h + (rows - 1) * options.gap + 2 * options.margin
    if max(width, height) > MAX_SIDE or width * height > MAX_PIXELS:
        raise ValueError("That collage would be too large. Use a smaller cell width or fewer columns.")
    colour = hex_to_rgb(options.background)
    sheet = Image.new("RGBA", (width, height), (0, 0, 0, 0) if options.transparent else colour + (255,))
    for index, picture in enumerate(pictures):
        row, column = divmod(index, columns)
        cell = picture.convert("RGBA")
        cell = ImageOps.fit(cell, (cell_w, cell_h), Image.LANCZOS) if options.fit == "cover" else ImageOps.contain(cell, (cell_w, cell_h), Image.LANCZOS)
        x = options.margin + column * (cell_w + options.gap) + (cell_w - cell.width) // 2
        y = options.margin + row * (cell_h + options.gap) + (cell_h - cell.height) // 2
        sheet.alpha_composite(cell, (x, y))
    return sheet if options.transparent else flatten(sheet, colour)


@dataclass
class SplitOptions:
    rows: int = 2
    columns: int = 2
    fmt: str = "png"                 # png | jpg | webp
    quality: int = 92

    @classmethod
    def from_dict(cls, raw: dict | None) -> "SplitOptions":
        raw = raw or {}
        options = cls()
        for key in ("rows", "columns", "quality"):
            setattr(options, key, int(round(float(raw.get(key, getattr(options, key))))))
        options.fmt = str(raw.get("fmt", options.fmt))
        if options.fmt not in ("png", "jpg", "webp"):
            raise ValueError("Format must be png, jpg or webp")
        options.rows, options.columns = min(20, max(1, options.rows)), min(20, max(1, options.columns))
        if options.rows * options.columns < 2:
            raise ValueError("Use at least 2 tiles.")
        options.quality = min(100, max(1, options.quality))
        return options


def split_sheet(picture: Image.Image, options: SplitOptions) -> list[tuple[str, Image.Image]]:
    """[(name without extension, tile)] left to right, top to bottom. edges are shared exactly, no pixel is lost."""
    width, height = picture.size
    if width < options.columns or height < options.rows:
        raise ValueError("The picture is too small for that many tiles.")
    tiles = []
    for row in range(options.rows):
        for column in range(options.columns):
            box = (column * width // options.columns, row * height // options.rows,
                   (column + 1) * width // options.columns, (row + 1) * height // options.rows)
            tiles.append((f"tile-r{row + 1}-c{column + 1}", picture.crop(box)))
    return tiles
