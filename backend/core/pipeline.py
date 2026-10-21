"""Upscale -> watermark -> encode, for one image or one video.

Everything stays in memory between stages, so an image is encoded exactly
once (the old two-script flow re-compressed the JPEG after watermarking).
torch is imported lazily, so watermark-only jobs work even without it.
"""
from __future__ import annotations

import threading
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Callable, Optional

import numpy as np
from PIL import Image, ImageOps
from PIL.PngImagePlugin import PngInfo

from .editing.operations import apply_edit
from .errors import Cancelled
from .media import watermark as watermark_module
from .models import registry

Image.MAX_IMAGE_PIXELS = None   # local, trusted files: 4x upscales easily exceed the default limit

Progress = Callable[[float, str], None]


@dataclass
class JobOptions:
    model: str = "auto"             # "auto" (use profile) or a file name inside models/
    profile: str = "photo"          # "photo" | "art"  (only used when model == "auto")
    scale: int = 2                  # 1 = no upscaling
    fmt: str = "jpg"                # images: jpg | png | webp   (video is always mp4)
    quality: int = 95
    keep_metadata: bool = False
    tile: int = 512
    fp32: bool = False
    video_crf: int = 18
    video_preset: str = "medium"
    watermark: Optional[watermark_module.WatermarkOptions] = field(default=None)

    @classmethod
    def from_dict(cls, data: dict) -> "JobOptions":
        options = cls()
        options.model = str(data.get("model") or "auto")
        if options.model != "auto":
            registry.safe_model_name(options.model)
            if not registry.weights_path(options.model).is_file():
                raise ValueError(f"Model file not found in the models folder: {options.model}")
        options.profile = data.get("profile", options.profile)
        options.scale = int(data.get("scale", options.scale))
        options.fmt = data.get("fmt", options.fmt)
        options.quality = int(data.get("quality", options.quality))
        options.keep_metadata = bool(data.get("keep_metadata", options.keep_metadata))
        options.tile = int(data.get("tile", options.tile))
        options.fp32 = bool(data.get("fp32", options.fp32))
        options.video_crf = int(data.get("video_crf", options.video_crf))
        options.video_preset = data.get("video_preset", options.video_preset)
        options.watermark = watermark_module.WatermarkOptions.from_dict(data.get("watermark"))
        if options.profile not in ("photo", "art"):
            raise ValueError("profile must be 'photo' or 'art'")
        if options.scale not in (1, 2, 3, 4):
            raise ValueError("scale must be 1, 2, 3 or 4")
        if options.fmt not in ("jpg", "png", "webp"):
            raise ValueError("fmt must be jpg, png or webp")
        if options.video_preset not in ("ultrafast", "veryfast", "fast", "medium", "slow", "slower"):
            options.video_preset = "medium"
        options.quality = min(100, max(1, options.quality))
        options.video_crf = min(40, max(0, options.video_crf))
        options.tile = min(2048, max(0, options.tile))
        return options

    def to_dict(self) -> dict:
        return asdict(self)


def _get_upscaler(options: JobOptions, progress: Progress):
    from .upscaler import Upscaler
    file = registry.resolve(options.profile, options.scale, options.model)
    if not registry.weights_present(file):
        progress(0.0, "Downloading model (first run only)…")
    return Upscaler.get(
        file, fp32=options.fp32,
        on_download=lambda fraction: progress(0.0, f"Downloading model… {int(fraction * 100)}%"))


def output_name(stem: str, options: JobOptions, video: bool = False) -> str:
    ext = "mp4" if video else options.fmt
    tag = f"-{options.scale}x" if options.scale > 1 else ("-wm" if options.watermark else "")
    return f"{stem}{tag}.{ext}"


# ------------------------------------------------------------------ images --
def _save(img: Image.Image, path: Path, options: JobOptions, exif, icc, text) -> None:
    save_kwargs: dict = {}
    if icc:
        save_kwargs["icc_profile"] = icc
    if options.keep_metadata and exif:
        save_kwargs["exif"] = exif
    if options.fmt == "jpg":
        img.save(path, "JPEG", quality=options.quality, optimize=True, **save_kwargs)
    elif options.fmt == "webp":
        img.save(path, "WEBP", quality=options.quality, method=4, **save_kwargs)
    else:
        if options.keep_metadata and text:
            info = PngInfo()
            for key, value in text.items():
                info.add_text(str(key), str(value))
            save_kwargs["pnginfo"] = info
        img.save(path, "PNG", compress_level=6, **save_kwargs)


def process_image(src: str, dst: Path, options: JobOptions, progress: Progress,
                  cancel: Optional[threading.Event] = None, edit: Optional[dict] = None) -> dict:
    with Image.open(src) as source_image:
        source_image = ImageOps.exif_transpose(source_image)          # same orientation handling as cv2.imread
        exif = source_image.info.get("exif")
        icc = source_image.info.get("icc_profile")
        text = dict(getattr(source_image, "text", {}) or {}) if source_image.format == "PNG" else {}
        rgb = np.asarray(source_image.convert("RGB"))

    # crop and rotate first, so nothing gets upscaled that is cut away anyway
    rgb = apply_edit(rgb, edit)

    if options.scale > 1:
        upscaler = _get_upscaler(options, progress)
        progress(0.01, f"Upscaling {options.scale}x on {upscaler.device.type.upper()}")
        rgb = upscaler.enhance(rgb, options.scale, tile=options.tile,
                         progress=lambda fraction: progress(0.02 + 0.93 * fraction, f"Upscaling {options.scale}x"),
                         cancel=cancel)
    else:
        rgb = rgb.copy()

    if cancel is not None and cancel.is_set():
        raise Cancelled()
    if options.watermark:
        progress(0.96, "Adding watermark")
        height, width = rgb.shape[:2]
        rgb = watermark_module.apply(rgb, watermark_module.render((width, height), options.watermark))
    progress(0.98, "Saving")
    _save(Image.fromarray(rgb), dst, options, exif, icc, text)
    progress(1.0, "Done")
    return {"w": int(rgb.shape[1]), "h": int(rgb.shape[0])}


# ------------------------------------------------------------------- video --
def process_video(src: str, dst: Path, options: JobOptions, progress: Progress,
                  cancel: Optional[threading.Event] = None) -> dict:
    from .media import video

    upscaler = _get_upscaler(options, progress) if options.scale > 1 else None
    patch_cache: dict = {}

    def per_frame(frame: np.ndarray) -> np.ndarray:
        if upscaler is not None:
            frame = upscaler.enhance(frame, options.scale, tile=options.tile, cancel=cancel)
        if options.watermark:
            height, width = frame.shape[:2]
            if "p" not in patch_cache:                    # render once, reuse for every frame
                patch_cache["p"] = watermark_module.render((width, height), options.watermark)
            frame = watermark_module.apply(frame, patch_cache["p"])
        return frame

    video.process_video(str(src), str(dst), per_frame, crf=options.video_crf, preset=options.video_preset,
                        keep_metadata=options.keep_metadata, progress=progress, cancel=cancel)
    progress(1.0, "Done")
    info = video.probe(str(dst))
    return {"w": info["w"], "h": info["h"], "duration": info["duration"]}
