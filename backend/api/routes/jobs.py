"""create, list, inspect, cancel and delete jobs."""
from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

from starlette.responses import JSONResponse

from ...config import JOBS_DIR
from ...core import pipeline
from ...core.editing.operations import validate_edit
from ...core.media.types import IMAGE_EXT, VIDEO_EXT
from ...services.jobs import JobBusy
from ..deps import manager
from ..helpers import error_response, get_job_or_404, is_local_request, safe_name


async def list_jobs(request):
    return JSONResponse({"jobs": [job.summary() for job in manager.list()],
                         "data_dir": str(JOBS_DIR.resolve())})


async def create_job(request):
    form = await request.form()
    try:
        opts = pipeline.JobOptions.from_dict(json.loads(form.get("options") or "{}"))
    except (ValueError, TypeError) as options_error:
        return error_response(f"Invalid options: {options_error}")
    files = [uploaded_file for uploaded_file in form.getlist("files") if hasattr(uploaded_file, "filename")]
    if not files:
        return error_response("No files uploaded")

    # one crop / rotate entry per file, in the same order as the files (null = untouched)
    try:
        raw_edits = json.loads(form.get("edits") or "[]")
        if not isinstance(raw_edits, list):
            raise ValueError("edits must be a list")
        edits = [validate_edit(raw_edits[idx]) if idx < len(raw_edits) else None for idx in range(len(files))]
    except (ValueError, TypeError) as edits_error:
        return error_response(f"Invalid edits: {edits_error}")

    kinds = {("image" if Path(uploaded_file.filename or "").suffix.lower() in IMAGE_EXT else
              "video" if Path(uploaded_file.filename or "").suffix.lower() in VIDEO_EXT else None) for uploaded_file in files}
    kinds.discard(None)
    if len(kinds) > 1:
        return error_response("Images and videos can't be processed in the same job. Upload them separately.")
    job_id = manager.new_id()
    in_dir = JOBS_DIR / job_id / "in"
    in_dir.mkdir(parents=True, exist_ok=True)
    uploads = []
    try:
        for idx, uploaded_file in enumerate(files):
            ext = Path(uploaded_file.filename or "").suffix.lower()
            kind = "image" if ext in IMAGE_EXT else "video" if ext in VIDEO_EXT else None
            if not kind:
                continue
            if kind == "video" and edits[idx]:
                raise ValueError("Crop and rotate are only available for images")
            dst = in_dir / f"{idx}_{safe_name(uploaded_file.filename)}"
            with open(dst, "wb") as out:
                while chunk := await uploaded_file.read(1 << 20):
                    out.write(chunk)
            uploads.append((safe_name(uploaded_file.filename), dst, kind, edits[idx]))
    except ValueError as edit_error:
        shutil.rmtree(in_dir.parent, ignore_errors=True)
        return error_response(str(edit_error))
    except Exception:
        shutil.rmtree(in_dir.parent, ignore_errors=True)
        raise
    if not uploads:
        shutil.rmtree(in_dir.parent, ignore_errors=True)
        return error_response("None of the files are supported images or videos")
    return JSONResponse(manager.create(job_id, opts, uploads).to_dict())


async def get_job(request):
    return JSONResponse(get_job_or_404(request).to_dict())


async def cancel_job(request):
    manager.cancel(get_job_or_404(request).id)
    return JSONResponse({"ok": True})


async def delete_job(request):
    try:
        manager.delete(request.path_params["job_id"])
    except JobBusy as busy_error:
        return error_response(str(busy_error), 409)
    return JSONResponse({"ok": True})


async def open_folder(request):
    """Show the job's output folder in Explorer/Finder. Only for the machine running the app."""
    job = get_job_or_404(request)
    if not is_local_request(request):
        return error_response("Only available on the computer that runs the app", 403)
    target = str((job.dir / "out").resolve())
    try:
        if sys.platform == "win32":
            os.startfile(target)  # noqa: S606
        elif sys.platform == "darwin":
            subprocess.Popen(["open", target])
        else:
            subprocess.Popen(["xdg-open", target], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    except Exception as open_error:  # noqa: BLE001
        return error_response(f"Could not open the folder: {open_error}", 500)
    return JSONResponse({"ok": True})
