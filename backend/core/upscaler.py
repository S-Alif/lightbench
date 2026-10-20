"""Tiled Real-ESRGAN inference with automatic out-of-memory fallback.

Mirrors the behaviour of RealESRGANer from your scripts (reflect mod-padding,
tile + tile_pad stitching, `outscale` resize) without needing basicsr.
"""
from __future__ import annotations

import math
import threading
from typing import Callable, Optional

import numpy as np
import torch
import torch.nn.functional as functional
from PIL import Image

from . import device as dev_mod
from .models import loader, registry
from .errors import Cancelled

TILE_PAD = 10
TILE_FALLBACKS = (512, 256, 128, 64)


def _is_oom(error: BaseException) -> bool:
    if isinstance(error, MemoryError):
        return True
    if hasattr(torch, "OutOfMemoryError") and isinstance(error, torch.OutOfMemoryError):
        return True
    msg = str(error).lower()
    return isinstance(error, RuntimeError) and ("out of memory" in msg or "allocate" in msg and "memory" in msg)


class Upscaler:
    """One loaded network. Use Upscaler.get() so models are cached."""

    _cache: Optional["Upscaler"] = None
    _lock = threading.Lock()

    def __init__(self, file: str, device: torch.device, half: bool):
        self.key, self.device, self.half = file, device, half
        model_spec = loader.spec(file)
        self.net_scale, self.mod = model_spec["net_scale"], model_spec["mod"]
        self.net = loader.load_network(file, device, half)

    @classmethod
    def get(cls, file: str, fp32: bool = False,
            on_download: Optional[Callable[[float], None]] = None) -> "Upscaler":
        registry.ensure_weights(file, on_download)
        device = dev_mod.pick_device()
        # fp16 only on CUDA/ROCm. (Some GTX 16xx cards need fp32 -> the UI toggle.)
        half = device.type == "cuda" and not fp32
        with cls._lock:
            cached = cls._cache
            if cached and (cached.key, cached.device.type, cached.half) == (file, device.type, half):
                return cached
            cls._cache = None  # free VRAM before loading the next model
            dev_mod.empty_cache(device)
            cls._cache = cls(file, device, half)
            return cls._cache

    # ------------------------------------------------------------------
    @torch.inference_mode()
    def _forward_tiled(self, input_tensor: torch.Tensor, tile: int, progress, cancel) -> torch.Tensor:
        scale = self.net_scale
        batch_size, channels, height, width = input_tensor.shape
        if tile <= 0 or (height <= tile and width <= tile):
            if cancel and cancel.is_set():
                raise Cancelled()
            out = self.net(input_tensor)
            if progress:
                progress(1.0)
            return out
        out = input_tensor.new_zeros((batch_size, channels, height * scale, width * scale))
        tiles_across, tiles_down = math.ceil(width / tile), math.ceil(height / tile)
        total, tiles_done = tiles_across * tiles_down, 0
        for tile_row in range(tiles_down):
            for tile_column in range(tiles_across):
                if cancel and cancel.is_set():
                    raise Cancelled()
                tile_left, tile_right = tile_column * tile, min(tile_column * tile + tile, width)
                tile_top, tile_bottom = tile_row * tile, min(tile_row * tile + tile, height)
                px0, px1 = max(tile_left - TILE_PAD, 0), min(tile_right + TILE_PAD, width)
                py0, py1 = max(tile_top - TILE_PAD, 0), min(tile_bottom + TILE_PAD, height)
                tile_output = self.net(input_tensor[:, :, py0:py1, px0:px1])
                ox0, oy0 = (tile_left - px0) * scale, (tile_top - py0) * scale
                out[:, :, tile_top * scale:tile_bottom * scale, tile_left * scale:tile_right * scale] = \
                    tile_output[:, :, oy0:oy0 + (tile_bottom - tile_top) * scale, ox0:ox0 + (tile_right - tile_left) * scale]
                tiles_done += 1
                if progress:
                    progress(tiles_done / total)
        return out

    def enhance(self, rgb: np.ndarray, outscale: float, tile: int = 512,
                progress: Optional[Callable[[float], None]] = None,
                cancel: Optional[threading.Event] = None) -> np.ndarray:
        """rgb: HxWx3 uint8 -> upscaled HxWx3 uint8."""
        height, width = rgb.shape[:2]
        scale = self.net_scale
        input_tensor = torch.from_numpy(np.array(rgb)).permute(2, 0, 1).unsqueeze(0).float().div_(255)
        input_tensor = input_tensor.to(self.device)
        if self.half:
            input_tensor = input_tensor.half()
        mod = self.mod
        pad_bottom, pad_right = (-height) % mod, (-width) % mod
        if pad_bottom or pad_right:
            input_tensor = functional.pad(input_tensor, (0, pad_right, 0, pad_bottom), mode="reflect")

        tile = max(0, tile - tile % 4) if tile else 0
        sizes = [tile] + [tile_size_to_try for tile_size_to_try in TILE_FALLBACKS if tile == 0 or tile_size_to_try < tile]
        last_err = None
        for tile_size_to_try in sizes:
            try:
                output_tensor = self._forward_tiled(input_tensor, tile_size_to_try, progress, cancel)
                break
            except Cancelled:
                raise
            except Exception as error:  # noqa: BLE001
                if not _is_oom(error):
                    raise
                last_err = error
                dev_mod.empty_cache(self.device)
        else:
            raise RuntimeError(f"Out of memory even with 64px tiles: {last_err}")

        output_tensor = output_tensor[:, :, : height * scale, : width * scale]
        out = output_tensor.squeeze(0).float().clamp_(0, 1).mul_(255).round_().byte().permute(1, 2, 0).cpu().numpy()
        if abs(outscale - scale) > 1e-6:
            resized_image = Image.fromarray(out).resize(
                (max(1, round(width * outscale)), max(1, round(height * outscale))), Image.LANCZOS)
            out = np.array(resized_image)
        return out
