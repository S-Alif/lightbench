"""downloads and previews of finished files."""
from __future__ import annotations

import zipfile
from pathlib import Path

from starlette.background import BackgroundTask
from starlette.exceptions import HTTPException
from starlette.responses import FileResponse

from ..helpers import get_job_or_404


async def item_file(request):
    job = get_job_or_404(request)
    item = next((candidate for candidate in job.items if candidate.id == request.path_params["item_id"]), None)
    if not item or item.status != "done" or not item.out or not item.out.exists():
        raise HTTPException(404, "Result not ready")
    # ?inline=1 -> for <img>/<video> previews; otherwise a download
    if request.query_params.get("inline"):
        return FileResponse(item.out)
    return FileResponse(item.out, filename=item.out_name)


async def job_zip(request):
    job = get_job_or_404(request)
    done = [item for item in job.items if item.status == "done" and item.out and item.out.exists()]
    if not done:
        raise HTTPException(404, "Nothing to download yet")
    zpath = job.dir / "results.zip"
    with zipfile.ZipFile(zpath, "w", zipfile.ZIP_STORED) as archive:   # media is already compressed
        for item in done:
            archive.write(item.out, item.out_name)
    return FileResponse(zpath, filename=f"upscaled-{job.id}.zip", media_type="application/zip",
                        background=BackgroundTask(lambda: zpath.unlink(missing_ok=True)))


async def item_thumb(request):
    job = get_job_or_404(request)
    thumb_path = job.dir / "thumbs" / f"{Path(request.path_params['item_id']).name}.jpg"
    if not thumb_path.is_file():
        raise HTTPException(404, "No preview")
    return FileResponse(thumb_path, headers={"Cache-Control": "max-age=3600"})
