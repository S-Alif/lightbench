"""runs jobs one at a time on a single worker thread.

One worker on purpose: the GPU (or CPU) is the bottleneck, and running two upscales at once
just fights for VRAM. Images and videos are never processed at the same time either.
"""
from __future__ import annotations

import os
import queue
import shutil
import threading
import time
import uuid
from pathlib import Path
from typing import Optional

from ...config import DATA_DIR, JOBS_DIR, LOCATIONS_FILE
from ...core import pipeline
from ...core.errors import Cancelled
from ...core.media import thumbnails
from .locations import Locations, absolute
from .models import Item, Job


class JobBusy(Exception):
    """Raised when asking to delete a job that is still queued or running."""


class JobManager:
    def __init__(self) -> None:
        self.jobs: dict[str, Job] = {}            # jobs whose folder can be reached
        self.lost: dict[str, dict] = {}           # listed in job-locations.json but the folder can't be reached right now
        self.q: "queue.Queue[str]" = queue.Queue()
        self.lock = threading.Lock()
        self._sync_lock = threading.RLock()
        self.locations = Locations(LOCATIONS_FILE, DATA_DIR)
        JOBS_DIR.mkdir(parents=True, exist_ok=True)
        self.locations.load()
        self.sync()
        threading.Thread(target=self._worker, daemon=True, name="upscale-worker").start()

    # ---- keeping the list of job folders and the loaded history in step
    def _adopt_untracked(self) -> None:
        """job folders inside data/jobs that the list does not know yet (every install from before the list
        existed, or a folder copied in by hand) get an entry, so nothing is ever left out."""
        added = False
        try:
            children = sorted(JOBS_DIR.iterdir())
        except OSError:
            return
        known = {absolute(self.locations.path_of(entry)) for entry in self.locations.entries.values()}
        for folder in children:
            if absolute(folder) in known or not (folder / "job.json").is_file():
                continue
            job = Job.load(folder)
            if job and job.id not in self.locations.entries:
                self.locations.register(job.id, folder, job.created, save=False)
                added = True
        if added:
            self.locations.save()

    def _attach(self, job_id: str, entry: dict) -> None:
        """loads the job an entry points at, or notes why it can't be reached."""
        path = self.locations.path_of(entry)
        reason, job = "", None
        if not path.is_dir():
            reason = "Folder not found"
        elif not (path / "job.json").is_file():
            reason = "No Lightbench job in that folder"
        else:
            job = Job.load(path)
            if not job:
                reason = "job.json can't be read"
            elif job.id != job_id:
                job, reason = None, "That folder holds a different job"
        if not job:
            self.jobs.pop(job_id, None)
            self.lost[job_id] = {"id": job_id, "path": str(path), "created": entry.get("created") or 0, "reason": reason, "unreachable": True}
            return
        changed = False
        for item in job.items:
            if item.status in ("queued", "running"):      # the app was closed mid-job
                item.status, item.error, changed = "error", "Interrupted: the app was closed before this file finished", True
            elif item.status == "done" and (not item.out or not item.out.exists()):
                item.status, item.error, changed = "error", "The result file is missing from disk", True
        if changed:
            job.finished = job.finished or time.time()
            try:
                job.save()
            except OSError:
                pass
        self.lost.pop(job_id, None)
        self.jobs[job_id] = job

    def sync(self) -> None:
        """makes the loaded history match job-locations.json and the disk. cheap (one stat per job), so it
        runs whenever the list is asked for: a reconnected drive or a hand-fixed path shows up straight away."""
        with self._sync_lock:
            self.locations.reload_if_changed()
            self._adopt_untracked()
            entries = dict(self.locations.entries)
            for job_id, entry in entries.items():
                job = self.jobs.get(job_id)
                if job and job.active:
                    continue
                path = self.locations.path_of(entry)
                if job and job.dir == path and (path / "job.json").is_file():
                    continue
                self._attach(job_id, entry)
            for job_id in [known for known in self.jobs if known not in entries]:
                if not self.jobs[job_id].active:               # taken out of the file by hand: stop listing it
                    self.jobs.pop(job_id, None)
            for job_id in [known for known in self.lost if known not in entries]:
                self.lost.pop(job_id, None)

    @staticmethod
    def _owned_by_app(folder: Path) -> bool:
        return absolute(folder).parent == absolute(JOBS_DIR)

    def plan_location(self, job_id: str, base_text: str = "", like: Optional[Job] = None) -> Path:
        """creates the (empty) folder <root>/<id> a new job will live in and returns it. base_text is the root
        folder chosen by the person; "" means data/jobs, or next to the job `like` when that one was kept somewhere else.
        raises ValueError when the folder can't be used."""
        if base_text.strip():
            from ...core.tools import resolve_folder
            base = resolve_folder(base_text)
        elif like is not None and not self._owned_by_app(like.dir):
            base = like.dir.parent
        else:
            base = JOBS_DIR
        folder = absolute(base) / job_id                 # same layout as data/jobs: <root>/<id>/
        try:
            folder.mkdir(parents=True, exist_ok=False)
        except OSError as failure:
            raise ValueError(f"Can't use that folder: {failure.strerror or failure}") from failure
        return folder

    # ---- api used by the web layer
    @staticmethod
    def new_id() -> str:
        return uuid.uuid4().hex[:12]

    def create(self, job_id: str, opts: pipeline.JobOptions,
               uploads: list[tuple[str, Path, str, Optional[dict]]], location: Path) -> Job:
        """uploads: (original name, path already saved in the job folder, kind, edit or None).
        location: the job folder from plan_location."""
        options_dict = opts.to_dict()
        options_dict.pop("location", None)          # where it was saved is in job-locations.json, not a setting
        if not options_dict.get("watermark"):
            options_dict.pop("watermark", None)
        job = Job(id=job_id, opts=opts, opts_dict=options_dict, items=[], location=location)
        for name, path, kind, edit in uploads:
            job.items.append(Item(id=uuid.uuid4().hex[:8], name=name, kind=kind, src=path, edit=edit,
                                  src_size=path.stat().st_size))
        job.save()
        self.locations.register(job.id, location, job.created)
        with self.lock:
            self.jobs[job.id] = job
        self.q.put(job.id)
        return job

    def get(self, job_id: str) -> Optional[Job]:
        if job_id not in self.jobs and job_id not in self.lost:
            self.sync()                                # maybe a path was just added by hand
        return self.jobs.get(job_id)

    def list(self) -> list[Job]:
        self.sync()
        return sorted(self.jobs.values(), key=lambda job: job.created, reverse=True)

    def unreachable(self) -> list[dict]:
        return sorted(self.lost.values(), key=lambda entry: entry["created"], reverse=True)

    def lost_entry(self, job_id: str) -> Optional[dict]:
        return self.lost.get(job_id)

    def cancel(self, job_id: str) -> None:
        job = self.get(job_id)
        if job:
            job.cancel.set()

    def delete(self, job_id: str) -> None:
        """removes a job. a job whose folder can't be reached is only taken off the list; nothing on disk is touched."""
        if job_id in self.lost:
            self.lost.pop(job_id, None)
            self.locations.forget(job_id)
            return
        job = self.get(job_id)
        if not job:
            return
        if job.active:
            raise JobBusy("Cancel this job before deleting it")
        with self.lock:
            self.jobs.pop(job_id, None)
        self._remove_files(job)
        self.locations.forget(job_id)

    def _remove_files(self, job: Job) -> None:
        folder = job.dir
        if self._owned_by_app(folder):
            shutil.rmtree(folder, ignore_errors=True)
            return
        # a folder the person chose: remove only what this job created, and the folder itself only if nothing else is in it
        for item in job.items:
            if item.out:
                item.out.unlink(missing_ok=True)
            (folder / "thumbs" / f"{item.id}.jpg").unlink(missing_ok=True)
        shutil.rmtree(folder / "in", ignore_errors=True)
        for name in ("job.json", "job.json.tmp", "results.zip"):
            (folder / name).unlink(missing_ok=True)
        for name in ("out", "thumbs"):
            try:
                (folder / name).rmdir()
            except OSError:
                pass
        try:
            folder.rmdir()
        except OSError:
            pass

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
            except Exception as failure:  # noqa: BLE001  (never let the worker thread die)
                for item in job.items:           # e.g. the drive holding the job folder was unplugged
                    if item.status in ("queued", "running"):
                        item.status, item.error = "error", f"Can't write to the job folder: {failure}"
                job.finished = time.time()
                try:
                    job.save()
                except OSError:
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
        shutil.rmtree(job.dir / "in", ignore_errors=True)
        job.save()
