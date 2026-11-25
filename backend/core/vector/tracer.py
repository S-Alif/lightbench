"""turn a raster image into an svg with vtracer. no web code in here."""
from __future__ import annotations

import io
import re
from dataclasses import dataclass, replace

import numpy as np
from PIL import Image, ImageFilter, ImageOps

from . import preprocess


class VectorizerMissing(RuntimeError):
    """raised when the vtracer package is not installed."""


def _clamp(value, low, high, cast=float):
    return max(low, min(high, cast(value)))


@dataclass
class TraceOptions:
    colormode: str = "color"          # "color" or "binary" (black and white)
    colors: int = 8                   # 2..32, size of the flat palette the image is reduced to
    smoothing: float = 1.0            # 0..3, blur before tracing, smoother edges but softer corners
    merge_small: int = 6              # 0..40, tiny colour patches (side length in px at 1400 wide) merge into their surroundings, 0 is off
    remove_specks: int = 4            # 0..64, ignore blobs smaller than this many pixels
    corners: int = 60                 # 0..180, angle above which a point counts as a sharp corner
    curves: str = "spline"            # "spline" (smooth), "polygon" (straight lines) or "pixel"
    layering: str = "stacked"         # "stacked" (shapes overlap, smaller file) or "cutout" (no overlap)
    detail: float = 4.0               # 3.5..10, smallest segment length, higher means simpler shapes
    max_side: int = 2048              # larger images are shrunk to this before tracing
    keep_transparency: bool = True    # png files with transparent areas keep them
    remove_background: bool = True    # a solid background colour is left out of the svg
    remove_enclosed: bool = True      # ...including the parts inside letters and holes

    @classmethod
    def from_dict(cls, raw: dict | None) -> "TraceOptions":
        raw = raw or {}
        defaults = cls()
        colormode = raw.get("colormode", defaults.colormode)
        curves = raw.get("curves", defaults.curves)
        layering = raw.get("layering", defaults.layering)
        if colormode not in ("color", "binary"):
            raise ValueError("colormode must be 'color' or 'binary'")
        if curves not in ("spline", "polygon", "pixel"):
            raise ValueError("curves must be 'spline', 'polygon' or 'pixel'")
        if layering not in ("stacked", "cutout"):
            raise ValueError("layering must be 'stacked' or 'cutout'")
        return cls(
            colormode=colormode,
            colors=_clamp(raw.get("colors", defaults.colors), 2, 32, int),
            smoothing=round(_clamp(raw.get("smoothing", defaults.smoothing), 0, 3), 2),
            merge_small=_clamp(raw.get("merge_small", defaults.merge_small), 0, 40, int),
            remove_specks=_clamp(raw.get("remove_specks", defaults.remove_specks), 0, 64, int),
            corners=_clamp(raw.get("corners", defaults.corners), 0, 180, int),
            curves=curves,
            layering=layering,
            detail=round(_clamp(raw.get("detail", defaults.detail), 3.5, 10), 2),
            max_side=_clamp(raw.get("max_side", defaults.max_side), 256, 4096, int),
            keep_transparency=bool(raw.get("keep_transparency", defaults.keep_transparency)),
            remove_background=bool(raw.get("remove_background", defaults.remove_background)),
            remove_enclosed=bool(raw.get("remove_enclosed", defaults.remove_enclosed)),
        )


def _prepare(image_bytes: bytes, options: TraceOptions) -> dict:
    """decode and clean the image. returns {png, size, background, dark_on_light}."""
    with Image.open(io.BytesIO(image_bytes)) as opened:
        image = ImageOps.exif_transpose(opened)
        has_alpha = image.mode in ("RGBA", "LA", "PA") or "transparency" in image.info
        image = image.convert("RGBA")
    pixels = np.asarray(image)
    rgb, alpha = pixels[..., :3].copy(), pixels[..., 3]
    background = None
    transparent = alpha < 128
    if has_alpha and options.keep_transparency and transparent.any():
        # transparent areas become the background; paint them with a colour the artwork does not use
        background = preprocess.pick_marker_colour(rgb, ~transparent)
        rgb[transparent] = background
    else:
        # flatten any transparency onto white
        weight = (alpha.astype(np.float32) / 255.0)[..., None]
        rgb = np.rint(rgb * weight + 255.0 * (1.0 - weight)).astype(np.uint8)

    clean = Image.fromarray(rgb)
    # work at a good size: small images are enlarged so curves are smooth, huge ones shrunk
    longest = max(clean.size)
    target = min(options.max_side, 1400) if longest < 1400 else min(longest, options.max_side)
    if target != longest:
        ratio = target / longest
        clean = clean.resize((max(1, round(clean.width * ratio)), max(1, round(clean.height * ratio))), Image.LANCZOS)
    clean = clean.filter(ImageFilter.MedianFilter(3))  # jpeg noise
    if options.smoothing > 0:
        clean = clean.filter(ImageFilter.GaussianBlur(options.smoothing * clean.width / 1400 + 0.4))
    rgb = np.asarray(clean)
    out_width = clean.width

    if background is None and options.remove_background:
        background = preprocess.detect_background(rgb)

    design_colour = None
    if options.colormode == "binary":
        grey = np.asarray(clean.convert("L"))
        cut = preprocess.otsu_threshold(grey)
        if background is not None:
            back_grey = int(round(0.299 * background[0] + 0.587 * background[1] + 0.114 * background[2]))
            foreground = grey <= cut if back_grey > cut else grey > cut
        else:
            foreground = grey <= cut
        if foreground.any() and foreground.mean() < 0.9:
            mean_colour = rgb[foreground].mean(axis=0)
            # a design lighter than its background keeps its colour instead of turning black
            if background is not None and float(mean_colour @ [0.299, 0.587, 0.114]) > back_grey:
                design_colour = tuple(int(channel) for channel in np.rint(mean_colour))
        mask = foreground.astype(np.uint8)
        if options.merge_small > 0:
            mask = preprocess.merge_small_patches(mask, round((options.merge_small * out_width / 1400) ** 2))
        out = Image.fromarray(np.where(mask > 0, 0, 255).astype(np.uint8)).convert("RGB")
    else:
        palette = preprocess.build_palette(rgb, options.colors, background)
        min_area = round((options.merge_small * out_width / 1400) ** 2)
        out = Image.fromarray(preprocess.snap_to_palette(rgb, palette, background, min_patch_area=min_area))

    buffer = io.BytesIO()
    out.save(buffer, format="PNG")
    return {"png": buffer.getvalue(), "size": out.size, "background": background, "design_colour": design_colour}


def _hex(colour: tuple[int, int, int]) -> str:
    return "#%02x%02x%02x" % colour


_PATH_TAG = re.compile(r"<path\b[^>]*>")
_FILL = re.compile(r'fill="(#[0-9a-fA-F]{6})"')
_NUMBER = re.compile(r"-?\d+(?:\.\d+)?")
_TRANSLATE = re.compile(r"translate\(\s*(-?[\d.]+)[ ,]+(-?[\d.]+)\s*\)")


def _near(hex_a: str, hex_b: str, tolerance: int = 6) -> bool:
    return all(abs(int(hex_a[i:i + 2], 16) - int(hex_b[i:i + 2], 16)) <= tolerance for i in (1, 3, 5))


def _covers_most_of_image(tag: str, width: int, height: int) -> bool:
    d_match = re.search(r'\bd="([^"]*)"', tag)
    if not d_match:
        return False
    numbers = [float(value) for value in _NUMBER.findall(d_match.group(1))]
    if len(numbers) < 4:
        return False
    shift = _TRANSLATE.search(tag)
    shift_x, shift_y = (float(shift.group(1)), float(shift.group(2))) if shift else (0.0, 0.0)
    xs, ys = numbers[0::2], numbers[1::2]
    return (max(xs) - min(xs) >= 0.85 * width) and (max(ys) - min(ys) >= 0.85 * height) and shift_x <= 0.1 * width and shift_y <= 0.1 * height


def strip_background(svg: str, background: tuple[int, int, int], width: int, height: int, enclosed_too: bool) -> str:
    """removes the background-coloured shapes (all of them, or only the big outer one)."""
    background_hex = _hex(background)

    def decide(match):
        tag = match.group(0)
        fill = _FILL.search(tag)
        if not fill or not _near(fill.group(1), background_hex):
            return tag
        if enclosed_too or _covers_most_of_image(tag, width, height):
            return ""
        return tag

    return _PATH_TAG.sub(decide, svg)


def _vtracer_convert(png_bytes: bytes, options: TraceOptions) -> str:
    try:
        import vtracer
    except ImportError as import_error:
        raise VectorizerMissing("The vectorizer package is not installed. Run:  pip install vtracer") from import_error
    return vtracer.convert_raw_image_to_svg(
        png_bytes,
        img_format="png",
        colormode=options.colormode,
        hierarchical=options.layering,
        mode="none" if options.curves == "pixel" else options.curves,
        filter_speckle=options.remove_specks,
        # the image is already reduced to flat colours, so vtracer must not merge them again
        color_precision=8,
        layer_difference=4,
        corner_threshold=options.corners,
        length_threshold=options.detail,
        max_iterations=10,
        splice_threshold=45,
        path_precision=2,
    )


def trace_image(image_bytes: bytes, options: TraceOptions, convert=_vtracer_convert) -> dict:
    """returns {svg, width, height, paths, bytes, background}. `convert` can be swapped in tests."""
    prepared = _prepare(image_bytes, options)
    width, height = prepared["size"]
    background = prepared["background"] if options.remove_background else None
    removing = background is not None and options.colormode == "color"
    # holes only come out right when shapes do not overlap
    effective = replace(options, layering="cutout") if removing and options.remove_enclosed else options
    svg = convert(prepared["png"], effective)
    if removing:
        svg = strip_background(svg, background, width, height, options.remove_enclosed)
    if prepared["design_colour"] is not None:
        svg = re.sub(r'fill="#000000"', f'fill="{_hex(prepared["design_colour"])}"', svg)
    if "viewBox" not in svg:
        svg = re.sub(r"<svg\b", f'<svg viewBox="0 0 {width} {height}"', svg, count=1)
    return {
        "svg": svg,
        "width": width,
        "height": height,
        "paths": svg.count("<path"),
        "bytes": len(svg.encode("utf-8")),
        "background": _hex(background) if removing else None,
    }
