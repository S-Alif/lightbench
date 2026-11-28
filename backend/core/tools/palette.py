"""the main colours of a picture."""
from __future__ import annotations

import numpy as np
from PIL import Image

MIN_COLOURS, MAX_COLOURS = 2, 12


def extract_palette(picture: Image.Image, count: int = 6) -> list[dict]:
    """[{hex, share}] biggest first. transparent pixels are ignored."""
    count = min(MAX_COLOURS, max(MIN_COLOURS, int(count)))
    small = picture.convert("RGBA")
    small.thumbnail((200, 200))
    pixels = np.asarray(small).reshape(-1, 4)
    solid = pixels[pixels[:, 3] > 128][:, :3]
    if not len(solid):
        return []
    strip = Image.fromarray(solid.reshape(1, -1, 3).astype(np.uint8))
    reduced = strip.quantize(colors=count, method=Image.Quantize.MEDIANCUT, dither=Image.Dither.NONE)
    palette = reduced.getpalette() or []
    found = sorted(reduced.getcolors() or [], reverse=True)  # [(pixels, index)]
    total = sum(pixels_in for pixels_in, _ in found) or 1
    return [{"hex": "#%02x%02x%02x" % tuple(palette[index * 3:index * 3 + 3]), "share": round(pixels_in / total, 4)}
            for pixels_in, index in found]
