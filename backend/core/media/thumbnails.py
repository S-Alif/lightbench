"""Small preview images for the history/result cards."""
from __future__ import annotations

import subprocess
from pathlib import Path

from PIL import Image, ImageOps

Image.MAX_IMAGE_PIXELS = None
THUMB_W, THUMB_H = 480, 640        # portrait 3:4, matches the cards in the UI


def make_thumb(src: Path, kind: str, dst: Path) -> bool:
    """Write a JPEG thumbnail. Returns False (and never raises) if it fails."""
    try:
        dst.parent.mkdir(parents=True, exist_ok=True)
        if kind == "image":
            with Image.open(src) as image:
                image.draft("RGB", (THUMB_W * 2, THUMB_H * 2))      # fast path for big JPEGs
                image = ImageOps.exif_transpose(image)
                image = image.convert("RGB")
                image.thumbnail((THUMB_W, THUMB_H), Image.LANCZOS)
                image.save(dst, "JPEG", quality=82)
            return True
        from .video import ffmpeg_exe
        for seek_seconds in ("0.5", "0"):                                   # very short clips have no frame at 0.5s
            result = subprocess.run(
                [ffmpeg_exe(), "-v", "error", "-nostdin", "-y", "-ss", seek_seconds, "-i", str(src),
                 "-frames:v", "1", "-vf", f"scale='min({THUMB_W},iw)':-2", "-q:v", "4", str(dst)],
                capture_output=True, timeout=60)
            if result.returncode == 0 and dst.exists() and dst.stat().st_size > 0:
                return True
        return False
    except Exception:  # noqa: BLE001
        return False
