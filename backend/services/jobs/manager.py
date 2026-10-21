"""runs jobs one at a time on a single worker thread.

One worker on purpose: the GPU (or CPU) is the bottleneck, and running two upscales at once
just fights for VRAM. Images and videos are never processed at the same time either.
"""
from __future__ import annotations

import queue
import shutil
import threading
import time
import uuid
from pathlib import Path
from typing import Optional

from ...config import JOBS_DIR
from ...core import pipeline
from ...core.errors import Cancelled
from ...core.media import thumbnails
from .models import Item, Job


class JobBusy(Exception):
    """Raised when asking to delete a job that is still queued or running."""


class JobManager:
    def __init__(self) -> None:
        self.jobs: dict[str, Job] = {}
        self.q: "queue.Queue[str]" = queue.Queue()
        self.lock = threading.Lock()
        JOBS_DIR.mkdir(parents=True, exist_ok=True)
        self._load_history()
        threading.Thread(target=self._worker, daemon=True, name="upscale-worker").start()

    def _load_history(self) -> None:
        for job_dir in JOBS_DIR.iterdir():
            if not (job_dir / "job.json").is_file():
                continue
            job = Job.load(job_dir)
            if not job:
                continue
            changed = False
            for item in job.items:
                if item.status in ("queued", "running"):      # the app was closed mid-job
                    item.status, item.error, changed = "error", "Interrupted: the app was closed before this file finished", True
                elif item.status == "done" and (not item.out or not item.out.exists()):
                    item.status, item.error, changed = "error", "The result file is missing from disk", True
            if changed:
                job.finished = job.finished or time.time()
                job.save()
            self.jobs[job.id] = job

    # ---- api used by the web layer
    @staticmethod
    def new_id() -> str:
        return uuid.uuid4().hex[:12]

    def create(self, job_id: str, opts: pipeline.JobOptions,
               uploads: list[tuple[str, Path, str, Optional[dict]]]) -> Job:
        """uploads: (original name, path already saved in the job folder, kind, edit or None)"""
        options_dict = opts.to_dict()
        if not options_dict.get("watermark"):
            options_dict.pop("watermark", None)
        job = Job(id=job_id, opts=opts, opts_dict=options_dict, items=[])
        for name, path, kind, edit in uploads:
            job.items.append(Item(id=uuid.uuid4().hex[:8], name=name, kind=kind, src=path, edit=edit,
                                  src_size=path.stat().st_size))
        job.save()
        with self.lock:
            self.jobs[job.id] = job
        self.q.put(job.id)
        return job

    def get(self, job_id: str) -> Optional[Job]:
        return self.jobs.get(job_id)

    def list(self) -> list[Job]:
        return sorted(self.jobs.values(), key=lambda job: job.created, reverse=True)

    def cancel(self, job_id: str) -> None:
        job = self.get(job_id)
        if job:
            job.cancel.set()

    def delete(self, job_id: str) -> None:
        job = self.get(job_id)
        if not job:
            return
        if job.active:
            raise JobBusy("Cancel this job before deleting it")
        with self.lock:
            self.jobs.pop(job_id, None)
        shutil.rmtree(job.dir, ignore_errors=True)

    # ---- worker
    @staticmethod
    def _unique_name(job: Job, name: str) -> str:
        taken = {item.out_name for item in job.items if item.out_name}
        if name not in taken:
            return name
        name_path = Path(name)
        counter = 2
        while f"{name_path.stem}-{counter}{name_path.suffix}" in taken:
            counter += 1
        return f"{name_path.stem}-{counter}{name_path.suffix}"

    def _worker(self) -> None:
        while True:
            job = self.jobs.get(self.q.get())
            if not job or not job.opts:
                continue
            try:
                self._run(job)
            except Exception:  # noqa: BLE001  (never let the worker thread die)
                pass

    def _run(self, job: Job) -> None:
        out_dir = job.dir / "out"
        out_dir.mkdir(parents=True, exist_ok=True)
        job.started = time.time()
        for item in job.items:
            if job.cancel.is_set():
                item.status, item.message = "cancelled", "Cancelled"
                continue
            item.status = "running"
            job.save()
            name = self._unique_name(
                job, pipeline.output_name(Path(item.name).stem, job.opts, item.kind == "video"))
            item.out_name = name
            dst = out_dir / name

            def progress(frac: float, msg: str = "", target_item=item) -> None:
                target_item.progress, target_item.message = frac, msg or target_item.message

            try:
                if item.kind == "video":
                    info = pipeline.process_video(str(item.src), dst, job.opts, progress, job.cancel) or {}
                else:
                    info = pipeline.process_image(str(item.src), dst, job.opts, progress, job.cancel,
                                                  edit=item.edit) or {}
                item.out, item.status, item.progress, item.message = dst, "done", 1.0, "Done"
                item.size = dst.stat().st_size
                item.width, item.height = info.get("w", 0), info.get("h", 0)
                item.duration = info.get("duration", 0.0)
                item.thumb = thumbnails.make_thumb(dst, item.kind, job.dir / "thumbs" / f"{item.id}.jpg")
            except Cancelled:
                item.status, item.message, item.out_name = "cancelled", "Cancelled", None
                dst.unlink(missing_ok=True)
            except Exception as error:  # noqa: BLE001
                item.status, item.error, item.out_name = "error", str(error) or error.__class__.__name__, None
                item.message = ""
                dst.unlink(missing_ok=True)
            finally:
                if item.src:
                    item.src.unlink(missing_ok=True)   # original no longer needed
            job.save()
        job.finished = time.time()
        job.save()
        shutil.rmtree(job.dir / "in", ignore_errors=True)
