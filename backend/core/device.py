"""Pick the best available torch device and describe it for the UI."""
from __future__ import annotations

import torch


def pick_device() -> torch.device:
    # Note: ROCm builds of torch also report themselves as "cuda".
    if torch.cuda.is_available():
        return torch.device("cuda")
    
    mps = getattr(torch.backends, "mps", None)

    if mps is not None and mps.is_available():
        return torch.device("mps")
    
    return torch.device("cpu")


def describe() -> dict:
    dev = pick_device()
    info = {"device": dev.type, "name": "CPU", "vram_gb": None, "torch": torch.__version__}

    if dev.type == "cuda":
        props = torch.cuda.get_device_properties(0)
        hip = getattr(torch.version, "hip", None)
        info["name"] = props.name
        info["vram_gb"] = round(props.total_memory / 1024**3, 1)
        info["backend"] = "ROCm" if hip else "CUDA"

    elif dev.type == "mps":
        info["name"] = "Apple Silicon (MPS)"
        info["backend"] = "MPS"

    else:
        info["backend"] = "CPU"

    return info


def empty_cache(dev: torch.device) -> None:
    try:
        if dev.type == "cuda":
            torch.cuda.empty_cache()

        elif dev.type == "mps":
            torch.mps.empty_cache()
            
    except Exception:
        pass
