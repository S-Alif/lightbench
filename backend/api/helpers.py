"""small helpers used by several routes."""
from __future__ import annotations

import re
from pathlib import Path

from starlette.exceptions import HTTPException
from starlette.responses import JSONResponse

from .deps import manager


def error_response(msg: str, status: int = 400) -> JSONResponse:
    return JSONResponse({"error": msg}, status_code=status)


def safe_name(name: str) -> str:
    name = Path(name.replace("\\", "/")).name
    return re.sub(r"[^\w.\- ()]", "_", name)[:120] or "file"


def is_local_request(request) -> bool:
    return bool(request.client) and request.client.host in ("127.0.0.1", "::1", "localhost")


def get_job_or_404(request):
    job = manager.get(request.path_params["job_id"])
    if not job:
        raise HTTPException(404, "Unknown job")
    return job
