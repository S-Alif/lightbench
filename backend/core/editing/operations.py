"""flip, rotate, straighten, crop and colour adjustments for images, applied before upscaling.

An edit is a small dict, the same shape the frontend sends and job.json stores:

    {"flip": true, "rotate": 90, "straighten": -2.5, "adjust": {"brightness": 10, "contrast": 0, "saturation": -20}, "crop": {"x": 0.1, "y": 0.2, "width": 0.5, "height": 0.6}}

flip mirrors the image left to right, applied first. (a top to bottom mirror is the same as
flip plus a 180 degree turn, so one flag is enough.)
rotate is clockwise degrees (0, 90, 180 or 270), applied second.
straighten is a small extra turn in clockwise degrees (-45 to 45) to level a tilted horizon. The
image is then cut to the biggest rectangle of the same shape that has no empty corners, applied third.
crop is a box in fractions (0..1) of the flipped, rotated and straightened image, so the preview in the
browser and the real image agree no matter what size the file is.
adjust changes brightness, contrast and saturation, each from -100 to 100 (0 = untouched), applied last.
The maths is the same as the CSS filters the editor uses for its live preview, so what you see is what you get.
"""
from __future__ import annotations

from typing import Optional

import math

import numpy as np
from PIL import Image

ROTATIONS = (0, 90, 180, 270)
MAX_STRAIGHTEN = 45.0
ADJUST_KEYS = ("brightness", "contrast", "saturation")
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

    straighten = round(float(edit.get("straighten") or 0), 1)
    if abs(straighten) > MAX_STRAIGHTEN:
        raise ValueError(f"straighten must be between -{MAX_STRAIGHTEN:g} and {MAX_STRAIGHTEN:g} degrees")

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

    adjust = edit.get("adjust")
    if adjust is not None:
        if not isinstance(adjust, dict):
            raise ValueError("adjust must be an object")
        unknown = set(adjust) - set(ADJUST_KEYS)
        if unknown:
            raise ValueError(f"unknown adjustment: {', '.join(sorted(unknown))}")
        adjust = {key: int(round(float(adjust.get(key) or 0))) for key in ADJUST_KEYS}
        if any(abs(value) > 100 for value in adjust.values()):
            raise ValueError("each adjustment must be between -100 and 100")
        if not any(adjust.values()):
            adjust = None

    if not flip and rotate == 0 and straighten == 0 and crop is None and adjust is None:
        return None
    return {"flip": flip, "rotate": rotate, "straighten": straighten, "crop": crop, "adjust": adjust}


def flip_horizontal(rgb: np.ndarray) -> np.ndarray:
    return rgb[:, ::-1]


def rotate_clockwise(rgb: np.ndarray, degrees: int) -> np.ndarray:
    # np.rot90 turns counter-clockwise, so a clockwise turn is a negative count
    return np.rot90(rgb, k=-(degrees // 90))


def straightened_size(width: int, height: int, degrees: float) -> tuple[int, int]:
    """size of the biggest same-shaped rectangle that fits inside the image after turning it by degrees."""
    angle = math.radians(abs(degrees))
    longer_over_shorter = max(width, height) / min(width, height)
    scale = 1 / (math.cos(angle) + math.sin(angle) * longer_over_shorter)
    return max(1, math.floor(width * scale)), max(1, math.floor(height * scale))


def straighten(rgb: np.ndarray, degrees: float) -> np.ndarray:
    """turn clockwise by degrees around the centre, then keep the middle part that has no empty corners."""
    height, width = rgb.shape[:2]
    keep_width, keep_height = straightened_size(width, height, degrees)
    # PIL turns counter-clockwise, so a clockwise turn is a negative angle
    turned = np.asarray(Image.fromarray(rgb).rotate(-degrees, resample=Image.BICUBIC, expand=False))
    left = (width - keep_width) // 2
    top = (height - keep_height) // 2
    return turned[top:top + keep_height, left:left + keep_width]


def adjust_colour(rgb: np.ndarray, adjust: dict) -> np.ndarray:
    """brightness, then contrast, then saturation: the same formulas as the CSS filters used for the preview."""
    pixels = rgb.astype(np.float32) / 255.0
    brightness = 1 + adjust["brightness"] / 100
    contrast = 1 + adjust["contrast"] / 100
    saturation = 1 + adjust["saturation"] / 100
    if adjust["brightness"]:
        pixels = np.clip(pixels * brightness, 0, 1)
    if adjust["contrast"]:
        pixels = np.clip((pixels - 0.5) * contrast + 0.5, 0, 1)
    if adjust["saturation"]:
        matrix = np.array([
            [0.213 + 0.787 * saturation, 0.715 - 0.715 * saturation, 0.072 - 0.072 * saturation],
            [0.213 - 0.213 * saturation, 0.715 + 0.285 * saturation, 0.072 - 0.072 * saturation],
            [0.213 - 0.213 * saturation, 0.715 - 0.715 * saturation, 0.072 + 0.928 * saturation],
        ], dtype=np.float32)
        pixels = np.clip(pixels @ matrix.T, 0, 1)
    return np.rint(pixels * 255).astype(np.uint8)


def crop_box(rgb: np.ndarray, crop: dict) -> np.ndarray:
    height, width = rgb.shape[:2]
    left = min(max(round(crop["x"] * width), 0), width - 1)
    top = min(max(round(crop["y"] * height), 0), height - 1)
    right = min(max(round((crop["x"] + crop["width"]) * width), left + 1), width)
    bottom = min(max(round((crop["y"] + crop["height"]) * height), top + 1), height)
    return rgb[top:bottom, left:right]


def apply_edit(rgb: np.ndarray, edit: Optional[dict]) -> np.ndarray:
    """flip, rotate, straighten, crop, then colour. returns a new contiguous array."""
    edit = validate_edit(edit)
    if edit is None:
        return rgb
    if edit["flip"]:
        rgb = flip_horizontal(rgb)
    if edit["rotate"]:
        rgb = rotate_clockwise(rgb, edit["rotate"])
    if edit["straighten"]:
        rgb = straighten(rgb, edit["straighten"])
    if edit["crop"]:
        rgb = crop_box(rgb, edit["crop"])
    if edit["adjust"]:
        rgb = adjust_colour(rgb, edit["adjust"])
    return np.ascontiguousarray(rgb)
