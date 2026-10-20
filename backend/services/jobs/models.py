"""data classes for a job and the files inside it, and how they are saved to disk.

Every job lives in data/jobs/<id>/ :
    job.json      settings + per-file results (this is the history record)
    out/          the finished files
    thumbs/       small previews for the cards
    in/           uploads, removed as soon as each file has been processed
"""
from __future__ import annotations

import json
import os
import threading
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

from ...config import JOBS_DIR
from ...core import pipeline


@dataclass
class Item:
    id: str
    name: str
    kind: str                     # image | video
    src: Optional[Path] = None
    status: str = "queued"        # queued | running | done | error | cancelled
    progress: float = 0.0
    message: str = ""
    out_name: Optional[str] = None
    out: Optional[Path] = None
    error: Optional[str] = None
    size: int = 0                 # bytes of the result
    src_size: int = 0
    width: int = 0
    height: int = 0
    duration: float = 0.0
    thumb: bool = False

    def to_dict(self) -> dict:
        return {"id": self.id, "name": self.name, "kind": self.kind, "status": self.status,
                "progress": round(self.progress, 4), "message": self.message,
                "out_name": self.out_name, "error": self.error, "size": self.size,
                "src_size": self.src_size, "w": self.width, "h": self.height,
                "duration": round(self.duration, 2), "thumb": self.thumb}

    @classmethod
    def from_json(cls, data: dict, job_dir: Path) -> "Item":
        item = cls(id=data["id"], name=data["name"], kind=data["kind"], status=data.get("status", "error"),
                 out_name=data.get("out_name"), error=data.get("error"), size=data.get("size", 0),
                 src_size=data.get("src_size", 0), width=data.get("w", 0), height=data.get("h", 0),
                 duration=data.get("duration", 0.0), thumb=data.get("thumb", False))
        if item.out_name:
            item.out = job_dir / "out" / item.out_name
        if item.status == "done":
            item.progress = 1.0
        return item


@dataclass
class Job:
    id: str
    opts_dict: dict
    items: list[Item]
    opts: Optional[pipeline.JobOptions] = None      # none for jobs loaded from history
    created: float = field(default_factory=time.time)
    started: Optional[float] = None
    finished: Optional[float] = None
    cancel: threading.Event = field(default_factory=threading.Event)

    @property
    def dir(self) -> Path:
        return JOBS_DIR / self.id

    @property
    def active(self) -> bool:
        return self.status in ("queued", "running")

    @property
    def status(self) -> str:
        statuses = [item.status for item in self.items]
        if any(status_name == "running" for status_name in statuses):
            return "running"
        if any(status_name == "queued" for status_name in statuses):
            return "running" if any(status_name != "queued" for status_name in statuses) else "queued"
        done = statuses.count("done")
        if done == len(statuses):
            return "done"
        if self.cancel.is_set() or "cancelled" in statuses:
            return "cancelled"
        return "partial" if done else "failed"

    @property
    def kind(self) -> str:
        kinds = {item.kind for item in self.items}
        return kinds.pop() if len(kinds) == 1 else "mixed"

    @property
    def elapsed(self) -> float:
        if not self.started:
            return 0.0
        return max(0.0, (self.finished or time.time()) - self.started)

    def summary(self) -> dict:
        done = [item for item in self.items if item.status == "done"]
        return {
            "id": self.id, "status": self.status, "kind": self.kind,
            "created": self.created, "started": self.started, "finished": self.finished,
            "elapsed": round(self.elapsed, 1),
            "count": len(self.items), "done": len(done),
            "failed": sum(1 for item in self.items if item.status == "error"),
            "total_bytes": sum(item.size for item in done),
            "path": str((self.dir / "out").resolve()),
            "options": self.opts_dict,
            "thumbs": [item.id for item in done if item.thumb][:4],
        }

    def to_dict(self) -> dict:
        data = self.summary()
        data["items"] = [item.to_dict() for item in self.items]
        return data

    # ---- persistence
    def save(self) -> None:
        data = {"version": 1, "id": self.id, "created": self.created, "started": self.started,
                "finished": self.finished, "opts": self.opts_dict,
                "items": [{**item.to_dict(), "progress": None, "message": None} for item in self.items]}
        self.dir.mkdir(parents=True, exist_ok=True)
        tmp = self.dir / "job.json.tmp"
        tmp.write_text(json.dumps(data, indent=1), encoding="utf-8")
        os.replace(tmp, self.dir / "job.json")

    @classmethod
    def load(cls, job_dir: Path) -> Optional["Job"]:
        try:
            data = json.loads((job_dir / "job.json").read_text(encoding="utf-8"))
            job = cls(id=data["id"], opts_dict=data.get("opts", {}), items=[],
                      created=data.get("created", job_dir.stat().st_mtime),
                      started=data.get("started"), finished=data.get("finished"))
            job.items = [Item.from_json(item_data, job_dir) for item_data in data.get("items", [])]
            return job
        except Exception:  # noqa: BLE001
            return None
