"""what is hidden inside an image file: camera, date, GPS location, generation prompts, colour profile.

Only reads the file header and tags, the picture itself is never decoded.
"""
from __future__ import annotations

from pathlib import Path

from PIL import ExifTags, Image

EXIF_IFD = 0x8769
GPS_IFD = 0x8825
# (exif tag name, label shown to the person)
EXIF_FIELDS = [
    ("Make", "Camera make"), ("Model", "Camera model"), ("LensModel", "Lens"),
    ("DateTimeOriginal", "Taken"), ("DateTime", "Modified"), ("Software", "Software"),
    ("ExposureTime", "Exposure time"), ("FNumber", "Aperture"), ("ISOSpeedRatings", "ISO"),
    ("FocalLength", "Focal length"), ("Artist", "Artist"), ("Copyright", "Copyright"),
]
# text chunks that AI image tools write into PNG files
PROMPT_KEYS = {"parameters", "prompt", "workflow", "sd-metadata", "invokeai_metadata", "dream", "comment"}
MAX_TEXT = 400


def _text(value) -> str:
    if isinstance(value, bytes):
        value = value.decode("utf-8", "replace")
    text = str(value).strip().replace("\x00", "")
    return text if len(text) <= MAX_TEXT else text[:MAX_TEXT] + "…"


def _degrees(parts, reference) -> float | None:
    try:
        degrees, minutes, seconds = (float(part) for part in parts)
    except (TypeError, ValueError):
        return None
    value = degrees + minutes / 60 + seconds / 3600
    return -value if str(reference).upper() in ("S", "W") else value


def read_gps(exif: Image.Exif) -> tuple[float, float] | None:
    gps = exif.get_ifd(GPS_IFD)
    if not gps:
        return None
    latitude = _degrees(gps.get(2), gps.get(1))
    longitude = _degrees(gps.get(4), gps.get(3))
    if latitude is None or longitude is None:
        return None
    return latitude, longitude


def read_metadata(path: Path) -> dict:
    fields: list[dict] = []
    warnings: list[str] = []
    with Image.open(path) as image:
        summary = {"format": image.format, "width": image.width, "height": image.height, "mode": image.mode,
                   "bytes": Path(path).stat().st_size}
        fields.append({"label": "Format", "value": f"{image.format} · {image.width}×{image.height} px"})

        exif = image.getexif()
        merged = {**dict(exif), **exif.get_ifd(EXIF_IFD)}
        by_name = {ExifTags.TAGS.get(tag, str(tag)): value for tag, value in merged.items()}
        for name, label in EXIF_FIELDS:
            if by_name.get(name) not in (None, ""):
                fields.append({"label": label, "value": _text(by_name[name])})

        gps = read_gps(exif)
        if gps:
            fields.append({"label": "GPS location", "value": f"{gps[0]:.5f}, {gps[1]:.5f}"})
            warnings.append("Contains the GPS location where the photo was taken")

        info = image.info
        prompts = [key for key in info if str(key).lower() in PROMPT_KEYS and isinstance(info[key], (str, bytes))]
        for key in prompts:
            fields.append({"label": f"Text “{key}”", "value": _text(info[key])})
        if any(str(key).lower() in PROMPT_KEYS - {"comment"} for key in prompts):
            warnings.append("Contains the text prompt or settings used to generate the image")
        if info.get("xmp") or info.get("XML:com.adobe.xmp"):
            fields.append({"label": "XMP data", "value": "present"})
        if image.info.get("icc_profile"):
            fields.append({"label": "Colour profile", "value": "embedded"})

    return {"summary": summary, "fields": fields, "warnings": warnings,
            "has_gps": bool(gps), "has_prompt": any("prompt" in warning for warning in warnings)}
