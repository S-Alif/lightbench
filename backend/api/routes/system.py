"""GET /api/system, hardware and folder info for the header."""
from __future__ import annotations

from starlette.responses import JSONResponse

from ...config import DATA_DIR, MODELS_DIR
from ..helpers import is_local_request


async def system(request):
    from ...core.media import video
    info: dict = {"ffmpeg": video.ffmpeg_available(), "data_dir": str(DATA_DIR.resolve()),
                  "models_dir": str(MODELS_DIR.resolve()), "local": is_local_request(request)}
    try:
        from ...core import device
        info.update(device.describe())
    except ImportError as import_error:
        info.update({"device": "none", "name": "PyTorch is not installed", "backend": "none",
                     "error": f"{import_error}. Run `python setup.py`. Watermark-only jobs still work."})
    return JSONResponse(info)
