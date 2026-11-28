"""the list of where every job folder lives.

data/job-locations.json is a json ARRAY OF OBJECTS, one object per job:

    [
      {"id": "3f9c1a7b2d4e", "path": "/home/you/Pictures/Lightbench/2026-11-27_0942-3f9c1a7b2d4e", "created": 1795765320.5}
    ]

* the history follows these paths instead of scanning a folder, so a job can live anywhere.
* an object (not a bare string) per job, so a new field can be added later without breaking anything.
  keys this version does not know are kept untouched when the file is rewritten, so a newer
  version's data survives an older version, and a hand-added note survives too.
* paths are written absolute. a relative path typed by hand is read as relative to the data folder,
  and "~" means the home folder. the file can be edited by hand while the app runs; it is re-read
  when it changes.
* a broken file is never overwritten: it is renamed to job-locations.json.broken-<time> and the list is
  rebuilt from data/jobs. entries that are not objects with an id and a path are kept as they are.
* this file only points at folders. deleting a job from the list never touches files outside what the
  job itself created (see JobManager.delete).
"""
from __future__ import annotations

import json
import os
import threading
import time
from pathlib import Path
from typing import Optional


def absolute(path: "str | Path") -> Path:
    """absolute and tidy (no ..), without following symlinks so the path stays what the person chose."""
    return Path(os.path.abspath(os.path.expanduser(str(path))))


class Locations:
    def __init__(self, file: Path, base: Path) -> None:
        self.file = file
        self.base = base                       # relative paths in the file are read from here
        self.entries: dict[str, dict] = {}
        self._others: list = []                # things in the file that are not job entries; written back as they were
        self._stamp: Optional[tuple] = None
        self.lock = threading.RLock()

    # ---- reading
    def _stat(self) -> Optional[tuple]:
        try:
            info = self.file.stat()
            return (info.st_mtime_ns, info.st_size)
        except OSError:
            return None

    def load(self) -> None:
        with self.lock:
            self.entries, self._others = {}, []
            self._stamp = self._stat()
            if self._stamp is None:
                return
            try:
                raw = json.loads(self.file.read_text(encoding="utf-8"))
                if not isinstance(raw, list):
                    raise ValueError("not a list")
            except ValueError:                 # unreadable json: keep it for the person, start a fresh list
                try:
                    self.file.rename(self.file.with_name(f"{self.file.name}.broken-{int(time.time())}"))
                except OSError:
                    pass
                self._stamp = None
                return
            except OSError:
                return
            for item in raw:
                if isinstance(item, dict) and isinstance(item.get("id"), str) and isinstance(item.get("path"), str) and item["id"]:
                    self.entries[item["id"]] = item
                else:
                    self._others.append(item)

    def reload_if_changed(self) -> bool:
        """true when the file was edited (or replaced) since it was last read or written by us."""
        with self.lock:
            stamp = self._stat()
            if stamp is None or stamp == self._stamp:
                return False
            self.load()
            return True

    def path_of(self, entry: dict) -> Path:
        path = Path(os.path.expanduser(entry["path"]))
        return absolute(path if path.is_absolute() else self.base / path)

    # ---- writing
    def save(self) -> bool:
        with self.lock:
            ordered = sorted(self.entries.values(), key=lambda entry: entry.get("created") if isinstance(entry.get("created"), (int, float)) else 0)
            temporary = self.file.with_name(self.file.name + ".tmp")
            try:
                self.file.parent.mkdir(parents=True, exist_ok=True)
                temporary.write_text(json.dumps(ordered + self._others, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
                os.replace(temporary, self.file)
            except OSError:
                return False
            self._stamp = self._stat()
            return True

    def register(self, job_id: str, path: "str | Path", created: float, save: bool = True) -> None:
        with self.lock:
            entry = self.entries.get(job_id) or {"id": job_id}
            entry["path"] = str(absolute(path))
            entry.setdefault("created", round(float(created), 3))
            self.entries[job_id] = entry
            if save:
                self.save()

    def forget(self, job_id: str) -> None:
        with self.lock:
            if self.entries.pop(job_id, None) is not None:
                self.save()
