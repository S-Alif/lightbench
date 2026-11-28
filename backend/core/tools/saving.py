"""writes results into a folder the person chose. never overwrites: a taken name gets -2, -3, ..."""
from __future__ import annotations

import os
from pathlib import Path


def resolve_folder(raw: str) -> Path:
    """the folder as an absolute path, created if needed. raises ValueError if it can't be used."""
    text = (raw or "").strip()
    if not text:
        raise ValueError("Choose a folder to save to.")
    folder = Path(text).expanduser()
    if not folder.is_absolute():
        raise ValueError("Use a full folder path, like /home/you/Pictures or C:\\Users\\you\\Pictures.")
    try:
        folder.mkdir(parents=True, exist_ok=True)
    except OSError as failure:
        raise ValueError(f"Can't use that folder: {failure.strerror or failure}") from failure
    if not os.access(folder, os.W_OK):
        raise ValueError("Can't write to that folder.")
    return folder


def _free_path(folder: Path, name: str) -> Path:
    path = Path(name)
    for counter in range(1, 10000):
        candidate = folder / (name if counter == 1 else f"{path.stem}-{counter}{path.suffix}")
        if not candidate.exists():
            return candidate
    raise ValueError("Too many files with the same name in that folder.")


def write_into_folder(folder: Path, name: str, data: bytes) -> Path:
    for _ in range(50):
        target = _free_path(folder, name)
        try:
            with open(target, "xb") as out:  # "x" fails instead of overwriting if someone else just took the name
                out.write(data)
            return target
        except FileExistsError:
            continue
    raise ValueError("Could not find a free file name.")
