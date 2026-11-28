"""runs the image tools. one at a time, so a big batch does not flood the machine."""
from __future__ import annotations

import io
import threading
import zipfile
from dataclasses import dataclass
from pathlib import Path

from ..core.tools import (CollageOptions, ConvertOptions, SplitOptions, convert_image, extract_palette, make_collage,
                          open_image, resolve_folder, split_sheet, write_into_folder)
from ..core.tools.common import SUPPORTED_SAVE

MAX_UPLOAD_BYTES = 100 * 1024 * 1024
_lock = threading.Lock()
MIME = {"jpg": "image/jpeg", "png": "image/png", "webp": "image/webp", "zip": "application/zip"}


@dataclass
class ToolOutput:
    name: str
    data: bytes
    ext: str
    width: int = 0
    height: int = 0
    note: str = ""
    saved: list[str] | None = None   # full paths, when the result was written to a folder instead of returned

    @property
    def mime(self) -> str:
        return MIME[self.ext]


def _check(data: bytes) -> None:
    if len(data) > MAX_UPLOAD_BYTES:
        raise ValueError("A picture is too large (limit 100 MB each).")


def _stem(name: str) -> str:
    return Path(name).stem[:100] or "image"


def _finish(output: ToolOutput, folder: Path | None) -> ToolOutput:
    if folder is not None:
        output.saved = [str(write_into_folder(folder, output.name, output.data))]
    return output


def convert(data: bytes, name: str, raw_options: dict, save_to: str | None = None) -> ToolOutput:
    _check(data)
    options = ConvertOptions.from_dict(raw_options)
    folder = resolve_folder(save_to) if save_to else None
    with _lock:
        picture = open_image(data)
        result = convert_image(picture, picture.info.get("source_format"), options)
    return _finish(ToolOutput(f"{_stem(name)}.{result.ext}", result.data, result.ext, result.width, result.height, result.note), folder)


def collage(files: list[tuple[str, bytes]], raw_options: dict, save_to: str | None = None) -> ToolOutput:
    options = CollageOptions.from_dict(raw_options)
    folder = resolve_folder(save_to) if save_to else None
    for _, data in files:
        _check(data)
    with _lock:
        sheet = make_collage([open_image(data) for _, data in files], options)
        buffer = io.BytesIO()
        if options.fmt == "png":
            sheet.save(buffer, "PNG", optimize=True)
        else:
            sheet.save(buffer, "JPEG", quality=options.quality, optimize=True, progressive=True)
    return _finish(ToolOutput(f"collage.{options.fmt}", buffer.getvalue(), options.fmt, sheet.width, sheet.height), folder)


def split(data: bytes, name: str, raw_options: dict, save_to: str | None = None) -> ToolOutput:
    _check(data)
    options = SplitOptions.from_dict(raw_options)
    folder = resolve_folder(save_to) if save_to else None
    with _lock:
        picture = open_image(data)
        tiles = split_sheet(picture, options)
        encoded = []
        for tile_name, tile in tiles:
            buffer = io.BytesIO()
            if options.fmt == "png":
                tile.save(buffer, "PNG", optimize=True)
            elif options.fmt == "webp":
                tile.save(buffer, "WEBP", quality=options.quality)
            else:
                tile.convert("RGB").save(buffer, "JPEG", quality=options.quality, optimize=True)
            encoded.append((f"{_stem(name)}-{tile_name}.{options.fmt}", buffer.getvalue()))
    if folder is not None:
        saved = [str(write_into_folder(folder, tile_file, tile_data)) for tile_file, tile_data in encoded]
        return ToolOutput(f"{_stem(name)}-tiles.zip", b"", "zip", picture.width, picture.height, saved=saved)
    archive = io.BytesIO()
    with zipfile.ZipFile(archive, "w", zipfile.ZIP_STORED) as bundle:
        for tile_file, tile_data in encoded:
            bundle.writestr(tile_file, tile_data)
    return ToolOutput(f"{_stem(name)}-tiles.zip", archive.getvalue(), "zip", picture.width, picture.height)


def palette(data: bytes, count: int = 6) -> list[dict]:
    _check(data)
    with _lock:
        return extract_palette(open_image(data), count)
