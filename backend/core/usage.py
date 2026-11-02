"""live cpu, memory and gpu numbers for the resource monitor."""
from __future__ import annotations

import psutil

psutil.cpu_percent(None)       # the first call always answers 0, so ask once now and measure from here


def read_usage() -> dict:
    memory = psutil.virtual_memory()
    return {
        "cpu_percent": psutil.cpu_percent(None),
        "ram_used": memory.total - memory.available,
        "ram_total": memory.total,
        "gpu": _read_gpu(memory.total),
    }


def _read_gpu(ram_total: int):
    """memory (and load, where the driver reports it) of the device Lightbench uses, or None on cpu."""
    try:
        import torch
    except ImportError:
        return None
    try:
        if torch.cuda.is_available():           # ROCm builds report themselves as cuda too
            free, total = torch.cuda.mem_get_info()
            gpu = {"name": torch.cuda.get_device_name(0), "memory_used": total - free, "memory_total": total,
                   "percent": None}
            try:
                gpu["percent"] = torch.cuda.utilization()     # needs the nvidia-ml-py package, absent otherwise
            except Exception:  # noqa: BLE001
                pass
            return gpu
        mps = getattr(torch.backends, "mps", None)
        if mps is not None and mps.is_available():
            # apple silicon shares one memory pool with the cpu
            return {"name": "Apple Silicon (MPS)", "memory_used": torch.mps.driver_allocated_memory(),
                    "memory_total": ram_total, "percent": None}
    except Exception:  # noqa: BLE001
        return None
    return None
