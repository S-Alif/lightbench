"""convert, resize, compress, adjust colours and clean metadata of one picture.

the order is: resize -> colour -> sharpen -> save (with or without metadata).
the colour profile is always kept so colours do not shift. the camera's rotation flag is applied
to the pixels first, so removing metadata never turns a picture sideways.
"""
from __future__ import annotations

import io
from dataclasses import dataclass

import numpy as np
from PIL import Image, ImageFilter, PngImagePlugin

from ..editing.operations import adjust_colour
from .common import MAX_PIXELS, flatten, hex_to_rgb

FORMATS = ("keep", "jpg", "png", "webp")
RESIZE_MODES = ("none", "percent", "fit")
METADATA_MODES = ("remove_all", "remove_location", "keep")
GPS_IFD = 0x8825
EXIF_IFD = 0x8769
SOURCE_FORMAT = {"JPEG": "jpg", "PNG": "png", "WEBP": "webp"}


@dataclass
class ConvertOptions:
    fmt: str = "keep"
    quality: int = 85
    target_kb: int = 0                # 0 = off. jpg and webp only
    resize: str = "none"
    percent: int = 100
    width: int = 0                    # fit: the biggest size allowed, 0 = no limit on that side
    height: int = 0
    metadata: str = "remove_all"
    brightness: int = 0
    contrast: int = 0
    saturation: int = 0
    sharpen: int = 0                  # 0..100
    background: str = "#ffffff"       # replaces transparency when the result is a jpg

    @classmethod
    def from_dict(cls, raw: dict | None) -> "ConvertOptions":
        raw = raw or {}
        options = cls()
        options.fmt = str(raw.get("fmt", options.fmt))
        options.resize = str(raw.get("resize", options.resize))
        options.metadata = str(raw.get("metadata", options.metadata))
        options.background = str(raw.get("background", options.background))
        for key in ("quality", "target_kb", "percent", "width", "height", "brightness", "contrast", "saturation", "sharpen"):
            setattr(options, key, int(round(float(raw.get(key, getattr(options, key))))))
        if options.fmt not in FORMATS:
            raise ValueError("Format must be keep, jpg, png or webp")
        if options.resize not in RESIZE_MODES:
            raise ValueError("Unknown resize mode")
        if options.metadata not in METADATA_MODES:
            raise ValueError("Unknown metadata mode")
        options.quality = min(100, max(1, options.quality))
        options.target_kb = min(100_000, max(0, options.target_kb))
        options.percent = min(400, max(1, options.percent))
        options.width, options.height = min(20000, max(0, options.width)), min(20000, max(0, options.height))
        if options.resize == "fit" and not (options.width or options.height):
            raise ValueError("Enter a width or a height")
        for key in ("brightness", "contrast", "saturation"):
            setattr(options, key, min(100, max(-100, getattr(options, key))))
        options.sharpen = min(100, max(0, options.sharpen))
        hex_to_rgb(options.background)
        return options

    @property
    def changes_pixels(self) -> bool:
        return self.resize != "none" or any((self.brightness, self.contrast, self.saturation, self.sharpen))


@dataclass
class ConvertResult:
    data: bytes
    ext: str
    width: int
    height: int
    note: str = ""


def _target_size(width: int, height: int, options: ConvertOptions) -> tuple[int, int]:
    if options.resize == "percent":
        factor = options.percent / 100
    elif options.resize == "fit":
        factor = min(options.width / width if options.width else 1e9, options.height / height if options.height else 1e9, 1.0)  # only ever shrinks
    else:
        return width, height
    new = (max(1, round(width * factor)), max(1, round(height * factor)))
    if new[0] * new[1] > MAX_PIXELS:
        raise ValueError("The resized picture would be too large (limit 100 megapixels).")
    return new


def _exif_bytes(picture: Image.Image, mode: str) -> bytes | None:
    """the exif block to write, built as a fresh copy so the picture's own tags are never changed."""
    if mode == "remove_all":
        return None
    source = picture.getexif()
    folders = {pointer: dict(source.get_ifd(pointer)) for pointer in (GPS_IFD, EXIF_IFD)}
    if mode == "remove_location":
        folders[GPS_IFD] = {}
    fresh = Image.Exif()
    for tag, value in source.items():
        if tag not in folders:
            fresh[tag] = value
    for pointer, folder in folders.items():  # sub-folders are only written when they are set as values
        if folder:
            fresh[pointer] = folder
    return fresh.tobytes() if len(fresh) else None


def _encode(picture: Image.Image, ext: str, quality: int, exif: bytes | None, icc: bytes | None, text: dict) -> bytes:
    buffer = io.BytesIO()
    extra: dict = {}
    if icc:
        extra["icc_profile"] = icc
    if ext == "png":
        info = None
        if text:
            info = PngImagePlugin.PngInfo()
            for key, value in text.items():
                info.add_text(key, value)
        if exif:
            extra["exif"] = exif
        picture.save(buffer, "PNG", optimize=True, pnginfo=info, **extra)
    elif ext == "webp":
        if exif:
            extra["exif"] = exif
        picture.save(buffer, "WEBP", quality=quality, method=4, **extra)
    else:
        if exif:
            extra["exif"] = exif
        picture.save(buffer, "JPEG", quality=quality, optimize=True, progressive=True, **extra)
    return buffer.getvalue()


def convert_image(picture: Image.Image, source_format: str | None, options: ConvertOptions) -> ConvertResult:
    """picture comes from common.open_image. source_format is Pillow's format name of the original."""
    ext = options.fmt if options.fmt != "keep" else SOURCE_FORMAT.get(source_format or "", "png")
    note = ""
    icc = picture.info.get("icc_profile")
    exif = _exif_bytes(picture, options.metadata)
    text = {} if options.metadata != "keep" else {key: value for key, value in (getattr(picture, "text", None) or {}).items() if isinstance(value, str)}
    if picture.mode == "CMYK":
        icc = None  # the profile describes cmyk, the converted pixels are rgb

    has_alpha = picture.mode in ("RGBA", "LA", "PA") or "transparency" in picture.info
    working = picture.convert("RGBA") if has_alpha and ext != "jpg" else None
    if ext == "jpg":
        working = flatten(picture, hex_to_rgb(options.background))
    elif working is None:
        working = picture.convert("RGB")

    size = _target_size(*working.size, options)
    if size != working.size:
        working = working.resize(size, Image.LANCZOS)
    if any((options.brightness, options.contrast, options.saturation)):
        rgb = np.asarray(working.convert("RGB"))
        adjusted = Image.fromarray(adjust_colour(rgb, {"brightness": options.brightness, "contrast": options.contrast, "saturation": options.saturation}))
        if working.mode == "RGBA":
            adjusted.putalpha(working.getchannel("A"))
        working = adjusted
    if options.sharpen:
        radius = max(0.8, max(working.size) / 2000)
        sharp = working.convert("RGB").filter(ImageFilter.UnsharpMask(radius=radius, percent=options.sharpen * 2, threshold=2))
        if working.mode == "RGBA":
            sharp.putalpha(working.getchannel("A"))
        working = sharp

    if options.target_kb and ext in ("jpg", "webp"):
        limit = options.target_kb * 1000
        low, high, best = 5, 95, None
        while low <= high:  # biggest quality that still fits
            middle = (low + high) // 2
            attempt = _encode(working, ext, middle, exif, icc, text)
            if len(attempt) <= limit:
                best, low = attempt, middle + 1
            else:
                high = middle - 1
        if best is None:
            best = _encode(working, ext, 5, exif, icc, text)
            note = f"Could not get under {options.target_kb} KB without making it smaller."
        data = best
    else:
        if options.target_kb:
            note = "Target size works for JPG and WebP only."
        data = _encode(working, ext, options.quality, exif, icc, text)
    return ConvertResult(data=data, ext=ext, width=working.width, height=working.height, note=note)
