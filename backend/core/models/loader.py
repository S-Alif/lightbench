"""reads weight files, detects the architecture of custom models and builds the network."""
from __future__ import annotations

from pathlib import Path

import torch
import torch.nn as nn

from .architectures import RRDBNet, SRVGGNetCompact
from .registry import BUILTIN, describe_shapes, list_models as _list, weights_path


def _read_state(path: Path) -> dict:
    # weights_only=True: refuses to run arbitrary pickled code from a downloaded file
    state = torch.load(path, map_location="cpu", weights_only=True)
    for key in ("params_ema", "params", "state_dict", "model"):
        if isinstance(state, dict) and isinstance(state.get(key), dict):
            state = state[key]
            break
    return {(key[7:] if key.startswith("module.") else key): tensor for key, tensor in state.items() if hasattr(tensor, "shape")}


_inspect_cache: dict = {}


def spec(file: str) -> dict:
    """Spec for a model file (built-in or custom). Cached by file mtime."""
    builtin_spec = BUILTIN.get(file)
    if builtin_spec:
        model_spec = dict(builtin_spec, num_feat=64, num_grow_ch=32)
    else:
        weights_file = weights_path(file)
        key = (file, weights_file.stat().st_mtime_ns)
        if key not in _inspect_cache:
            state = _read_state(weights_file)
            _inspect_cache[key] = describe_shapes({tensor_name: tuple(tensor.shape) for tensor_name, tensor in state.items()})
        model_spec = dict(_inspect_cache[key])
    # reflect-pad inputs so pixel_unshuffle (scale 2 / 1 RRDBNet) sees multiples of 2 / 4
    model_spec["mod"] = {2: 2, 1: 4}.get(model_spec["net_scale"], 1) if model_spec["arch"] == "rrdb" else 1
    return model_spec


def list_models() -> list[dict]:
    return _list(spec)


def load_network(file: str, device: torch.device, half: bool) -> nn.Module:
    model_spec = spec(file)
    if model_spec["arch"] == "rrdb":
        net = RRDBNet(scale=model_spec["net_scale"], num_feat=model_spec["num_feat"], num_block=model_spec["num_block"],
                      num_grow_ch=model_spec["num_grow_ch"])
    else:
        net = SRVGGNetCompact(num_feat=model_spec["num_feat"], num_conv=model_spec["num_conv"], upscale=model_spec["net_scale"])
    net.load_state_dict(_read_state(weights_path(file)), strict=True)
    net.eval().to(device)
    return net.half() if half else net
