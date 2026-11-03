"""flip, rotate and crop for images, applied before upscaling.

An edit is a small dict, the same shape the frontend sends and job.json stores:

    {"flip": true, "rotate": 90, "crop": {"x": 0.1, "y": 0.2, "width": 0.5, "height": 0.6}}

flip mirrors the image left to right, applied first. (a top to bottom mirror is the same as
flip plus a 180 degree turn, so one flag is enough.)
rotate is clockwise degrees (0, 90, 180 or 270), applied second.
crop is a box in fractions (0..1) of the flipped and rotated image, so the preview in the
browser and the real image agree no matter what size the file is.
"""
from __future__ import annotations

from typing import Optional

import numpy as np

ROTATIONS = (0, 90, 180, 270)
CROP_KEYS = ("x", "y", "width", "height")
EPSILON = 1e-6


def validate_edit(edit: Optional[dict]) -> Optional[dict]:
    """returns a cleaned edit, or None when it changes nothing. raises ValueError for bad input."""
    if not edit:
        return None
    if not isinstance(edit, dict):
        raise ValueError("An edit must be an object")

    flip = bool(edit.get("flip"))
    rotate = int(edit.get("rotate") or 0) % 360
    if rotate not in ROTATIONS:
        raise ValueError("rotate must be 0, 90, 180 or 270")

    crop = edit.get("crop")
    if crop is not None:
        if not isinstance(crop, dict) or any(key not in crop for key in CROP_KEYS):
            raise ValueError("crop needs x, y, width and height")
        crop = {key: float(crop[key]) for key in CROP_KEYS}
        if crop["x"] < -EPSILON or crop["y"] < -EPSILON:
            raise ValueError("crop starts outside the image")
        if crop["width"] <= 0 or crop["height"] <= 0:
            raise ValueError("crop must have a size")
        if crop["x"] + crop["width"] > 1 + EPSILON or crop["y"] + crop["height"] > 1 + EPSILON:
            raise ValueError("crop goes outside the image")
        # a crop of the whole image is no crop at all
        covers_everything = (crop["x"] <= EPSILON and crop["y"] <= EPSILON
                             and crop["width"] >= 1 - EPSILON and crop["height"] >= 1 - EPSILON)
        if covers_everything:
            crop = None

    if not flip and rotate == 0 and crop is None:
        return None
    return {"flip": flip, "rotate": rotate, "crop": crop}


def flip_horizontal(rgb: np.ndarray) -> np.ndarray:
    return rgb[:, ::-1]


def rotate_clockwise(rgb: np.ndarray, degrees: int) -> np.ndarray:
    # np.rot90 turns counter-clockwise, so a clockwise turn is a negative count
    return np.rot90(rgb, k=-(degrees // 90))


def crop_box(rgb: np.ndarray, crop: dict) -> np.ndarray:
    height, width = rgb.shape[:2]
    left = min(max(round(crop["x"] * width), 0), width - 1)
    top = min(max(round(crop["y"] * height), 0), height - 1)
    right = min(max(round((crop["x"] + crop["width"]) * width), left + 1), width)
    bottom = min(max(round((crop["y"] + crop["height"]) * height), top + 1), height)
    return rgb[top:bottom, left:right]


def apply_edit(rgb: np.ndarray, edit: Optional[dict]) -> np.ndarray:
    """flip, then rotate, then crop. returns a new contiguous array."""
    edit = validate_edit(edit)
    if edit is None:
        return rgb
    if edit["flip"]:
        rgb = flip_horizontal(rgb)
    if edit["rotate"]:
        rgb = rotate_clockwise(rgb, edit["rotate"])
    if edit["crop"]:
        rgb = crop_box(rgb, edit["crop"])
    return np.ascontiguousarray(rgb)
