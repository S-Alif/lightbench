"""loading pictures for the tools."""
from __future__ import annotations

import io

from PIL import Image, ImageOps

MAX_PIXELS = 100_000_000
SUPPORTED_SAVE = {"jpg": "JPEG", "png": "PNG", "webp": "WEBP"}


def open_image(data: bytes) -> Image.Image:
    """decodes the picture (first frame only) and applies the camera's rotation flag, so the pixels
    are the right way up and the flag is no longer needed. raises ValueError / OSError for bad files."""
    Image.MAX_IMAGE_PIXELS = None  # checked below instead
    with Image.open(io.BytesIO(data)) as opened:
        if opened.width * opened.height > MAX_PIXELS:
            raise ValueError("Image is too large (limit 100 megapixels).")
        opened.load()
        picture = ImageOps.exif_transpose(opened)
        picture.info.update({key: value for key, value in opened.info.items() if key not in picture.info})
        picture.info["source_format"] = opened.format  # JPEG, PNG, ...
        return picture


def hex_to_rgb(value: str) -> tuple[int, int, int]:
    if not isinstance(value, str) or len(value) != 7 or value[0] != "#":
        raise ValueError("Colours look like #rrggbb")
    return tuple(int(value[index:index + 2], 16) for index in (1, 3, 5))  # type: ignore[return-value]


def flatten(picture: Image.Image, colour: tuple[int, int, int]) -> Image.Image:
    """RGB version of a picture; transparent areas become the given colour."""
    if picture.mode in ("RGBA", "LA", "PA") or "transparency" in picture.info:
        rgba = picture.convert("RGBA")
        base = Image.new("RGBA", rgba.size, colour + (255,))
        return Image.alpha_composite(base, rgba).convert("RGB")
    return picture.convert("RGB")
