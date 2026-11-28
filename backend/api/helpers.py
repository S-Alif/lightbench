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
    """true when the browser runs on the same computer as the app. that includes opening the app through the
    computer's own network address (http://192.168.x.x:8000 from that same computer): the request then comes
    from the address the app is listening on."""
    if not request.client:
        return False
    host = request.client.host.removeprefix("::ffff:")
    if host in ("::1", "localhost") or host.startswith("127."):
        return True
    server = request.scope.get("server")
    return bool(server) and server[0].removeprefix("::ffff:") == host


def get_job_or_404(request):
    job = manager.get(request.path_params["job_id"])
    if not job:
        lost = manager.lost_entry(request.path_params["job_id"])
        if lost:
            raise HTTPException(409, f"Can't reach this job's folder ({lost['reason']}): {lost['path']}")
        raise HTTPException(404, "Unknown job")
    return job
