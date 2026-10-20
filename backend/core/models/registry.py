"""Pure-python model registry: paths, built-in weights, download, architecture detection.
No torch import here, so the web layer can list models even if PyTorch isn't installed."""
from __future__ import annotations

import math
import os
import re
import urllib.request
from pathlib import Path
from typing import Callable, Optional

from ...config import MODELS_DIR

MODEL_EXT = (".pth", ".pt")

# ---------------------------------------------------------------- registry --
_BASE = "https://github.com/xinntao/Real-ESRGAN/releases/download"
BUILTIN = {
    "RealESRGAN_x2plus.pth": dict(
        label="Real-ESRGAN x2plus", note="Photo · native 2×", arch="rrdb", net_scale=2, num_block=23,
        url=f"{_BASE}/v0.2.1/RealESRGAN_x2plus.pth", min_bytes=60_000_000),
    "RealESRGAN_x4plus.pth": dict(
        label="Real-ESRGAN x4plus", note="Photo · native 4×", arch="rrdb", net_scale=4, num_block=23,
        url=f"{_BASE}/v0.1.0/RealESRGAN_x4plus.pth", min_bytes=60_000_000),
    "RealESRGAN_x4plus_anime_6B.pth": dict(
        label="Real-ESRGAN x4plus anime 6B", note="Art · native 4×", arch="rrdb", net_scale=4, num_block=6,
        url=f"{_BASE}/v0.2.2.4/RealESRGAN_x4plus_anime_6B.pth", min_bytes=15_000_000),
}

# profile -> {requested output scale -> weights file}. Same mapping as the
# original scripts: 3x uses the 4x weights and is resized down to 3x.
PROFILES = {
    "photo": {2: "RealESRGAN_x2plus.pth", 3: "RealESRGAN_x4plus.pth", 4: "RealESRGAN_x4plus.pth"},
    "art": {output_scale: "RealESRGAN_x4plus_anime_6B.pth" for output_scale in (2, 3, 4)},
}


def safe_model_name(name: str) -> str:
    """Only plain file names inside the models folder are allowed (no path tricks)."""
    if not name or Path(name).name != name or not name.lower().endswith(MODEL_EXT):
        raise ValueError(f"Invalid model name: {name!r}")
    return name


def resolve(profile: str, scale: int, model: str = "auto") -> str:
    """-> weights file name for this job."""
    if model and model != "auto":
        safe_model_name(model)
        return model
    try:
        return PROFILES[profile][scale]
    except KeyError:
        raise ValueError(f"Unsupported profile/scale: {profile} {scale}x")


def weights_path(file: str) -> Path:
    return MODELS_DIR / file


def weights_present(file: str) -> bool:
    path = weights_path(file)
    if not path.is_file():
        return False
    builtin_spec = BUILTIN.get(file)
    return path.stat().st_size >= (builtin_spec["min_bytes"] if builtin_spec else 1)


def ensure_weights(file: str, progress: Optional[Callable[[float], None]] = None) -> Path:
    """Built-in models are downloaded on first use (we don't redistribute them).
    Custom files must already be in the models folder."""
    path = weights_path(file)
    if weights_present(file):
        return path
    builtin_spec = BUILTIN.get(file)
    if not builtin_spec:
        raise FileNotFoundError(f"Model file not found: {path}")
    MODELS_DIR.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(".part")
    req = urllib.request.Request(builtin_spec["url"], headers={"User-Agent": "upscaler-app"})
    try:
        with urllib.request.urlopen(req, timeout=60) as response, open(tmp, "wb") as partial_file:
            total = int(response.headers.get("Content-Length") or 0)
            done = 0
            while True:
                chunk = response.read(1 << 20)
                if not chunk:
                    break
                partial_file.write(chunk)
                done += len(chunk)
                if progress and total:
                    progress(done / total)
        if tmp.stat().st_size < builtin_spec["min_bytes"]:
            raise RuntimeError("Downloaded model file is incomplete")
        os.replace(tmp, path)
    except Exception as error:
        tmp.unlink(missing_ok=True)
        raise RuntimeError(
            f"Could not download {file} ({error}). Download it manually from {builtin_spec['url']} "
            f"and place it in {MODELS_DIR}") from error
    return path


# ------------------------------------------------------- detection / specs --
def describe_shapes(shapes: dict) -> dict:
    """Work out architecture + hyper-parameters from {tensor name: shape}.
    Pure python (no torch), so it's easy to test. Raises ValueError if unsupported."""
    keys = set(shapes)
    if {"conv_first.weight", "conv_up1.weight", "conv_last.weight", "body.0.rdb1.conv1.weight"} <= keys:
        in_ch = shapes["conv_first.weight"][1]
        scale = {3: 4, 12: 2, 48: 1}.get(in_ch)
        if scale is None:
            raise ValueError(f"Unsupported RRDBNet input channels ({in_ch})")
        if shapes["conv_last.weight"][0] != 3:
            raise ValueError("Only 3-channel (RGB) models are supported")
        blocks = {int(match.group(1)) for tensor_name in keys if (match := re.match(r"body\.(\d+)\.rdb1\.conv1\.weight$", tensor_name))}
        return dict(arch="rrdb", net_scale=scale, num_feat=shapes["conv_first.weight"][0],
                    num_block=max(blocks) + 1, num_grow_ch=shapes["body.0.rdb1.conv1.weight"][0])
    if "body.0.weight" in keys and "body.1.weight" in keys and "conv_first.weight" not in keys:
        idx = sorted(int(match.group(1)) for tensor_name in keys if (match := re.match(r"body\.(\d+)\.weight$", tensor_name)))
        last = idx[-1]
        in_ch, out = shapes["body.0.weight"][1], shapes[f"body.{last}.weight"][0]
        scale = math.isqrt(out // 3) if out % 3 == 0 else 0
        if in_ch != 3 or scale not in (2, 3, 4) or scale * scale * 3 != out or (last - 2) % 2:
            raise ValueError("Unsupported SRVGGNetCompact layout")
        return dict(arch="compact", net_scale=scale, num_feat=shapes["body.0.weight"][0],
                    num_conv=(last - 2) // 2)
    raise ValueError("Unsupported model architecture (supported: Real-ESRGAN RRDBNet and SRVGGNetCompact)")



def list_models(spec_fn: Optional[Callable[[str], dict]] = None) -> list[dict]:
    """Built-in models plus every .pth/.pt in the models folder, for the UI picker.
    spec_fn inspects custom files (needs torch); without it they are listed as unchecked."""
    out = []
    for file_name, builtin_spec in BUILTIN.items():
        out.append(dict(file=file_name, builtin=True, label=builtin_spec["label"], note=builtin_spec["note"], net_scale=builtin_spec["net_scale"],
                        arch="RRDBNet", present=weights_present(file_name), ok=True))
    if MODELS_DIR.is_dir():
        for model_path in sorted(MODELS_DIR.iterdir(), key=lambda model_path: model_path.name.lower()):
            if model_path.suffix.lower() not in MODEL_EXT or model_path.name in BUILTIN or not model_path.is_file():
                continue
            item = dict(file=model_path.name, builtin=False, label=model_path.stem, size=model_path.stat().st_size, present=True)
            if spec_fn is None:
                item.update(ok=None, note="PyTorch is needed to check this file")
            else:
                try:
                    model_spec = spec_fn(model_path.name)
                    item.update(ok=True, net_scale=model_spec["net_scale"],
                                arch="RRDBNet" if model_spec["arch"] == "rrdb" else "SRVGGNetCompact",
                                note=f"native {model_spec['net_scale']}×")
                except Exception as error:  # noqa: BLE001
                    item.update(ok=False, error=str(error) or error.__class__.__name__)
            out.append(item)
    return out
