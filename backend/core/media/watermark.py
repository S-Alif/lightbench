"""Text watermark renderer.

The text is rendered once per output size into a small alpha patch, then
blended onto frames with numpy. That makes it equally good for single images
and for thousands of video frames.
"""
from __future__ import annotations

import functools
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

import numpy as np
from PIL import Image, ImageDraw, ImageFont

from ...config import FONT_DIR

POSITIONS = {
    "top_left", "top_center", "top_right",
    "center_left", "center", "center_right",
    "bottom_left", "bottom_center", "bottom_right",
}


@dataclass
class WatermarkOptions:
    text: str = ""
    position: str = "bottom_right"
    opacity: float = 0.5            # 0..1
    color: str = "#ffffff"
    size_mode: str = "relative"     # "relative": % of image width | "pixels"
    font_size: float = 3.0          # % of width, or px
    margin_x: float = 6.0           # % of width, or px
    margin_y: float = 8.0           # % of height, or px

    @classmethod
    def from_dict(cls, data: Optional[dict]) -> Optional["WatermarkOptions"]:
        if not data or not str(data.get("text", "")).strip():
            return None
        options = cls()
        for field_name in cls.__dataclass_fields__:
            if field_name in data and data[field_name] is not None:
                setattr(options, field_name, type(getattr(options, field_name))(data[field_name]))
        options.opacity = min(1.0, max(0.0, options.opacity))
        if options.position == "center_center":
            options.position = "center"
        if options.position not in POSITIONS:
            options.position = "bottom_right"
        return options


def _font_candidates():
    yield FONT_DIR / "NotoSans-Bold.ttf"
    yield Path("/usr/share/fonts/truetype/noto/NotoSans-Bold.ttf")
    yield Path("/usr/share/fonts/noto/NotoSans-Bold.ttf")
    yield Path("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf")
    if sys.platform == "win32":
        yield Path("C:/Windows/Fonts/arialbd.ttf")
        yield Path("C:/Windows/Fonts/segoeuib.ttf")
    if sys.platform == "darwin":
        yield Path("/System/Library/Fonts/Supplemental/Arial Bold.ttf")
        yield Path("/Library/Fonts/Arial Bold.ttf")


@functools.lru_cache(maxsize=32)
def _font(size: int) -> ImageFont.FreeTypeFont:
    for font_path in _font_candidates():
        if font_path.exists():
            try:
                return ImageFont.truetype(str(font_path), size)
            except OSError:
                continue
    return ImageFont.load_default(size)  # Pillow >= 10.1


def _hex_rgb(hex_text: str):
    hex_text = hex_text.lstrip("#")
    if len(hex_text) == 3:
        hex_text = "".join(char * 2 for char in hex_text)
    try:
        return tuple(int(hex_text[start:start + 2], 16) for start in (0, 2, 4))
    except ValueError:
        return (255, 255, 255)


@dataclass
class Patch:
    left: int
    top: int
    alpha: np.ndarray   # HxWx1 float32, already multiplied by opacity
    color: np.ndarray   # 1x1x3 float32


def render(size: tuple[int, int], options: WatermarkOptions) -> Patch:
    image_width, image_height = size
    if options.size_mode == "pixels":
        font_size_px, margin_x_px, margin_y_px = options.font_size, options.margin_x, options.margin_y
    else:
        font_size_px, margin_x_px, margin_y_px = image_width * options.font_size / 100, image_width * options.margin_x / 100, image_height * options.margin_y / 100
    font = _font(max(6, round(font_size_px)))

    probe = ImageDraw.Draw(Image.new("L", (1, 1)))
    left, top, right, bottom = probe.textbbox((0, 0), options.text, font=font)
    text_width, text_height = right - left, bottom - top
    mask = Image.new("L", (text_width, text_height), 0)
    # offset by the bbox origin so the glyphs sit exactly inside the patch
    ImageDraw.Draw(mask).text((-left, -top), options.text, font=font, fill=255)

    if options.position == "center":
        row, col = "center", "center"
    else:
        row, col = options.position.split("_")
    patch_left = {"left": margin_x_px, "center": (image_width - text_width) / 2, "right": image_width - text_width - margin_x_px}[col]
    patch_top = {"top": margin_y_px, "center": (image_height - text_height) / 2, "bottom": image_height - text_height - margin_y_px}[row]
    patch_left, patch_top = int(round(patch_left)), int(round(patch_top))
    patch_left, patch_top = min(max(patch_left, 0), max(image_width - text_width, 0)), min(max(patch_top, 0), max(image_height - text_height, 0))

    alpha = np.asarray(mask, dtype=np.float32)[..., None] / 255.0 * options.opacity
    color = np.array(_hex_rgb(options.color), dtype=np.float32).reshape(1, 1, 3)
    return Patch(patch_left, patch_top, alpha, color)


def apply(rgb: np.ndarray, patch: Patch) -> np.ndarray:
    """Blend patch onto an HxWx3 uint8 array (in place when writable) and return it."""
    if not rgb.flags.writeable:
        rgb = rgb.copy()
    patch_height, patch_width = patch.alpha.shape[:2]
    bottom, right = min(patch.top + patch_height, rgb.shape[0]), min(patch.left + patch_width, rgb.shape[1])
    patch_height, patch_width = bottom - patch.top, right - patch.left
    if patch_height <= 0 or patch_width <= 0:
        return rgb
    region = rgb[patch.top:bottom, patch.left:right].astype(np.float32)
    alpha = patch.alpha[:patch_height, :patch_width]
    rgb[patch.top:bottom, patch.left:right] = np.clip(region * (1 - alpha) + patch.color * alpha + 0.5, 0, 255).astype(np.uint8)
    return rgb
